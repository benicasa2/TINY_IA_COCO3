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
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

USER_AGENT = "TinyIACoCo3/1.1 (https://github.com/benicasa2/TINY_IA_COCO3)"
WIKIS = {"en": "en.wikipedia.org", "pt": "pt.wikipedia.org"}
MAX_RECORD = 16384


def question_key(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def lookup(question, language="en"):
    wiki = WIKIS[language]
    arguments = urlencode({
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": question, "gsrlimit": 3,
        "gsrnamespace": 0, "prop": "extracts|info",
        "exintro": 1, "explaintext": 1, "exchars": 320, "exlimit": 3,
        "inprop": "url",
    })
    request = Request(f"https://{wiki}/w/api.php?{arguments}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=8) as response:
        payload = json.loads(response.read(512_000))
    pages = sorted(payload.get("query", {}).get("pages", []), key=lambda page: page.get("index", 999))
    for page in pages:
        extract = " ".join(page.get("extract", "").split())
        if extract:
            return {
                "question": question, "title": page["title"], "text": extract[:400],
                "url": f"https://{wiki}/?curid={page['pageid']}",
                "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
    return None


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
        item = {k: item[k] for k in fields}
        key = question_key(item["question"])
        if not key or not item["url"].startswith(tuple(f"https://{wiki}/" for wiki in WIKIS.values())) or not item["text"]:
            return
        body = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if len(body.encode("utf-8")) > MAX_RECORD:
            return
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        db.execute("INSERT OR IGNORE INTO facts VALUES (?, ?, ?, ?)", (digest, key, item["date"], body))

    def save(self, item):
        with self.connect() as db:
            self.insert(db, item)
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

    def find(self, question):
        with self.connect() as db:
            row = db.execute("SELECT body FROM facts WHERE key=? ORDER BY day DESC,id DESC LIMIT 1",
                             (question_key(question),)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def format(item, label):
        return (f"{label}: {item['title']}\n{item['text']}\n"
                f"Source: {item['url']}\nDate: {item['date'][:10]}\n"
                "Wikipedia (CC BY-SA; see article for attribution).")

    def execute(self, text, pending):
        cmd, _, arg = text.partition(" ")
        arg = arg.strip()
        cmd = cmd.lower()
        if cmd == "/db":
            provider = self.config().get("provider", "local").upper()
            return (f"Memory {provider}. /WEB topic, /SAVE, /FIND topic, /SYNC. /LANG EN or PT.\n"
                    "/DRIVE LOCAL | GOOGLE | ONEDRIVE [path].", pending)
        if cmd == "/drive":
            provider, _, path = arg.partition(" ")
            provider = provider.lower()
            if provider in {"local", "google", "onedrive"}:
                return self.select(provider, path.strip()), pending
            return "Use /DRIVE LOCAL, /DRIVE GOOGLE or /DRIVE ONEDRIVE [path].", pending
        if cmd == "/lang":
            language = arg.lower()
            if language not in WIKIS:
                return "Use /LANG EN or /LANG PT.", pending
            with self.connect() as db:
                db.execute("INSERT OR REPLACE INTO config VALUES ('language', ?)", (language,))
            return f"Wikipedia language: {language.upper()}.", pending
        if cmd == "/sync":
            return self.sync(self.config()), pending
        if cmd == "/web":
            if not question_key(arg):
                return "Use /WEB followed by a topic.", None
            try:
                item = self.search(arg, self.config().get("language", "en"))
            except (OSError, URLError, ValueError, KeyError):
                item = self.find(arg)
                if item:
                    return self.format(item, "OFFLINE MEMORY"), None
                return "Web unavailable. Saved facts can still be read with /FIND.", None
            return (self.format(item, "WEB") + "\n/SAVE to remember." if item else "No article found."), item
        if cmd == "/save":
            return (self.save(pending) if pending else "Use /WEB before /SAVE."), None
        if cmd == "/find":
            item = self.find(arg)
            return (self.format(item, "MEMORY") if item else "No saved answer for this question."), pending
        if cmd.startswith("/"):
            return "Unknown command. Type /DB for web and memory help.", pending
        item = self.find(text)
        return (self.format(item, "MEMORY") if item else ""), pending


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
