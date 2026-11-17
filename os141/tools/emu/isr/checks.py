"""Whole-interrupt checks of a MAX build against the stock OS 1.41 (the real audio interrupt, see board.py).

    python tools/emu/isr/checks.py BUILD.syx MANIFEST.json      # prints the report, exit 1 if a check fails

1. delay/reverb untouched: inputs and outputs of the delay and the reverb bit-identical to stock, block by block,
   with the mods at rest and working (FX3 sending, the compressor in MAIN and FX, FLTR ON with RET KIT);
2. FLTR ON = stock set up by hand: the DAC ring, both buses, the delay/reverb buffers and the CV struct (but the
   resonance CV, which the master filter rewrites on purpose) bit-identical to stock whose copy of the live values
   gets the same edits at the same point, for RET FLTR / KIT and the kit's returns direct / through the FX block;
3. the OS's loop guards with FLTR ON: the delay -> reverb send stays (TEST15b), the FX block's own DEL/REV sends
   are muted with RET FLTR (the returns are in the FX block) and work with RET KIT on a kit routed direct;
4. cost: instructions and peak stack per interrupt, stock vs the build at rest and with every mod busy.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import board  # noqa: E402
import rig  # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE  # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_D2, UC_M68K_REG_D3  # noqa: E402

ROOT = HERE.parents[2]
STOCK = ROOT / "firmware" / "Syntakt_OS1.41.syx"
SET = 0x4000_DA32                                  # kit parameter set (vparams sends our ids to the mods)
ID = {"COMP": 262, "GATE": 265, "SC": 266, "LVL": 431, "CMP": 432, "FLTR": 442, "TYPE": 443, "FREQ": 402,
      "RESO": 406, "RET": 412, "FX3_TYPE": 246, "FX3_FDBK": 251, "FX3_DEL": 249, "FX3_VOL": 253}
SND3 = 39                                          # fx3's per-track send (internal id, unused by the OS)
ROUT = [142 * t + 126 for t in range(12)]
TYPE, FREQ, RESO, ENV, FPAN = 1820, 1822, 1824, 1826, 1840


def setp(r, name, value):
    r.b.call(SET, [0x4700_0000, ID[name], value, 1], count=2_000_000)


def rigs(build, manifest, snd3=0, **kit):
    s, m = rig.Rig(STOCK), rig.Rig(build, manifest)
    for r in (s, m):
        r.kit(**kit)
        if snd3:
            for t in range(12):
                r.w16(rig.eng(t, SND3), snd3)
            r.sync()
    return s, m


# ---------------------------------------------------------------- 1
def delay_reverb_untouched(build, manifest, settings=(), blocks=60, snd3=0x6000):
    s, m = rigs(build, manifest, snd3=snd3)
    for name, v in settings:
        setp(m, name, v)
    for k in range(blocks):
        a, b = s.block(), m.block()
        for key in ("dly_in", "rev_in", "dly_out", "rev_out"):
            if a.get(key) != b.get(key):
                return f"block {k}: {key} differs"
    return None


# ---------------------------------------------------------------- 2
def by_hand(uc, ret_kit, freq, reso, type_):
    def edit(uc, addr, size, _):
        w = lambda off, v: uc.mem_write(rig.COPY + off, struct.pack(">H", v))  # noqa: E731
        r = lambda off: struct.unpack(">H", uc.mem_read(rig.COPY + off, 2))[0]  # noqa: E731
        for off in ROUT + [rig.IN_ROUT]:
            w(off, 0)
        if not ret_kit:
            w(rig.DLY_ROUT, 0)
            w(rig.REV_ROUT, 0)
        if r(rig.DLY_ROUT) == 0:
            w(rig.FX_DEL, 0)                         # TEST15b: muted send, no loop-guard cut
        w(TYPE, type_ << 8)
        w(FREQ, freq << 8)
        w(RESO, reso << 8)
        w(ENV, 0x4000)
        w(FPAN, 0x4000)
    uc.hook_add(UC_HOOK_CODE, edit, begin=0x400A_4F24, end=0x400A_4F24)   # where mf_fx_hook sits


def snap(r):
    cv = bytes(r.uc.mem_read(rig.CV, 1000))
    return {"dac": bytes(r.uc.mem_read(rig.DAC_RING, 0x1000)), "fxbus": tuple(r.b.longs(rig.FXBUS, 64)),
            "direct": tuple(r.b.longs(rig.DIRECT, 64)), "rev_out": tuple(r.b.longs(rig.REV_OUT, 64)),
            "dly_out": tuple(r.b.longs(rig.DLY_OUT, 64)), "cv": cv[:78] + cv[80:]}


def fltr_on_is_stock_by_hand(build, manifest, ret_kit, returns, blocks=40, freq=50, reso=90, type_=1):
    s, m = rigs(build, manifest, returns=returns)
    by_hand(s.uc, ret_kit, freq, reso, type_)
    for r in (s, m):
        r.word(rig.FX_DEL, 0x4000)
        r.word(rig.DLY + 12, 0x5000)                 # delay -> reverb
        r.sync()
    for name, v in (("TYPE", type_ << 8), ("FREQ", freq << 8), ("RESO", reso << 8),
                    ("RET", 0x100 if ret_kit else 0), ("FLTR", 0x100)):
        setp(m, name, v)
    for k in range(blocks):
        s.block(), m.block()
        a, b = snap(s), snap(m)
        for key in a:
            if a[key] != b[key]:
                return f"block {k}: {key} differs"
    return None


# ---------------------------------------------------------------- 3
def delay_into_reverb(r, blocks=30, fx_del=0x4000, returns=0x100):
    r.kit(sends=(0x6000, 0), returns=returns)       # tracks send to the delay only: the reverb hears the delay
    r.word(rig.DLY + 12, 0x7000)
    r.word(rig.FX_DEL, fx_del)
    r.sync()
    peak = 0.0
    for k in range(blocks):
        p = r.block()
        if k > 8:
            peak = max(peak, rig.rms(p["rev_in"]))
    return peak


def fx_block_sends(r, returns=0x100, blocks=4):
    """The FX block's own DEL/REV send gains as the mix computes them (0 = muted by the OS)."""
    got = {}
    r.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, _: got.__setitem__("DEL", uc.reg_read(UC_M68K_REG_D3)),
                  begin=0x4008_F686, end=0x4008_F686)
    r.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, _: got.__setitem__("REV", uc.reg_read(UC_M68K_REG_D2)),
                  begin=0x4008_F698, end=0x4008_F698)
    r.kit(sends=(0, 0), returns=returns)
    r.word(rig.FX_DEL, 0x6000)
    r.word(rig.FX_REV, 0x5000)
    r.sync()
    for _ in range(blocks):
        r.block()
    return {k: v != 0 for k, v in got.items()}


