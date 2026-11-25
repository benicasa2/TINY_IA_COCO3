"""Rebuild the four CoCo 3 images with CMOC and LWTOOLS on PATH."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--fujinet"):
    sys.exit("Usage: python build.py OUTPUT_DIRECTORY [--fujinet]")
fujinet = len(sys.argv) == 3
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="tiny-coco3-") as tmp:
    work = Path(tmp)
    pack = [sys.executable, str(root / "pack.py"), str(root / "weights/TINY.BIN"), "."]
    # Relative filenames protect older host builds of CMOC from shell quoting.
    subprocess.run(pack, cwd=work, check=True)
    for name in ("bank.asm", "tiny.c"):
        shutil.copyfile(root / name, work / name)
    subprocess.run(["lwasm", "--6809", "--format=decb", "--output=BANK.BIN",
                    "bank.asm"], cwd=work, check=True)
    flags = []
    if fujinet:
        driver = root / "fujinet.inc"
        shutil.copyfile(driver if driver.is_file() else root.parent / "fujinet.inc", work / "fujinet.inc")
        flags.append("-DTINY_FUJINET")
    subprocess.run(["cmoc", *flags, "--coco", "--org=2000", "--limit=6000", "-O2",
                    "-o", "TINY.BIN", "tiny.c"], cwd=work, check=True)
    subprocess.run([*pack, str(out), *sys.argv[2:]], cwd=work, check=True)
