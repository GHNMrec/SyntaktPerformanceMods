"""Generate os141_sec3_emac_sites.json: the EMAC instruction addresses of the stock OS 1.41 section 3 (CPU #1).

The audio interrupt (0x400A3856) and the routines it calls mix with EMAC; Unicorn does not emulate EMAC, so
board.py hands those instructions to tools/emu/emac.py, which needs every site. GNU objdump's linear sweep of
the section (ColdFire ISA_C + EMAC) gives them; the instruction regex allows the padding objdump puts after
the hex words (a stricter one missed sites). Only the code region is swept: data decoded as instructions
would add thousands of false sites.

    python tools/emu/isr/gen_sites.py [--objdump ~/tools/m68k/root]
Writes addresses only (compatibility information), no Elektron bytes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "unpack"))
import eft  # noqa: E402

LOAD = 0x4000_0400
CODE_END = 0x401C_0000                  # code ends here; the rest of the section is tables and data
OUT = HERE / "os141_sec3_emac_sites.json"
LINE = re.compile(r"^\s*([0-9a-f]{8}):\s+((?:[0-9a-f]{4} ?)+)\s*\t(\S+)\s*(.*)$")
MNEMONICS = re.compile(r"^(mac[lw]|msac[lw]|movclrl)$")
NOTE = ("EMAC instruction addresses of the stock OS 1.41 section 3 (CPU #1): GNU objdump (m68k:isa-c:emac) linear "
        "sweep of the code region; addresses only, no Elektron bytes. Regenerate: tools/emu/isr/gen_sites.py.")


def sites(dis: str) -> list[int]:
    out = []
    for line in dis.splitlines():
        m = LINE.match(line)
        if m and (MNEMONICS.match(m[3]) or re.search(r"%acc|%macsr|%mask", m[4])):
            out.append(int(m[1], 16))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--objdump", default="~/tools/m68k/root", help="root of the extracted m68k binutils")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        sec3 = eft.unpack(ROOT / "firmware" / "Syntakt_OS1.41.syx", Path(tmp), ids=[3])[3]
        r = os.path.expanduser(a.objdump)
        env = dict(os.environ, LD_LIBRARY_PATH=f"{r}/usr/lib/x86_64-linux-gnu")
        dis = subprocess.run([f"{r}/usr/bin/m68k-linux-gnu-objdump", "-b", "binary", "-m", "m68k:isa-c:emac",
                              f"--adjust-vma={LOAD:#x}", f"--stop-address={CODE_END:#x}", "-D", str(sec3)],
                             capture_output=True, text=True, check=True, env=env).stdout
    s = sorted(sites(dis))
    OUT.write_text(json.dumps({"section3_note": NOTE,
                               "code_range": ["0x40000400", "0x401C0000"], "count": len(s), "sites": s},
                              indent=0) + "\n")
    print(f"{OUT.name}: {len(s)} sites")


if __name__ == "__main__":
    main()
