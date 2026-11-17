"""Mod tripwire (diagnostic, OS 1.41 and 1.42): tw.c, a stack tripwire for the silent freeze (TEST33b-diag).

- linked in the mod area at +0x10B00 (up to +0x11000: the end of seqpages' old reservation, before maxmenu); its table and
  counters are .data inside that chunk;
- hooks: the OS's task create (0x40001640, the same on both OSes) registers and paints every task stack; the
  audio interrupt, right after it saved its registers (1.41 0x400A3864, 1.42 0x400A38DC), checks the interrupted
  stack and one canary a block, and at its end (0x400A54A0 / 0x400A5518) the interrupted stack's canary (tw.c says
  what the stop screen shows).

    python mods/tripwire/make_patch.py [1.41|1.42]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

OSV = sys.argv[1] if len(sys.argv) > 1 else "1.41"
HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]       # this OS tree (os141 or os142)
sys.path[:0] = [str(REPO / "tools" / "unpack"), str(REPO / "tools" / "build")]
import eft  # noqa: E402
import modarea_layout  # noqa: E402

LOAD = 0x4000_0400
RAM, IMG = modarea_layout.RAM, modarea_layout.IMG
CODE_BASE, CODE_END = RAM + 0x10B00, RAM + 0x11000
TOOLS = os.environ.get("M68K_ROOT", "~/tools/m68k/root")   # "/" = the distro cross-toolchain (apt: gcc-13-m68k-linux-gnu binutils-m68k-linux-gnu)
CFLAGS = "-mcpu=54418 -Os -ffreestanding -fno-builtin -nostdlib -fno-pic -fno-common -Wall -Wextra"
EXPORT = ("tw_mk", "tw_blk_hook", "tw_end_hook", "tw_create", "tw_isr", "tw_exit", "tw_base", "tw_end", "tw_entry", "tw_n", "tw_rot", "tw_blk",
          "tw_skip", "tw_least", "tw_lix", "tw_cur")
SITES = {"1.41": dict(isr=0x400A_3864, end=0x400A_54A0), "1.42": dict(isr=0x400A_38DC, end=0x400A_5518)}
CREATE = 0x4000_1640


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sh(cmd: str) -> str:
    r = subprocess.run((["wsl.exe", "-e", "bash", "-lc", cmd] if os.name == "nt" else ["bash", "-lc", cmd]),
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"command failed:\n{cmd}\n{r.stderr}")
    return r.stdout + r.stderr


def build_blob():
    with tempfile.TemporaryDirectory(prefix="tw-") as tmp:
        tmp = Path(tmp)
        shutil.copy(HERE / "tw.c", tmp / "tw.c")
        w = eft.to_wsl_path(tmp)
        env = f"R={TOOLS}; export LD_LIBRARY_PATH=$R/usr/lib/x86_64-linux-gnu; cd {w}; "
        gcc = "$R/usr/bin/m68k-linux-gnu-gcc-13 -B$R/usr/libexec/gcc/m68k-linux-gnu/13/ -B$R/usr/bin/m68k-linux-gnu-"
        osd = " -DOS142" if OSV == "1.42" else ""
        warn = sh(env + f"{gcc} {CFLAGS}{osd} -c tw.c -o tw.o")
        if "warning" in warn or "error" in warn:
            raise SystemExit(warn)
        sh(env + f"$R/usr/bin/m68k-linux-gnu-ld -N -Ttext={CODE_BASE:#x} -e tw_isr -o tw.elf tw.o")
        undef = sh(env + "$R/usr/bin/m68k-linux-gnu-nm -u tw.elf").strip()
        if undef:
            raise SystemExit(f"external symbols not allowed (libgcc?): {undef}")
        heads = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -h tw.elf")
        for name, size in re.findall(r"^\s*\d+\s+(\.\S+)\s+([0-9a-f]+)", heads, re.M):
            if name in (".bss", ".sbss") and int(size, 16):
                raise SystemExit("tw.c must not have .bss variables")
        sh(env + "$R/usr/bin/m68k-linux-gnu-objcopy -O binary -j .text -j .rodata -j .data tw.elf tw.bin")
        syms = {}
        for line in sh(env + "$R/usr/bin/m68k-linux-gnu-nm tw.elf").splitlines():
            parts = line.split()
            if len(parts) == 3:
                syms[parts[2]] = int(parts[0], 16)
        dis = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -d -m m68k:isa-c:emac tw.elf")
        blob = (tmp / "tw.bin").read_bytes()
    return blob, syms, dis


def main() -> None:
    stock = REPO / "firmware" / f"Syntakt_OS{OSV}.syx"
    sec3 = eft.unpack(stock, REPO / "unpacked" / stock.stem, ids=[3])[3].read_bytes()
    blob, syms, dis = build_blob()
    if CODE_BASE + len(blob) > CODE_END:
        raise SystemExit(f"does not fit: {len(blob)} B (max {CODE_END - CODE_BASE})")
    if re.search(r"\b(mac|msac|movclr)\w*\b|%acc|%macsr", dis):
        raise SystemExit("tw.c must not use the EMAC (the interrupt saves it only later)")
    clash = modarea_layout.runtime_clash(CODE_BASE, CODE_BASE + len(blob))
    if clash:
        raise SystemExit(f"code overlaps a run-time buffer: {clash}")

    def fixed(addr: int, new: bytes, what: str, expect: str) -> dict:
        old = sec3[addr - LOAD:addr - LOAD + len(new)]
        if old.hex() != expect:
            raise SystemExit(f"{addr:#x}: unexpected bytes {old.hex()} (expected {expect})")
        return {"section": 3, "addr": f"{addr:#010X}", "len": len(new), "expect_sha256": sha(old),
                "hex": new.hex(), "what": what}

    j = lambda s: struct.pack(">I", syms[s])                                        # noqa: E731
    patches = [{"section": 3, "addr": f"{IMG + CODE_BASE - RAM:#010X}", "len": len(blob), "append": True,
                "hex": blob.hex(), "ram": f"{CODE_BASE:#010x}", "what": "(mod area) tw.c"},
               fixed(CREATE, b"\x4e\xf9" + j("tw_mk"), "task create (tcb, entry, prio, stack, size): register and "
                     "paint the stack, then stock", "202f000c72fc"),
               fixed(SITES[OSV]["isr"], b"\x4e\xb9" + j("tw_blk_hook"), "audio interrupt, registers saved: the "
                     "stack guard and one canary a block", "c1b9fc04c010"),
               fixed(SITES[OSV]["end"], b"\x4e\xb9" + j("tw_end_hook"), "audio interrupt, before its registers come "
                     "back: the interrupted stack's canary (an overrun by this block)", "4cee3fffff5c")]
    spec = {
        "name": "tripwire",
        "version": "1.0-test33b",
        "os": OSV,
        "requires": ["modarea"],
        "description": "DIAGNOSTIC: paints every task stack at creation; every audio block checks the room left "
                       "under the interrupted stack and one stack's bottom canary. A stack about to run out (or "
                       "already overrun) stops the unit with an exception screen (57AC...) that names the task.",
        "generated_by": "mods/tripwire/make_patch.py",
        "links": {},
        "symbols": {k: f"{syms[k]:#010x}" for k in EXPORT},
        "patches": patches,
    }
    (HERE / "patch.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (REPO / "out" / "tripwire").mkdir(parents=True, exist_ok=True)
    (HERE / "tw.lst").write_text(dis, encoding="utf-8")
    print(f"patch.json ({OSV}): {len(blob)} B at {CODE_BASE:#x}..{CODE_BASE + len(blob):#x}")


if __name__ == "__main__":
    main()