def loop_guards(build, manifest):
    out = {"stock: returns direct, FX AMP DEL 64": delay_into_reverb(rig.Rig(STOCK)),
           "stock: returns through the FX block, FX AMP DEL 64": delay_into_reverb(rig.Rig(STOCK), returns=0)}
    for ret in (0, 0x100):
        r = rig.Rig(build, manifest)
        setp(r, "FLTR", 0x100)
        setp(r, "RET", ret)
        out[f"build: FLTR ON RET {'KIT' if ret else 'FLTR'}, kit returns direct, FX AMP DEL 64"] = delay_into_reverb(r)
    sends = {"stock, returns direct": fx_block_sends(rig.Rig(STOCK)),
             "stock, returns through the FX block": fx_block_sends(rig.Rig(STOCK), returns=0)}
    for ret in (0, 0x100):
        r = rig.Rig(build, manifest)
        setp(r, "FLTR", 0x100)
        setp(r, "RET", ret)
        sends[f"build FLTR ON RET {'KIT' if ret else 'FLTR'}, kit returns direct"] = fx_block_sends(r)
    return out, sends


# ---------------------------------------------------------------- 4
BUSY = [("COMP", 100 << 8), ("GATE", 40 << 8), ("LVL", 96 << 8), ("SC", 2709), ("TYPE", 1 << 8),
        ("RESO", 100 << 8), ("FREQ", 60 << 8), ("FLTR", 0x100), ("RET", 0x100), ("FX3_TYPE", 1 << 8),
        ("FX3_FDBK", 100 << 8), ("FX3_DEL", 0x6000), ("FX3_VOL", 0x6000)]


