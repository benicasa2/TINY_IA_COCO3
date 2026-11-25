"""Tiny CoCo 3 Becker bridge. Python standard library only."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socketserver
import sqlite3
import subprocess
import threading
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

USER_AGENT = "TinyIACoCo3/1.2 (https://github.com/benicasa2/TINY_IA_COCO3)"
LANGUAGES = {"en": "us", "pt": "br"}
MAX_RECORD = 16384


class SearchError(Exception):
    """A safe, user-facing error that never includes the API key."""


def legacy_key(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def question_key(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Keep operators and decimal separators: 2+2 and 2-2 are different facts.
    text = text.strip().rstrip("?!.,;:")
    return " ".join(re.findall(r"[a-z0-9]+|[+*/^%=<>-]|[.,](?=[0-9])", text))


def source_url(url):
    if not isinstance(url, str) or any(c.isspace() for c in url):
        return ""
    try:
        parsed = urlsplit(url)
        if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username:
            return url
    except ValueError:
        pass
    return ""


def serp_request(key, **params):
    query = urlencode({**params, "api_key": key})
    request = Request(f"https://serpapi.com/search.json?{query}", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=9) as result:
            payload = json.loads(result.read(1_500_000))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise SearchError("SerpApi key rejected. Check SERPAPI_API_KEY.") from None
        if exc.code == 429:
            raise SearchError("SerpApi limit reached. Try again later.") from None
        raise SearchError("Google search service returned an error.") from None
    if not isinstance(payload, dict) or payload.get("error"):
        raise SearchError("Google search service returned an error.")
    return payload


def plain_text(value):
    return " ".join(value.split()) if isinstance(value, str) else ""


def overview_text(entries):
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        text = plain_text(entry.get("snippet") or entry.get("title"))
        if entry.get("type") != "heading" and text:
            yield text
        for field in ("list", "text_blocks"):
            children = entry.get(field)
            if isinstance(children, list):
                yield from overview_text(children)


def lookup(question, language="en"):
    key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not key:
        raise SearchError("Set SERPAPI_API_KEY in Windows before starting the bridge.")
    payload = serp_request(key, engine="google", q=question, hl=language, gl=LANGUAGES[language])
    google_link = "https://www.google.com/search?" + urlencode({"q": question, "hl": language})
    box = payload.get("answer_box")
    box = box if isinstance(box, dict) else {}
    text = next((plain_text(box.get(field)) for field in ("answer", "result", "snippet")
                 if plain_text(box.get(field))), "")
    attribution = source_url(box.get("link"))
    title = "Google direct answer"
    if not text:
        overview = payload.get("ai_overview")
        overview = overview if isinstance(overview, dict) else {}
        token = overview.get("page_token")
        if isinstance(token, str) and token and not overview.get("text_blocks"):
            extra = serp_request(key, engine="google_ai_overview", page_token=token)
            overview = extra.get("ai_overview")
            overview = overview if isinstance(overview, dict) else {}
        blocks = overview.get("text_blocks")
        if isinstance(blocks, list):
            text = " ".join(overview_text(blocks))
        references = overview.get("references")
        if isinstance(references, list):
            attribution = next((url for ref in references if isinstance(ref, dict)
                                if (url := source_url(ref.get("link")))), "")
        title = "Google AI Overview"
    if not text:
        return None
    return {
        "question": question, "title": title, "text": text,
        "url": attribution or google_link, "provider": "google",
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def mounted_root(provider):
    if provider == "onedrive":
        candidates = [Path(os.environ[k]) for k in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")
                      if os.environ.get(k)]
        candidates.append(Path.home() / "OneDrive")
    else:
        candidates = [Path(f"{drive}:/") / name
                      for drive in "GHIJKLMNOPQRSTUVWXYZDEF" for name in ("My Drive", "Meu Drive")]
    override = os.environ.get("TINY_" + provider.upper() + "_DIR")
    if override:
        candidates.insert(0, Path(override))
    return next((path for path in candidates if path.is_dir()), None)


class Memory:
    def __init__(self, data_dir, search=lookup):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.database = data_dir / "memory.sqlite3"
        self.search = search
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, key TEXT, day TEXT, body TEXT)")
            db.execute("CREATE INDEX IF NOT EXISTS facts_key ON facts(key, day)")
            db.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def config(self):
        with self.connect() as db:
            return dict(db.execute("SELECT key,value FROM config"))

    def select(self, provider, raw_path):
        if provider == "local":
            root = None
        else:
            root = Path(raw_path).expanduser() if raw_path else mounted_root(provider)
            if root is None or not root.is_absolute() or not root.is_dir():
                return "Drive not mounted. Use /DRIVE with the mounted Windows path."
            root = root / "TinyIA-CoCo3"
            root.mkdir(exist_ok=True)
        with self.connect() as db:
            db.executemany("INSERT OR REPLACE INTO config VALUES (?, ?)",
                           [("provider", provider), ("folder", str(root) if root else "")])
        config = self.config()
        return self.sync(config) if root else "Drive: LOCAL. Saved knowledge stays available offline."

    @staticmethod
    def insert(db, item):
        fields = ("question", "title", "text", "url", "date")
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) for k in fields):
            return
        provider = item.get("provider", "wikipedia")
        item = {k: item[k] for k in fields} | ({"provider": provider} if "provider" in item else {})
        key = question_key(item["question"])
        if not key or not source_url(item["url"]) or not item["text"] or provider not in ("google", "wikipedia"):
            return
        body = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if len(body.encode("utf-8")) > MAX_RECORD:
            return
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        db.execute("INSERT OR IGNORE INTO facts VALUES (?, ?, ?, ?)", (digest, key, item["date"], body))
        return True

    def save(self, item):
        with self.connect() as db:
            if not self.insert(db, item):
                return "Response could not be saved: invalid or too large."
        try:
            return "Saved locally. " + self.sync(self.config())
        except OSError:
            return "Saved locally. Drive unavailable; use /SYNC later."

    def sync(self, config):
        folder = config.get("folder")
        if not folder:
            return "Local memory."
        root = Path(folder)
        if not root.is_dir():
            return "Drive unavailable; local memory remains available."
        imported = exported = 0
        with self.connect() as db:
            for file in root.glob("*.json"):
                try:
                    if file.stat().st_size > MAX_RECORD:
                        continue
                    item = json.loads(file.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                before = db.total_changes
                self.insert(db, item)
                imported += db.total_changes - before
            for identity, body in db.execute("SELECT id,body FROM facts"):
                file = root / f"{identity}.json"
                if file.exists():
                    continue
                temporary = root / f".{uuid4().hex}.tmp"
                try:
                    temporary.write_text(body, encoding="utf-8")
                    temporary.replace(file)
                finally:
                    temporary.unlink(missing_ok=True)
                exported += 1
        return f"Drive {config['provider'].upper()}: {imported} imported, {exported} exported."

    def find(self, question, direct_only=False):
        key = question_key(question)
        with self.connect() as db:
            rows = db.execute("SELECT body FROM facts WHERE key IN (?, ?) ORDER BY day DESC,id DESC",
                              (key, legacy_key(question)))
            for (body,) in rows:
                item = json.loads(body)
                if question_key(item["question"]) == key and (
                    not direct_only or item.get("provider") == "google"
                ):
                    return item
        return None

    @staticmethod
    def format(item, label):
        direct = item.get("provider") == "google"
        text = item["text"]
        if len(text) > 395:
            text = text[:392].rsplit(" ", 1)[0] + "..."
        url = item["url"]
        if len(url) > 155:
            url = urlsplit(url).hostname or "See saved record for URL."
        note = "Google via SerpApi." if direct else "Wikipedia archive (CC BY-SA)."
        return f"{label}: {item['title']}\n{text}\nSource: {url}\nDate: {item['date'][:10]}\n{note}"

    def answer(self, question, pending, refresh=False):
        if not question_key(question):
            return "Enter a question to send to Google.", pending
        if not refresh:
            cached = self.find(question, direct_only=True)
            if cached:
                return self.format(cached, "MEMORY"), None
        try:
            item = self.search(question, self.config().get("language", "en"))
        except (SearchError, OSError, URLError, ValueError, KeyError) as exc:
            cached = self.find(question)
            if cached:
                return self.format(cached, "OFFLINE MEMORY"), None
            return (str(exc) if isinstance(exc, SearchError) else "Google search unavailable."), None
        if item is None:
            return "Google returned no direct answer. Try rephrasing the question.", None
        return self.format(item, "ANSWER") + "\n/SAVE to remember.", item

    def execute(self, text, pending):
        cmd, _, arg = text.partition(" ")
        arg = arg.strip()
        cmd = cmd.lower()
        if cmd == "/db":
            provider = self.config().get("provider", "local").upper()
            google = "key set" if os.environ.get("SERPAPI_API_KEY", "").strip() else "key missing"
            return (f"Memory {provider}. Google: {google}.\n"
                    "/WEB question, /SAVE, /FIND question, /SYNC. /LANG EN or PT.\n"
                    "/DRIVE LOCAL | GOOGLE | ONEDRIVE [path].", pending)
        if cmd == "/drive":
            provider, _, path = arg.partition(" ")
            provider = provider.lower()
            if provider in {"local", "google", "onedrive"}:
                return self.select(provider, path.strip()), pending
            return "Use /DRIVE LOCAL, /DRIVE GOOGLE or /DRIVE ONEDRIVE [path].", pending
        if cmd == "/lang":
            language = arg.lower()
            if language not in LANGUAGES:
                return "Use /LANG EN or /LANG PT.", pending
            with self.connect() as db:
                db.execute("INSERT OR REPLACE INTO config VALUES ('language', ?)", (language,))
            return f"Google search language: {language.upper()}.", pending
        if cmd == "/sync":
            return self.sync(self.config()), pending
        if cmd == "/web":
            return self.answer(arg, pending, refresh=True)
        if cmd == "/save":
            return (self.save(pending) if pending else "Use /WEB before /SAVE."), None
        if cmd == "/find":
            item = self.find(arg)
            return (self.format(item, "MEMORY") if item else "No saved answer for this question."), pending
        if cmd.startswith("/"):
            return "Unknown command. Type /DB for web and memory help.", pending
        return self.answer(text, pending)


class Connection(socketserver.StreamRequestHandler):
    def handle(self):
        pending = None
        while True:
            try:
                raw = self.rfile.readline(128)
            except ConnectionResetError:
                return
            if not raw:
                return
            if len(raw) < 3 or not raw.endswith(b"\n") or not 65 <= raw[0] <= 90:
                continue
            request = raw[1:-1].decode("ascii", errors="replace")
            try:
                answer, pending = self.server.memory.execute(request, pending)
            except (OSError, ValueError, sqlite3.Error):
                answer, pending = "Memory or drive error. Retry or select /DRIVE LOCAL.", None
            normalized = unicodedata.normalize("NFKD", answer)
            normalized = "".join(c for c in normalized if not unicodedata.combining(c))
            clean = normalized.encode("ascii", "replace")
            clean = bytes(c for c in clean if c == 10 or 32 <= c <= 126)
            try:
                self.wfile.write(raw[:1] + (b"1" if clean else b"0") + clean[:720] + b"\0")
            except (BrokenPipeError, ConnectionResetError):
                return


class Bridge(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, memory):
        self.memory = memory
        super().__init__(address, Connection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TinyIA-CoCo3")
    parser.add_argument("--port", type=int, default=65504)
    parser.add_argument("emulator", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    with Bridge(("127.0.0.1", args.port), Memory(args.data)) as server:
        if not args.emulator:
            print(f"Tiny bridge ready on 127.0.0.1:{args.port}", flush=True)
            server.serve_forever()
        else:
            emulator = args.emulator[1:] if args.emulator[0] == "--" else args.emulator
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                return subprocess.call([*emulator, '-becker-port', str(server.server_address[1])])
            finally:
                server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
