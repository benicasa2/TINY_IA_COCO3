"""Build bank files and 35-track Disk BASIC images for Tiny 2.1."""
import hashlib
from pathlib import Path
import struct
import sys

PAGE = 8192
FIRST = 64
BANKS_PER_DISK = 14
D, L, H, HID = 96, 4, 4, 256
VOCAB, CTX = 97, 128


def msfloat(raw):
    word, = struct.unpack("<I", raw)
    exponent = (word >> 23) & 255
    if word & 0x7fffffff == 0:
        return bytes(5)
    if not 1 <= exponent <= 252:
        raise ValueError("Unsupported floating-point value in model")
    return bytes([exponent + 2]) + (
        ((word >> 31) << 31) | ((word & 0x7fffff) << 8)
    ).to_bytes(4, "big")


def pack(model):
    if model[:12] != struct.pack("<4s4H", b"TNY2", D, L, H, HID):
        raise ValueError("Expected the released Tiny 2.1 architecture")
    pages = [bytearray()]
    header = []
    pos = 12

    def gain():
        nonlocal pos
        for _ in range(D):
            pages[0].extend(msfloat(model[pos:pos+4]))
            pos += 4

    def table(name, rows, cols):
        nonlocal pos
        stride = 5 + cols
        if len(pages) == 1 or PAGE - len(pages[-1]) < stride:
            pages.append(bytearray())
        first = FIRST + len(pages) - 1
        offset = len(pages[-1])
        first_rows = min(rows, (PAGE - offset) // stride)
        n = PAGE // stride
        header.append(
            f"const Table {name} = {{{first}, {rows}, {cols}, {n}, "
            f"{offset}, {first_rows}}};"
        )
        for _ in range(rows):
            if PAGE - len(pages[-1]) < stride:
                pages.append(bytearray())
            pages[-1].extend(msfloat(model[pos:pos+4]))
            pages[-1].extend(model[pos+4:pos+4+cols])
            pos += 4 + cols

    table("emb", VOCAB, D)
    table("pos", CTX, D)
    for layer in range(L):
        gain()
        for label in ("wq", "wk", "wv", "wo"):
            table(f"{label}{layer}", D, D)
        gain()
        table(f"f1{layer}", HID, D)
        table(f"f2{layer}", D, HID)
    gain()
    assert pos == len(model) and len(pages) <= 64
    for symbol in ("wq", "wk", "wv", "wo", "f1", "f2"):
        items = ", ".join(f"&{symbol}{i}" for i in range(L))
        header.append(f"const Table *const {symbol}[{L}] = {{{items}}};")
    header.append(f"#define MODEL_PAGES {len(pages)}")
    return [p.ljust(PAGE, b"\0") for p in pages], "\n".join(header) + "\n"


def loadm(address, body, entry=0):
    return (struct.pack(">BHH", 0, len(body), address) + body
            + struct.pack(">BHH", 255, 0, entry))


class Disk:
    def __init__(self):
        self.image = bytearray(35 * 18 * 256)
        self.next_granule = 0
        self.next_entry = 0
        self.fat = (17 * 18 + 1) * 256
        self.directory = self.fat + 256
        self.image[self.fat:self.fat+68] = b"\xff" * 68
        self.image[self.directory:(18 * 18) * 256] = b"\xff" * (16 * 256)

    def add(self, name, body, basic=False, file_type=2):
        head, extension = name.split(".")
        if not 1 <= len(head) <= 8 or not 1 <= len(extension) <= 3:
            raise ValueError(f"Invalid Disk BASIC filename: {name}")
        entry = self.directory + self.next_entry * 32
        self.next_entry += 1
        number = self.next_granule
        for off in range(0, len(body), 2304):
            g = self.next_granule
            self.next_granule += 1
            if g >= 68:
                raise ValueError("Disk full")
            physical = g + (2 if g >= 34 else 0)
            chunk = body[off:off+2304]
            start = physical * 2304
            self.image[start:start+len(chunk)] = chunk
            self.image[self.fat+g] = (
                g + 1 if off + len(chunk) < len(body)
                else 0xc0 | ((len(chunk) + 255) // 256)
            )
        last = len(body) % 256 or 256
        record = struct.pack(">8s3sBBBH", head.encode().ljust(8),
                             extension.encode().ljust(3), 0 if basic else file_type,
                             255 if basic or file_type == 1 else 0, number, last)
        self.image[entry:entry+32] = record.ljust(32, b"\0")


def loader(pages, swap=False, mode=0):
    lines = [
        f'CLEAR {500 if mode == 2 else 200},&H1DFF',
        'WIDTH 80:CLS',
        'PRINT "TINY 2.1 / TANDY COLOR COMPUTER 3"',
        'LOADM "BANK.BIN:0"',
        'EXEC &H1E00',
        'IF PEEK(&H1EF1)<>1 THEN PRINT "REQUIRES 2 MB DAT/MMU":END',
        f'FOR I=0 TO {pages-1}',
        f'V=INT(I/{BANKS_PER_DISK})',
    ]
    if swap:
        lines += [
            f'IF I=V*{BANKS_PER_DISK} AND V>0 THEN PRINT "MOUNT DISK";V+1;"IN DRIVE 0. PRESS ENTER":GOSUB 900',
            'F$="W"+RIGHT$("0"+MID$(STR$(I),2),2)+".BIN:0"',
        ]
    else:
        lines += [
            f'IF I=V*{BANKS_PER_DISK} THEN PRINT "LOADING MODEL DISK";V+1',
            'F$="W"+RIGHT$("0"+MID$(STR$(I),2),2)+".BIN:"+MID$(STR$(V),2)',
        ]
    lines += [
        'LOADM F$',
        f'POKE &H1EF0,{FIRST}+I:EXEC &H1E03',
        'NEXT I',
        'LOADM "TINY.BIN:0"',
    ]
    if swap:
        lines.insert(-1, 'PRINT "REMOUNT DISK 1 IN DRIVE 0. PRESS ENTER":GOSUB 900')
    lines.append(f'POKE &H1EF2,{mode}')
    if mode != 2:
        lines.extend(['POKE 65497,0:EXEC:POKE 65496,0', 'END'])
    text = "".join(f"{10 * (i+1)} {line}\r" for i, line in enumerate(lines))
    if swap:
        text += '900 IF INKEY$<>CHR$(13) THEN 900\r910 RETURN\r'
    if mode == 2:
        text += (
            '800 OPEN "I",#1,"ASK.TXT:3"\r'
            '810 OPEN "O",#2,"ANSWERS.TXT:3"\r'
            '820 IF EOF(1) THEN 890\r'
            '830 LINE INPUT #1,Q$:Q$=LEFT$(Q$,72):IF LEN(Q$)=0 THEN 820\r'
            '840 FOR J=1 TO LEN(Q$):POKE &H1EFF+J,ASC(MID$(Q$,J,1)):NEXT:POKE &H1F00+LEN(Q$),0\r'
            '850 PRINT Q$:POKE 65497,0:EXEC:POKE 65496,0:IF PEEK(&H1EF3) THEN 890\r'
            '860 A$="":J=&H1F50\r'
            '870 C=PEEK(J):IF C THEN A$=A$+CHR$(C):J=J+1:GOTO 870\r'
            '880 PRINT A$:PRINT #2,Q$:PRINT #2,A$:GOTO 820\r'
            '890 CLOSE:PRINT "SAVED ANSWERS.TXT IN DRIVE 3":POKE &H1EF3,2:END\r'
        )
    return text.encode("ascii")


def main():
    model, build = Path(sys.argv[1]), Path(sys.argv[2])
    source = model.read_bytes()
    pages, header = pack(source)
    build.mkdir(parents=True, exist_ok=True)
    (build / "model.h").write_text(header, encoding="ascii")
    print(f"Model SHA-256 {hashlib.sha256(source).hexdigest()}, {len(pages)} banks")
    if len(sys.argv) == 3:
        return
    for volume in range((len(pages)+BANKS_PER_DISK-1)//BANKS_PER_DISK):
        disk = Disk()
        if volume == 0:
            disk.add("START.BAS", loader(len(pages)), basic=True)
            disk.add("SWAP.BAS", loader(len(pages), swap=True), basic=True)
            disk.add("DEMO.BAS", loader(len(pages), mode=1), basic=True)
            disk.add("WEB.BAS", loader(len(pages), mode=3), basic=True)
            disk.add("BATCH.BAS", loader(len(pages), mode=2), basic=True)
            disk.add("BANK.BIN", (build / "BANK.BIN").read_bytes())
            disk.add("TINY.BIN", (build / "TINY.BIN").read_bytes())
        for i in range(volume*BANKS_PER_DISK, min((volume+1)*BANKS_PER_DISK, len(pages))):
            disk.add(f"W{i:02d}.BIN", loadm(0x6000, pages[i]))
        if volume == 3:
            disk.add("ASK.TXT", b"What is 7 times 8?\rwhat is the capital of peru\r",
                     file_type=1)
        (Path(sys.argv[3]) / f"TINY{volume+1}.DSK").write_bytes(disk.image)


if __name__ == "__main__":
    main()