def cost(r, blocks=12, warm=100):
    n, low = [0], [board.STACK_TOP]
    for _ in range(warm):                            # past boot transients (fx3 flushing its line, glides)
        r.block()
    r.uc.hook_add(UC_HOOK_CODE, lambda *a: n.__setitem__(0, n[0] + 1))
    r.uc.hook_add(UC_HOOK_MEM_WRITE, lambda uc, acc, addr, size, v, _: low.__setitem__(0, min(low[0], addr)),
                  begin=board.STACK_TOP - 0x20000, end=board.STACK_TOP - 1)
    entry = board.STACK_TOP - 0x100 + 8              # the interrupted context's A7
    total, depth = 0, 0
    for _ in range(blocks):
        n[0], low[0] = 0, board.STACK_TOP
        r.block()
        total += n[0]
        depth = max(depth, entry - low[0])
    return total // blocks, depth


def costs(build, manifest):
    s = rig.Rig(STOCK)
    s.kit()
    m = rig.Rig(build, manifest)
    m.kit()
    h = rig.Rig(build, manifest)
    h.kit()
    for t in range(12):
        h.w16(rig.eng(t, SND3), 0x6000)
    h.sync()
    for name, v in BUSY:
        setp(h, name, v)
    return {"stock": cost(s), "build at rest": cost(m), "build busy": cost(h)}


def main(build, manifest):
    bad = 0
    print("1. delay/reverb inputs and outputs vs stock:")
    for label, settings in (("mods at rest, FX3 sending", ()),
                            ("COMP 48, GATE 40, LVL +3 dB, CMP MAIN", (("COMP", 48 << 8), ("GATE", 40 << 8),
                                                                        ("LVL", 80 << 8))),
                            ("COMP 100, SC TRK1, CMP FX", (("COMP", 100 << 8), ("SC", 2709), ("CMP", 0x100))),
                            ("FLTR ON, RET KIT, COMP 64", (("FLTR", 0x100), ("RET", 0x100), ("COMP", 64 << 8)))):
        e = delay_reverb_untouched(build, manifest, settings)
        bad += e is not None
        print(f"   {label:40s} {'identical' if e is None else 'DIFFERENT: ' + e}")
    print("2. FLTR ON vs stock set up by hand (DAC ring, buses, delay/reverb, CVs):")
    for ret_kit in (False, True):
        for returns in (0x100, 0):
            e = fltr_on_is_stock_by_hand(build, manifest, ret_kit, returns)
            bad += e is not None
            print(f"   RET {'KIT ' if ret_kit else 'FLTR'}, kit returns {'direct' if returns else 'in FX'}: "
                  f"{'identical' if e is None else 'DIFFERENT: ' + e}")
    print("3. loop guards (reverb input from the delay, rms; FX block sends on/off):")
    rev, sends = loop_guards(build, manifest)
    for k, v in rev.items():
        print(f"   {k:62s} {v:.4f}")
    for k, v in sends.items():
        print(f"   {k:62s} {v}")
    ok3 = (rev["stock: returns through the FX block, FX AMP DEL 64"] == 0
           and all(v > 0 for k, v in rev.items() if k.startswith("build"))
           and sends["build FLTR ON RET FLTR, kit returns direct"] == {"DEL": False, "REV": False}
           and sends["build FLTR ON RET KIT, kit returns direct"] == {"DEL": True, "REV": True})
    bad += not ok3
    print("4. instructions and peak stack per interrupt:")
    c = costs(build, manifest)
    for k, (ins, depth) in c.items():
        print(f"   {k:16s} {ins:7d} instructions, peak stack {depth} B")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(Path(sys.argv[1]), Path(sys.argv[2])) else 0)
