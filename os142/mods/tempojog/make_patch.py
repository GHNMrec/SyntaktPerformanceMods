"""Mod tempojog (TEST32a): tj.c, the JOG page (hold [TEMPO]): a CDJ-style jog with a turning platter, and a
"JOG DISPLAY" line in SETTINGS > PERSONALIZE. One source for both OSes (-DOS142):

- linked in the mod area at +0x1E000 (up to the area's end, +0x1FFF0; past the grid's room);
- hooks: the audio interrupt's read of the tempo word on the internal-clock path (jsr tj_rate_isr); the TEMPO
  view's encoder handler entry (jmp tj_enc), and its vtable slots 0 / 1 (destructors), 2 (keys) and 4 (draw): ours
  while the view is the JOG page, stock's otherwise; the boot's call of the PERSONALIZE menu's constructor
  (jsr tj_pers_v: the stock menu, then our line appended).

    python mods/tempojog/make_patch.py [1.41|1.42] [--link]

TEST35 (Syntakt Performance Mods): LINK is shelved. The default build is tj.c with -DNOLINK (mod "tempojog-nolink",
patch.json): LINK's "no bridge" state compiled in as constants, no LINK chunk, the two MIDI input callbacks left
stock. --link would build the LINK version (mod "tempojog"); since TEST35 it no longer fits its chunks.
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

NOLINK = "--link" not in sys.argv              # TEST35: LINK is shelved; the default build has none (--link: with LINK)
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
OSV = _args[0] if _args else "1.41"
HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]       # this OS tree (os141 or os142)
sys.path[:0] = [str(REPO / "tools" / "unpack"), str(REPO / "tools" / "build")]
import eft  # noqa: E402
import modarea_layout  # noqa: E402

LOAD = 0x4000_0400
RAM, IMG = modarea_layout.RAM, modarea_layout.IMG
CODE_BASE, CODE_END = RAM + 0x1E000, RAM + 0x1FFF0
TL_BASE, TL_END = RAM + 0x15100, RAM + 0x15800     # TEST33a: the LINK code (heat's curve tables end +0x15010, gbus starts +0x15800)
PF_BASE, PF_END = RAM + 0x1D100, RAM + 0x1E000     # TEST34: the drawing (grid's grp chunk ends +0x1D0CC; its reservation now too)
PF2_BASE, PF2_END = RAM + 0x1B480, RAM + 0x1C000   # TEST34: the pitch, the glide, the keys (sid ends +0x1B458; its reservation too)
TOOLS = os.environ.get("M68K_ROOT", "~/tools/m68k/root")   # "/" = the distro cross-toolchain (apt: gcc-13-m68k-linux-gnu binutils-m68k-linux-gnu)
CFLAGS = "-mcpu=54418 -Os -ffreestanding -fno-builtin -nostdlib -fno-pic -fno-common -Wall -Wextra"
EXPORT = ("tj_ag", "tj_tick", "tj_rate_isr", "tj_enc", "tj_key", "tj_draw_v", "tj_dtor0", "tj_dtor1", "tj_pers_v", "tj_rate_c",
          "tj_enc_c", "tj_key_c", "tj_draw", "tj_gone", "tj_pers", "tj_inv_name", "tj_inv_tog", "tj_inv_delta",
          "tj_inv_draw", "tj_bend", "tj_debt", "tj_sp", "tj_bstep", "tj_sstep", "tj_rate", "tj_pos", "tj_strobe",
          "tj_lease", "tj_popt", "tj_touch", "tj_mode", "tj_load", "tj_brake", "tj_start", "tj_range",
          "tj_disp", "tj_view", "tj_func", "tj_skip", "tj_pop", "tj_phs",
          "tl_din", "tl_usb", "tl_mode", "tl_bar", "tl_off", "tl_mt", "tl_dk", "tl_fl", "tl_bb", "tl_ext", "tl_new",
          "tl_bt", "tl_t0", "tl_blk", "tl_seen", "tl_age", "tl_err", "tl_rem", "tl_pull", "tl_f8", "tl_run",
          "tl_f8t", "tl_f8d", "tl_pd", "tl_pu",
          "tj_copy", "tj_pitch", "tj_mt", "tj_page", "tj_btgt", "tj_ratio", "tj_semi", "tj_bars", "tj_pat", "tj_step",
          "tj_phr", "tj_gld", "tj_gl", "tj_gl_cur", "tj_gl_tgt", "tj_gl_step", "tj_gl_from", "tj_open_t", "tj_fpos",
          "tj_mfp", "tj_glide", "tj_commit", "tj_keys", "tj_perf_knob", "tj_perf_enter", "tj_tags", "tj_perform",
          "tj_tap", "tj_fp", "tj_fq", "tj_fqt", "tj_fown", "tj_fb", "tj_spec", "tj_spon", "tj_fw", "tj_dw")
SITES = {   # OS: ISR tempo read (+ old bytes), encoder entry, TempoView vtable, its slots 0/1/2/4, PERSONALIZE call
    "1.41": dict(isr=(0x400A_539E, "2039402d7010"), enc=0x4006_DF38, vt=0x401D_4214,
                 slots=("40187ac2", "40187ba0", "4006dd62", "4006d592"), pers=(0x4005_F41E, "4eb940057180"),
                 din=(0x4008_25D2, "487940102664"), usb=(0x4008_25E2, "4879401028ac"),
                 copy=(0x400A_4A06, "4eb940097952")),
    "1.42": dict(isr=(0x400A_5416, "2039402d7360"), enc=0x4006_DFB0, vt=0x401D_44B4,
                 slots=("40187c86", "40187d64", "4006ddda", "4006d60a"), pers=(0x4005_F496, "4eb9400571f8"),
                 din=(0x4008_264A, "487940102828"), usb=(0x4008_265A, "487940102a70"),
                 copy=(0x400A_4A7E, "4eb9400979ca")),
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sh(cmd: str) -> str:
    r = subprocess.run((["wsl.exe", "-e", "bash", "-lc", cmd] if os.name == "nt" else ["bash", "-lc", cmd]),
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"command failed:\n{cmd}\n{r.stderr}")
    return r.stdout + r.stderr


def build_blob():
    with tempfile.TemporaryDirectory(prefix="tj-") as tmp:
        tmp = Path(tmp)
        shutil.copy(HERE / "tj.c", tmp / "tj.c")
        w = eft.to_wsl_path(tmp)
        env = f"R={TOOLS}; export LD_LIBRARY_PATH=$R/usr/lib/x86_64-linux-gnu; cd {w}; "
        gcc = "$R/usr/bin/m68k-linux-gnu-gcc-13 -B$R/usr/libexec/gcc/m68k-linux-gnu/13/ -B$R/usr/bin/m68k-linux-gnu-"
        osd = (" -DOS142" if OSV == "1.42" else "") + (" -DNOLINK" if NOLINK else "")
        warn = sh(env + f"{gcc} {CFLAGS}{osd} -c tj.c -o tj.o")
        if "warning" in warn or "error" in warn:
            raise SystemExit(warn)
        (tmp / "tj.ld").write_text(f"SECTIONS {{ . = {CODE_BASE:#x}; .text : {{ *(.text) }} .rodata : {{ *(.rodata*) }} "
                                   f".data : {{ *(.data) }} . = {TL_BASE:#x}; .tl : {{ *(.text.tl) }} "
                                   f". = {PF_BASE:#x}; .pf : {{ *(.text.pf) }} . = {PF2_BASE:#x}; .pf2 : {{ *(.text.pf2) }} }}\n")
        sh(env + "$R/usr/bin/m68k-linux-gnu-ld -N -T tj.ld -e tj_rate_isr -o tj.elf tj.o")
        undef = sh(env + "$R/usr/bin/m68k-linux-gnu-nm -u tj.elf").strip()
        if undef:
            raise SystemExit(f"external symbols not allowed (libgcc?): {undef}")
        heads = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -h tj.elf")
        for name, size in re.findall(r"^\s*\d+\s+(\.\S+)\s+([0-9a-f]+)", heads, re.M):
            if name in (".bss", ".sbss") and int(size, 16):
                raise SystemExit("tj.c must not have .bss variables")
        sh(env + "$R/usr/bin/m68k-linux-gnu-objcopy -O binary -j .text -j .rodata -j .data tj.elf tj.bin")
        sh(env + "$R/usr/bin/m68k-linux-gnu-objcopy -O binary -j .tl tj.elf tl.bin")
        sh(env + "$R/usr/bin/m68k-linux-gnu-objcopy -O binary -j .pf tj.elf pf.bin")
        sh(env + "$R/usr/bin/m68k-linux-gnu-objcopy -O binary -j .pf2 tj.elf pf2.bin")
        syms = {}
        for line in sh(env + "$R/usr/bin/m68k-linux-gnu-nm tj.elf").splitlines():
            parts = line.split()
            if len(parts) == 3:
                syms[parts[2]] = int(parts[0], 16)
        dis = sh(env + "$R/usr/bin/m68k-linux-gnu-objdump -d -m m68k:isa-c:emac tj.elf")
        blob = (tmp / "tj.bin").read_bytes()
        tl = (tmp / "tl.bin").read_bytes()
        pf = (tmp / "pf.bin").read_bytes()
        pf2 = (tmp / "pf2.bin").read_bytes()
    return blob, tl, pf, pf2, syms, dis


def main() -> None:
    stock = REPO / "firmware" / f"Syntakt_OS{OSV}.syx"
    sec3 = eft.unpack(stock, REPO / "unpacked" / stock.stem, ids=[3])[3].read_bytes()
    blob, tl, pf, pf2, syms, dis = build_blob()
    print(f"sizes: main {len(blob)}/{CODE_END - CODE_BASE} LINK {len(tl)}/{TL_END - TL_BASE} "
          f"draw {len(pf)}/{PF_END - PF_BASE} tools {len(pf2)}/{PF2_END - PF2_BASE}")
    if PF_BASE + len(pf) > PF_END or PF2_BASE + len(pf2) > PF2_END:
        raise SystemExit("a TEST34 chunk does not fit")
    if CODE_BASE + len(blob) > CODE_END:
        print(f"MAIN does not fit: {len(blob)} B (max {CODE_END - CODE_BASE}), pf {len(pf)}"); raise SystemExit(1)
    if TL_BASE + len(tl) > TL_END:
        raise SystemExit(f"LINK chunk does not fit: {len(tl)} B (max {TL_END - TL_BASE})")
    if NOLINK and tl:
        raise SystemExit("NOLINK build has a LINK chunk")
    if not NOLINK and not tl:
        raise SystemExit("LINK chunk is empty")
    if re.search(r"\b(mac|msac|movclr)\w*\b|%acc|%macsr", dis):
        raise SystemExit("tj.c must not use the EMAC")
    clash = modarea_layout.runtime_clash(CODE_BASE, CODE_BASE + len(blob)) or \
        modarea_layout.runtime_clash(TL_BASE, TL_BASE + len(tl)) or \
        modarea_layout.runtime_clash(PF_BASE, PF_BASE + len(pf)) or \
        modarea_layout.runtime_clash(PF2_BASE, PF2_BASE + len(pf2))
    if clash:
        raise SystemExit(f"code overlaps a run-time buffer: {clash}")

    def fixed(addr: int, new: bytes, what: str, expect: str) -> dict:
        old = sec3[addr - LOAD:addr - LOAD + len(new)]
        if old.hex() != expect:
            raise SystemExit(f"{addr:#x}: unexpected bytes {old.hex()} (expected {expect})")
        return {"section": 3, "addr": f"{addr:#010X}", "len": len(new), "expect_sha256": sha(old),
                "hex": new.hex(), "what": what}

    S = SITES[OSV]
    j = lambda s: struct.pack(">I", syms[s])  # noqa: E731
    vt = S["vt"]
    patches = [{"section": 3, "addr": f"{IMG + CODE_BASE - RAM:#010X}", "len": len(blob), "append": True,
                "hex": blob.hex(), "ram": f"{CODE_BASE:#010x}", "what": "(mod area) tj.c"},
               {"section": 3, "addr": f"{IMG + PF_BASE - RAM:#010X}", "len": len(pf), "append": True,
                "hex": pf.hex(), "ram": f"{PF_BASE:#010x}", "what": "(mod area) tj.c: the JOG / PERFORM drawing"},
               {"section": 3, "addr": f"{IMG + PF2_BASE - RAM:#010X}", "len": len(pf2), "append": True,
                "hex": pf2.hex(), "ram": f"{PF2_BASE:#010x}", "what": "(mod area) tj.c: the pitch, the glide, the keys"},
               fixed(S["copy"][0], b"\x4e\xb9" + j("tj_copy"), "audio interrupt: the copy of the live values -> "
                     "tj_copy (TUNE follows the jog, VOL fades on a brake; MASTER TEMPO on = stock)", S["copy"][1]),
               fixed(S["isr"][0], b"\x4e\xb9" + j("tj_rate_isr"), "audio interrupt, internal clock: the tempo word "
                     "read -> tj_rate_isr (the jog)", S["isr"][1]),
               fixed(S["enc"], b"\x4e\xf9" + j("tj_enc") + b"\x4e\x71", "TEMPO view encoder handler: the JOG page's "
                     "knobs A-H -> tj_enc", "4feffff048d7041c"),
               fixed(vt, j("tj_dtor0"), "TEMPO view vtable slot 0 (destructor) -> tj_dtor0 (JOG ends)", S["slots"][0]),
               fixed(vt + 4, j("tj_dtor1"), "TEMPO view vtable slot 1 (deleting destructor) -> tj_dtor1",
                     S["slots"][1]),
               fixed(vt + 8, j("tj_key"), "TEMPO view vtable slot 2 (keys) -> tj_key (hold [TEMPO] = JOG)",
                     S["slots"][2]),
               fixed(vt + 16, j("tj_draw_v"), "TEMPO view vtable slot 4 (draw) -> tj_draw_v", S["slots"][3]),
               fixed(S["pers"][0], b"\x4e\xb9" + j("tj_pers_v"), "boot: the PERSONALIZE menu's constructor -> "
                     "tj_pers_v (+ JOG DISPLAY)", S["pers"][1])]
    if not NOLINK:
        patches.insert(1, {"section": 3, "addr": f"{IMG + TL_BASE - RAM:#010X}", "len": len(tl), "append": True,
                           "hex": tl.hex(), "ram": f"{TL_BASE:#010x}", "what": "(mod area) tj.c: the LINK chunk"})
        patches += [fixed(S["din"][0], b"\x48\x79" + j("tl_din"), "boot: the DIN MIDI input's byte callback -> tl_din "
                     "(LINK frames out, the rest to the OS's own)", S["din"][1]),
               fixed(S["usb"][0], b"\x48\x79" + j("tl_usb"), "boot: the USB MIDI input's buffer callback -> tl_usb "
                     "(LINK frames out, the rest to the OS's parser)", S["usb"][1])]
    export = [k for k in EXPORT if not (NOLINK and k.startswith("tl_"))]
    spec = {
        "name": "tempojog-nolink" if NOLINK else "tempojog",
        "version": "1.0-test35a" + ("-nolink" if NOLINK else ""),
        "os": OSV,
        "requires": ["modarea"],
        "description": "Syntakt Performance Mods: JOG page (hold [TEMPO], or push knob A in the TEMPO menu): A = the "
                       "jog (spin: a bend that follows the spin and eases back by LOAD; VINYL: push = touch, BRAKE / "
                       "HOLD / START), B = LOAD, C = START, D = BRAKE, E = RANGE, F = PHASE. SETTINGS > PERSONALIZE > "
                       "JOG DISPLAY: VINYL / CDJ (look and behaviour). [RIGHT]: PERFORM, a DJ filter on the master "
                       "filter (perf-filter or master-filter) with its curve over the mix's spectrum. Internal clock "
                       "only.",
        "generated_by": "mods/tempojog/make_patch.py",
        "symbols": {k: f"{syms[k]:#010x}" for k in export},
        "patches": patches,
    }
    if NOLINK:
        spec["description"] += " Without LINK (no CDJ bridge code, MIDI inputs stock)."
    (HERE / "patch.json").write_text(json.dumps(spec, indent=2) + "\n",
                                                                         encoding="utf-8")
    out = REPO / "out" / ("tempojog-nolink" if NOLINK else "tempojog")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tj.lst").write_text(dis, encoding="utf-8")
    print(f"patch.json ({OSV}): {len(blob)} B at {CODE_BASE:#x}..{CODE_BASE + len(blob):#x}, "
          f"LINK {len(tl)} B at {TL_BASE:#x}..{TL_BASE + len(tl):#x}, TEST34 {len(pf)} B at {PF_BASE:#x}")


if __name__ == "__main__":
    main()
