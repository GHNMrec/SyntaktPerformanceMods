"""Mod perf-filter (Syntakt Performance Mods, TEST35): pf.c, the master filter for the jog's PERFORM page only (no
page, no parameters, no MIDI). One source for both OSes (-DOS142):

- linked in the mod area at +0x15100 (up to +0x15800: the room the shelved LINK chunk had; heat's curve tables end
  at +0x15010, gbus starts at +0x15800);
- one hook: the audio interrupt's call of the FX filter CV routine (jsr pf_fx_hook), master-filter's site, so the
  two are exclusive (the builder takes master-filter's when both are asked for: see the catalog).

    python mods/perf-filter/make_patch.py [1.41|1.42]
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

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
OSV = _args[0] if _args else "1.41"
HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "tools" / "unpack"), str(REPO / "tools" / "build")]
import eft  # noqa: E402
import modarea_layout  # noqa: E402

LOAD = 0x4000_0400
RAM, IMG = modarea_layout.RAM, modarea_layout.IMG
CODE_BASE, CODE_END = RAM + 0x15100, RAM + 0x15800
TOOLS = os.environ.get("M68K_ROOT", "~/tools/m68k/root")
CFLAGS = ("-mcpu=54418 -Os -ffreestanding -fno-builtin -nostdlib -fno-pic -fno-common "
          "-fno-tree-loop-distribute-patterns -Wall -Wextra")
EXPORT = ("pf_fx_hook", "pf_apply", "pf_post", "pf_p", "pf_on", "pf_s", "pf_blocks", "pf_posts")   # pf_p = pf + 19
SITES = {"1.41": (0x400A_4F24, "4eb940095da4"), "1.42": (0x400A_4F9C, "4eb940095e1c")}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sh(cmd: str) -> str:
    r = subprocess.run((["wsl.exe", "-e", "bash", "-lc", cmd] if os.name == "nt" else ["bash", "-lc", cmd]),
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"command failed:\n{cmd}\n{r.stderr}")
    return r.stdout + r.stderr


def build_blob():
    with tempfile.TemporaryDirectory(prefix="pf-") as tmp:
        tmp = Path(tmp)
        shutil.copy(HERE / "pf.c", tmp / "pf.c")
        w = eft.to_wsl_path(tmp)
        env = f"R={TOOLS}; export LD_LIBRARY_PATH=$R/usr/lib/x86_64-linux-gnu; cd {w}; "
        gcc = "$R/usr/bin/m68k-linux-gnu-gcc-13 -B$R/usr/libexec/gcc/m68k-linux-gnu/13/ -B$R/usr/bin/m68k-linux-gnu-"
        osd = " -DOS142" if OSV == "1.42" else ""
        warn = sh(env + f"{gcc} {CFLAGS}{osd} -c pf.c -o pf.o")
        if "warning" in warn or "error" in warn:
            raise SystemExit(warn)
        (tmp / "pf.ld").write_text(f"SECTIONS {{ . = {CODE_BASE:#x}; .text : {{ *(.text) }} .rodata : {{ *(.rodata*) }} "
                                   f".data : {{ *(.data) }} }}\n")
        sh(env + "$R/usr/bin/m68k-linux-gnu-ld -N -T pf.ld -e pf_fx_hook -o pf.elf pf.o")
        undef = sh(env + "$R/usr/bin/m68k-linux-gnu-nm -u pf.elf").strip()
        if undef:
            raise SystemExit(f"external symbols not allowed (libgcc?): {undef}")
        heads = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -h pf.elf")
        for name, size in re.findall(r"^\s*\d+\s+(\.\S+)\s+([0-9a-f]+)", heads, re.M):
            if name in (".bss", ".sbss") and int(size, 16):
                raise SystemExit("pf.c must not have .bss variables")
        sh(env + "$R/usr/bin/m68k-linux-gnu-objcopy -O binary -j .text -j .rodata -j .data pf.elf pf.bin")
        syms = {}
        for line in sh(env + "$R/usr/bin/m68k-linux-gnu-nm pf.elf").splitlines():
            parts = line.split()
            if len(parts) == 3:
                syms[parts[2]] = int(parts[0], 16)
        dis = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -d -m m68k:isa-c:emac pf.elf")
        blob = (tmp / "pf.bin").read_bytes()
    syms["pf_s"], syms["pf_p"] = syms["pf"], syms["pf"] + 19
    return blob, syms, dis


def main() -> None:
    stock = REPO / "firmware" / f"Syntakt_OS{OSV}.syx"
    sec3 = eft.unpack(stock, REPO / "unpacked" / stock.stem, ids=[3])[3].read_bytes()
    blob, syms, dis = build_blob()
    if CODE_BASE + len(blob) > CODE_END:
        raise SystemExit(f"perf-filter does not fit: {len(blob)} B (max {CODE_END - CODE_BASE})")
    if re.search(r"\b(mac|msac|movclr)\w*\b|%acc|%macsr", dis):
        raise SystemExit("pf.c must not use the EMAC")
    clash = modarea_layout.runtime_clash(CODE_BASE, CODE_BASE + len(blob))
    if clash:
        raise SystemExit(f"code overlaps a run-time buffer: {clash}")
    addr, expect = SITES[OSV]
    old = sec3[addr - LOAD:addr - LOAD + 6]
    if old.hex() != expect:
        raise SystemExit(f"{addr:#x}: unexpected bytes {old.hex()} (expected {expect})")
    patches = [{"section": 3, "addr": f"{IMG + CODE_BASE - RAM:#010X}", "len": len(blob), "append": True,
                "hex": blob.hex(), "ram": f"{CODE_BASE:#010x}", "what": "(mod area) pf.c"},
               {"section": 3, "addr": f"{addr:#010X}", "len": 6, "expect_sha256": sha(old),
                "hex": (b"\x4e\xb9" + struct.pack(">I", syms["pf_fx_hook"])).hex(),
                "what": "audio interrupt: the FX filter CV routine's call -> pf_fx_hook (PERFORM's filter edits the "
                        "copy of the live values, calls the OS routine, then rewrites its resonance CV)"}]
    spec = {
        "name": "perf-filter",
        "version": "1.0-test35a",
        "os": OSV,
        "requires": ["modarea"],
        "description": "Syntakt Performance Mods: the master filter for the JOG page's PERFORM page only (the analog "
                       "FX block as an end-of-chain DJ filter, Polivoks RESO). No page, no parameters, no MIDI. "
                       "Same hook as master-filter: with master-filter in the build, PERFORM uses that instead.",
        "generated_by": "mods/perf-filter/make_patch.py",
        "symbols": {k: f"{syms[k]:#010x}" for k in EXPORT},
        "patches": patches,
    }
    (HERE / "patch.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    out = REPO / "out" / "perf-filter"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pf.lst").write_text(dis, encoding="utf-8")
    print(f"patch.json ({OSV}): {len(blob)} B at {CODE_BASE:#x}..{CODE_BASE + len(blob):#x}, hook {addr:#x}")


if __name__ == "__main__":
    main()
