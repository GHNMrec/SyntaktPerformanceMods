"""Unpack YOUR stock OS file into unpacked/ (git-ignored) so the emulator tests can run.

    python tools/unpack/unpack_stock.py            # this OS tree's firmware/Syntakt_OS<ver>.syx

The stock file is never committed. Get it from elektron.se and put it in this tree's firmware/ folder."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eft  # noqa: E402

ver = "1.42" if ROOT.name == "os142" else "1.41"
syx = ROOT / "firmware" / f"Syntakt_OS{ver}.syx"
if not syx.is_file():
    sys.exit(f"missing {syx}: download the official OS {ver} file from elektron.se and put it there")
out = ROOT / "unpacked" / syx.stem
eft.unpack(syx, out, ids=[3, 7])
print("unpacked to", out)
