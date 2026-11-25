"""Rebuild the four CoCo 3 images with CMOC and LWTOOLS on PATH."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
if len(sys.argv) != 2:
    sys.exit("Usage: python build.py OUTPUT_DIRECTORY")
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="tiny-coco3-") as tmp:
    work = Path(tmp)
    pack = [sys.executable, str(root / "pack.py"), str(root / "weights/TINY.BIN"), "."]
    # Relative filenames protect older host builds of CMOC from shell quoting.
    subprocess.run(pack, cwd=work, check=True)
    for name in ("bank.asm", "tiny.c", "dot6309.asm"):
        shutil.copyfile(root / name, work / name)
    subprocess.run(["lwasm", "--6809", "--format=decb", "--output=BANK.BIN",
                    "bank.asm"], cwd=work, check=True)
    subprocess.run(["lwasm", "--6309", "-fobj", "--output=dot6309.o",
                    "dot6309.asm"], cwd=work, check=True)
    subprocess.run(["cmoc", "--coco", "--org=2000", "--limit=6000", "-O2",
                    "-o", "TINY.BIN", "tiny.c", "dot6309.o"], cwd=work, check=True)
    subprocess.run([*pack, str(out)], cwd=work, check=True)
