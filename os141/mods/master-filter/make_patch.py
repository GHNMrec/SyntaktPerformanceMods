"""Mod master-filter: builds patch.json from mf.c + mf_hook.S (see the comments at the top of both).

    python mods/master-filter/make_patch.py      # ColdFire gcc 13 + binutils (WSL on Windows, native on Linux)

Analog master filter: while its switch (FLTR) is ON, everything goes through the analog FX block, whose
filter TYPE/FREQ/RESO follow the master filter's knobs (controls on the FX track's SYN page 2, TEST15),
with a Polivoks-style RESO (past the FX filter's own maximum, see mf.c). Edits the audio interrupt's copy of
the live values and, after the OS's FX filter CV routine, its resonance CV only. Needs modarea, vparams (v6+)
and midi-guard (the 7 ids below). Links in the mod area at +0x6300 (up to +0x7E00; +0x6000..+0x62A4 stays
free for the FM4 port's relocated stock tables, tools/fm4).

    MF_PUSH=hot python mods/master-filter/make_patch.py   # twice the resonance push (MF_PUSH_SHIFT 1)
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO / "tools" / "unpack"), str(REPO / "tools" / "build")]
import eft  # noqa: E402
import modarea_layout  # noqa: E402

_vp = importlib.util.spec_from_file_location("vparams_make_patch", REPO / "mods" / "vparams" / "make_patch.py")
vparams = importlib.util.module_from_spec(_vp)
_vp.loader.exec_module(vparams)

LOAD = 0x4000_0400
DESC, REC = 0x4022_D59C, 52
CODE, CODE_END = modarea_layout.RAM + 0x6300, modarea_layout.RAM + 0x7E00
TOOLS = "~/tools/m68k/root"
# (id, short, long, max, default): borrowed ids, see mf.c. 443 = IMPULSE SHP, 402/406/412 = COL, 442 = IMPULSE
# HOLD, 431/432 = NLEV/NDEC of a fourth drum machine (group 31)
PARAMS = [(443, "TYPE", "Master Filter Type", 7, 0),
          (402, "FREQ", "Master Filter Freq", 127, 127),
          (406, "RESO", "Master Filter Reso", 127, 0),
          (412, "RET", "Delay/Reverb Returns", 1, 0),         # 0 = FLTR (through the filter), 1 = KIT (TEST15b; DRV's id)
          (442, "FLTR", "Master Filter On/Off", 1, 0),
          (431, "TRIM", "Output Level", 127, 64),             # 64 = 0 dB (LVL on the SYN page since TEST15)
          (432, "CMP", "Comp Target", 1, 0)]                  # 0 = MAIN, 1 = FX (read by master-comp)
IDS = {"TYPE": 443, "FREQ": 402, "RESO": 406, "RET": 412, "ON": 442, "TRIM": 431, "CMP": 432}
ID_IN = 268                                     # master-comp's IN meter, slot F of SYN page 2 (page 0)
P_CMP = 6                                       # mf_p index of CMP (mf.c): master-comp reads mf_p + P_CMP
VP_SLOT = 18                                    # vparams slots 18..24
TRIM_DB = 12 / 64                               # TRIM: (knob - 64) * 0.1875 dB, -12.0 .. +11.8 dB
HOOK = (0x400A_4F24, "4eb940095da4", "mf_fx_hook",
        "audio interrupt: jsr mf_fx_hook (master filter edits the copy of the live values, calls the FX filter "
        "CV routine 0x40095DA4, then rewrites its resonance CV)")
PAGE = (0x4019_4BC0, "42b941b9f730", "mf_page_stub",
        "TEST15: page 0 (SYN page 2): A FLTR, B TYPE, C FREQ, D RESO, E CMP, F IN, G empty (RET until TEST16); pages 12 and 19 stock; objects "
        "(jsr mf_page_stub, which also replays clr.l 0x41B9F730)")
# TEST15: the FX track's SYN tab (view built at 0x40035D1E with the page vector {32}, count at 0x40035CF4, array
# operand at 0x40035CFA) cycles {32, 0}: page 0 is the OS's NONE page, in no tab, empty; its names come from the
# page initializer's string copies (operands at 0x401942CE / 0x401942FE, as fx3 names page 25).
SYN_COUNT = (0x4003_5CF4, "7201", bytes.fromhex("7202"), "FX SYN tab: 2 pages (moveq #2,d1)")
SYN_ARRAY = (0x4003_5CFA, "401c7f58", "mf_syn_pages", "FX SYN tab: page vector {32, 0} (SYN, master filter)")
PAGE0_NAMES = [(0x4019_42CE, "4024f83f", "mf_page0_s", "page 0: short name SYN2 (was NONE)"),
               (0x4019_42FE, "40251a64", "mf_page0_l", "page 0: long name Master Filter (was None)")]
# MIDI in: the CC and NRPN handlers' table lookups (mf_cc_lookup / mf_nrpn_lookup, see mf.c MIDI)
MIDI_CC = (0x4001_C17A, "4eb9400a671e", "mf_cc_lookup",
           "CC handler 0x4001C12C: jsr mf_cc_lookup (FX track CC 3/9/12/13 -> master filter, else the OS's lookup)")
MIDI_NRPN = (0x4001_C2B4, "4eb9400a679e", "mf_nrpn_lookup",
             "NRPN handler 0x4001C262: jsr mf_nrpn_lookup (FX track NRPN 1:48..1:51 -> master filter, else the OS's lookup)")
MIDI_CCS = {"ON": 3, "TYPE": 9, "FREQ": 12, "RESO": 13}                    # RET, TRIM, CMP: none (CC 14 is the OS's)
MIDI_NRPNS = {"ON": (1, 48), "TYPE": (1, 49), "FREQ": (1, 50), "RESO": (1, 51)}
# Page 12 is drawn by the OS's generic 8-slot draw 0x4003A244 (the FILTER view sends its pages 11 (FLTR1) and
# 10 elsewhere, 0x4004291C), which draws every slot the same way: no per-id fix as TEST9's AMP view needed.
PUSH = os.environ.get("MF_PUSH", "")            # "" (default): PUSH = table range >> 2; "hot": >> 1
if PUSH not in ("", "hot"):
    raise SystemExit(f"MF_PUSH must be empty or 'hot', not {PUSH!r}")
CFLAGS = ("-mcpu=54418 -Os -ffreestanding -fno-builtin -nostdlib -fno-pic -fno-common "
          "-fno-tree-loop-distribute-patterns -Wall -Wextra " +
          " ".join(f"-DID_{k}={v}" for k, v in IDS.items()) + (" -DMF_PUSH_SHIFT=1" if PUSH == "hot" else ""))
ASFLAGS = "-mcpu=54418 " + " ".join(f"--defsym ID_{k}={v}" for k, v in IDS.items()) + f" --defsym ID_IN={ID_IN}"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sh(cmd: str) -> str:
    args = ["wsl.exe", "-e", "bash", "-lc", cmd] if os.name == "nt" else ["bash", "-lc", cmd]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"command failed:\n{cmd}\n{r.stderr}")
    return r.stdout + r.stderr


# ---- FREQ in Hz. The OS has no Hz scale for the analog FX filter (it shows 0.00-127.00; the cutoff depends on
# each unit's factory calibration). Measured on the author's Syntakt (2026-10-19): master filter BP2, high RESO, the
# Syntakt's noise through it, Ableton Spectrum; Hz = peak of the curve smoothed over ~1/6 octave. FREQ 0 peaks
# below the analyzer's 10 Hz floor; FREQ 96 was not captured. An analog exponential converter is linear in
# octaves, so the display uses the least-squares line through these points (log2 Hz against FREQ):
# about 5.9 Hz x 2^(0.0926 FREQ), 1.11 semitones per step, within 0.18 octave of every measured point.
MEASURED = [(16, 15), (32, 52), (48, 130), (64, 340), (80, 1016), (112, 8292), (127, 19373)]


def freq_line() -> tuple[float, float]:
    xs = [v for v, _ in MEASURED]
    ys = [math.log2(f) for _, f in MEASURED]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


def freq_hz(v: int) -> float:
    a, b = freq_line()
    return 2 ** (a + b * v)


def freq_text(f: float) -> str:
    if f < 1000:
        return f"{round(f)}Hz"
    if f < 9950:
        return f"{f / 1000:.1f}k"
    return f"{round(f / 1000)}k"


def trim_db(v: int) -> float:
    return (v - 64) * TRIM_DB


def trim_q12(v: int) -> int:
    return round(4096 * 10 ** (trim_db(v) / 20))


def trim_text(v: int) -> str:
    d = round(trim_db(v), 1)
    return "0.0" if d == 0 else f"{d:+.1f}"


def tables() -> str:
    txt = [freq_text(freq_hz(v)) for v in range(128)]
    trim = [trim_text(v) for v in range(128)]
    assert all(len(t) <= 5 for t in txt + trim) and trim_q12(64) == 4096
    return ("/* generated by mods/master-filter/make_patch.py (MEASURED, TRIM_DB) */\n"
            "static const char FREQ_TXT[128][6] = {" + ", ".join(json.dumps(t) for t in txt) + "};\n"
            "static const u16 TRIM_Q12[128] = {" + ", ".join(str(trim_q12(v)) for v in range(128)) + "};\n"
            "static const char TRIM_TXT[128][6] = {" + ", ".join(json.dumps(t) for t in trim) + "};\n")


def build() -> tuple[bytes, dict[str, int], str]:
    with tempfile.TemporaryDirectory(prefix="master-filter-") as tmp:
        tmp = Path(tmp)
        for f in ("mf.c", "mf_hook.S"):
            shutil.copy(HERE / f, tmp / f)
        (tmp / "mf_tables.h").write_text(tables(), encoding="ascii")
        w = eft.to_wsl_path(tmp)
        env = f"R={TOOLS}; export LD_LIBRARY_PATH=$R/usr/lib/x86_64-linux-gnu; cd {w}; "
        gcc = "$R/usr/bin/m68k-linux-gnu-gcc-13 -B$R/usr/libexec/gcc/m68k-linux-gnu/13/ -B$R/usr/bin/m68k-linux-gnu-"
        warn = sh(env + f"{gcc} {CFLAGS} -c mf.c -o mf.o")
        if warn.strip():
            raise SystemExit(f"compiler warnings:\n{warn}")
        sh(env + f"$R/usr/bin/m68k-linux-gnu-as {ASFLAGS} mf_hook.S -o mf_hook.o")
        sh(env + f"$R/usr/bin/m68k-linux-gnu-ld -N -Ttext={CODE:#x} -e mf_apply -o mf.elf mf_hook.o mf.o")
        undef = sh(env + "$R/usr/bin/m68k-linux-gnu-nm -u mf.elf").strip()
        if undef:
            raise SystemExit(f"external symbols not allowed (libgcc?): {undef}")
        heads = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -h mf.elf")
        for name, size in re.findall(r"^\s*\d+\s+(\.\S+)\s+([0-9a-f]+)", heads, re.M):
            if name in (".bss", ".sbss") and int(size, 16):
                raise SystemExit("mf.c must not have .bss variables")
        sh(env + "$R/usr/bin/m68k-linux-gnu-objcopy -O binary -j .text -j .rodata -j .data mf.elf mf.bin")
        syms = {}
        for line in sh(env + "$R/usr/bin/m68k-linux-gnu-nm mf.elf").splitlines():
            p = line.split()
            if len(p) == 3:
                syms[p[2]] = int(p[0], 16)
        dis = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -d -m m68k:isa-c:emac mf.elf")
        blob = (tmp / "mf.bin").read_bytes()
    return blob, syms, dis


def main() -> None:
    stock = REPO / "firmware" / "Syntakt_OS1.41.syx"
    sec3 = eft.unpack(stock, REPO / "unpacked" / stock.stem, ids=[3])[3].read_bytes()
    blob, syms, dis = build()
    if CODE + len(blob) > CODE_END:
        raise SystemExit(f"mf.bin too large: {len(blob)} B")
    emac = [int(m[1], 16) for m in re.finditer(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{4} ?)+\s+(\S+)\s*(.*)$", dis, re.M)
            if re.match(r"^(mac[lw]|msac[lw]|movclrl)$", m[2]) or re.search(r"%(acc|macsr|mask)", m[3])]
    if emac:                                    # the OS routines around the hook rely on MACSR and accumulators
        raise SystemExit(f"EMAC instructions in master-filter: {[hex(a) for a in emac]}")

    def fixed(addr: int, new: bytes, what: str, expect: str | None = None) -> dict:
        old = sec3[addr - LOAD:addr - LOAD + len(new)]
        if expect is not None and old.hex() != expect:
            raise SystemExit(f"{addr:#x}: unexpected bytes {old.hex()} (expected {expect})")
        return {"section": 3, "addr": f"{addr:#010X}", "len": len(new), "expect_sha256": sha(old),
                "hex": new.hex(), "what": what}

    long = lambda v: struct.pack(">I", v)
    img = modarea_layout.IMG + (CODE - modarea_layout.RAM)
    patches = [{"section": 3, "addr": f"{img:#010X}", "len": len(blob), "append": True, "hex": blob.hex(),
                "ram": f"{CODE:#010x}", "what": "(area mod) analog master filter (mf.c, mf_hook.S)"}]
    for addr, orig, sym, what in (HOOK, PAGE, MIDI_CC, MIDI_NRPN):
        patches.append(fixed(addr, struct.pack(">HI", 0x4EB9, syms[sym]), what, orig))
    patches.append(fixed(SYN_COUNT[0], SYN_COUNT[2], SYN_COUNT[3], SYN_COUNT[1]))
    patches.append(fixed(SYN_ARRAY[0], long(syms[SYN_ARRAY[2]]), SYN_ARRAY[3], SYN_ARRAY[1]))
    for addr, orig, sym, what in PAGE0_NAMES:
        patches.append(fixed(addr, long(syms[sym]), what, orig))
    for n, (pid, short, ln, mx, df) in enumerate(PARAMS):
        if pid == IDS["RET"]:                     # TEST26: RET left the page in TEST17; id 412 is G-BUS's MODE (mods/gbus)
            continue
        r = DESC + REC * pid
        key = short.lower()
        patches.append(vparams.entry(VP_SLOT + n, pid, syms["mf_get"], syms["mf_set"], f"master-filter {short}"))
        patches += [fixed(r + 8, struct.pack(">III", 0, mx << 8, df << 8), f"id {pid} -> {short}: min, max, default"),
                    fixed(r + 40, long(syms[f"mf_n_{key}_l"]), f"id {pid}: long name '{ln}'"),
                    fixed(r + 48, long(syms[f"mf_n_{key}_s"]), f"id {pid}: short name '{short}'")]
    spec = {
        "name": "master-filter", "os": "1.41", "requires": ["modarea", "vparams", "midi-guard"],
        "description": "Analog master filter: while its switch is ON, tracks 1-12, delay/reverb returns (always, TEST17) and the "
                       "input go through the analog FX block, whose filter (LP4/LP2/BP2/HP2/NO1/NO2/LPN or THRU), "
                       "FREQ and RESO follow the master filter (FX AMP and DRIVE stay the kit's). Edits only the audio "
                       "interrupt's copy of the live values and, after the OS's FX filter CV routine, its resonance CV "
                       "(RESO 63-127 climbs past the FX filter's own maximum: Polivoks-style" +
                       (", hot: twice the push" if PUSH == "hot" else "") + "); OFF gives the kit's routing back. "
                       "TEST15: controls on the FX track's SYN page 2 (page 0 made the SYN tab's second page: A FLTR, "
                       "B TYPE, C FREQ, D RESO, E CMP: MAIN / FX, what master-comp's dynamics act on, F IN: master-comp's "
                       "input meter, G empty (TEST17: RET removed, the returns always through the filter; id 412 unused); "
                       "earlier: G RET FLTR / KIT, the delay/reverb returns through the filter or where the kit "
                       "routes them; TEST15b); FLTR page 2 and AMP page 2 stock. With the delay's return in the FX block "
                       "the copy's FX AMP DEL is 0 (the OS mutes that send then anyway; its loop guard would cut the "
                       "delay's reverb send). TRIM is LVL (SYN page 1 H): the output level of the whole chain, always "
                       "on, applied by master-comp. The FX DRIVE is the kit's (SYN page 1 A; DRV's code removed in "
                       "TEST15b). Values global in RAM, not saved. MIDI on the FX CONTROL CH: CC 3/9/12/13 "
                       "and NRPN 1:48-1:51 (FLTR, TYPE, FREQ, RESO) in, and out on knob turns like the stock knobs.",
        "generated_by": "mods/master-filter/make_patch.py",
        "ids": IDS,
        "reso_push": "hot" if PUSH == "hot" else "normal",
        "symbols": {k: f"{syms[k]:#010x}" for k in (
            "mf_fx_hook", "mf_fx_hook_end", "mf_page_stub", "mf_apply", "mf_boot", "mf_get", "mf_set",
            "mf_p", "mf_mode", "mf_back", "mf_s", "mf_blocks", "mf_type_fmt", "mf_type_gfx",
            "mf_type_proto", "mf_tgfx_proto", "mf_freq_fmt", "mf_freq_proto", "mf_cc_lookup", "mf_nrpn_lookup",
            "mf_midi_in", "mf_midi_ins", "mf_midi_outs", "mf_post", "mf_posts", "mf_reso_cv", "mf_post_gain",
            "mf_post_s", "mf_ret_fmt", "mf_ret_proto", "mf_trim_fmt", "mf_trim_proto", "mf_cmp_fmt",
            "mf_cmp_proto", "mf_syn_pages", "mf_page0_s", "mf_page0_l")} | {"mf_cmp": f"{syms['mf_p'] + P_CMP:#010x}"},
        "midi": {"cc": MIDI_CCS, "nrpn": {k: f"{a}:{b}" for k, (a, b) in MIDI_NRPNS.items()}},
        "emac_sites": [],
        "patches": patches,
    }
    (HERE / "patch.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (REPO / "out" / "master-filter").mkdir(parents=True, exist_ok=True)
    (REPO / "out" / "master-filter" / "mf.lst").write_text(dis, encoding="utf-8")
    print(f"patch.json: {len(blob)} B at {CODE:#x}..{CODE + len(blob):#x}")


if __name__ == "__main__":
    main()
