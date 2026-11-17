"""TEST34 tempojog: pause, the pattern-anchored bar and the phrase counter, the pitch that follows the jog (MASTER
TEMPO), the brake fade, the tempo memories / reset with an exact glide, PERFORM and its DJ filter on master-filter's
own knob values, the snap. On the stock image with the mod's patches (test_tempojog.M), the screens on a booted rig.
- pause (the transport state 2): the bar position, the strobe and the phrase hold; play again carries on; stop = 0;
- a new pattern (0x800030B8) = the one and the phrase from bar 1; the pattern starting again (its step going back)
  = the one, and a part bar counts as a bar;
- the copy hook: the OS's copy builder runs, then every audio track with a TUNE (slot 18) gets 12 x log2(speed)
  semitones in 1/256 steps, MIDI / CY ALLOY / FX untouched, clamped; MASTER TEMPO on, or the jog at rest = stock;
  a VINYL brake fades AMP VOL (slot 48) over the last quarter of the speed;
- the glide: equal steps, never past the target, lands exactly; stored through the TEMPO view's setter, which
  takes over in the same block; CUT = the setter at once; LEVEL / [UP] / [DOWN] cancel it; LOCK refuses it;
  leaving the page mid-glide stores the target;
- the keys: [YES] MT (+ pop-up), [FUNC] + [YES] the phrase from 1, [FUNC] + [NO] reset, [FUNC] + [TRIG 1-4]
  130/140/150/160, [RIGHT] / [LEFT] the pages; [FUNC] + G / H: GLD / PHR;
- PERFORM: B = LP2 closing / THRU / HP2 opening on mf_p (its glide state started at the side's open end), C = RESO,
  B pushed = THRU, [FUNC] + B pushed = the master filter off; entering reads where the filter is;
- the screens: the phrase, MT, semitones, PAUSE, GLIDE, PERFORM (with and without the master filter)."""
import math
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_tempojog as J  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_D0  # noqa: E402

P142, SH, BEAT, Q, T120, VIEW, EV = J.P142, J.SH, J.BEAT, J.Q, J.T120, J.VIEW, J.EV
PLAYING, TEMPO = J.PLAYING, J.TEMPO
STEP = 0x43BD_83C0 if P142 else 0x43BD_73C0
PAT = 0x8000_30B8
SETTER = 0x4006_D3B6 if P142 else 0x4006_D33E
COPY_FN = 0x4009_79CA if P142 else 0x4009_7952
COPY = 0x8000_6348
pytestmark = J.pytestmark


class M(J.M):
    def __init__(self):
        super().__init__()
        uc = self.uc
        self.set_calls = []
        uc.mem_write(SETTER, b"\x4e\x75")                      # the TEMPO view's setter: logged, stores the tempo
        uc.hook_add(UC_HOOK_CODE, self._setter, begin=SETTER, end=SETTER)
        uc.mem_write(COPY_FN, b"\x20\x3c" + struct.pack(">I", COPY) + b"\x4e\x75")   # the copy builder: d0 = copy

    def _setter(self, uc, a, s, _):
        sp = uc.reg_read(UC_M68K_REG_A7)
        view, t = struct.unpack(">Ii", uc.mem_read(sp + 4, 8))
        self.set_calls.append((view, t))
        self.tempo(t)

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))

    def w16(self, a, v):
        self.uc.mem_write(a, struct.pack(">H", v & 0xFFFF))

    def fpos(self):
        return struct.unpack(">b", self.uc.mem_read(self.sym["tj_fpos"], 1))[0]

    def r16(self, a):
        return struct.unpack(">H", self.uc.mem_read(a, 2))[0]

    def u32(self, n):
        return struct.unpack(">I", bytes(self.uc.mem_read(self.sym[n], 4)))[0]

    def play(self, st=1):
        self.w32(PLAYING, st)

    def fkey(self, code, func=True):
        if func:
            self.key(1, 1)
        self.key(code, 1)
        self.key(code, 0)
        if func:
            self.key(1, 0)


@pytest.fixture
def m():
    return M()


# ---- pause, the anchor, the phrase ----

def test_pause_holds_everything(m):
    m.jog()
    m.play(1)
    m.w32(PAT, 0x4700_1000)
    for _ in range(1000):
        m.rate()
    pos, bars = m.u32("tj_pos"), m.u32("tj_bars")
    assert pos == (1000 * T120) % (4 * BEAT)
    m.play(2)                                                 # [PLAY]: paused
    for _ in range(3000):
        m.rate()
    assert m.u32("tj_pos") == pos and m.u32("tj_bars") == bars
    m.play(1)                                                 # [PLAY] again: carries on from there
    m.rate()
    assert m.u32("tj_pos") == pos + T120
    m.play(0)
    m.rate()
    assert m.u32("tj_pos") == 0 and m.u32("tj_bars") == 0


def test_new_pattern_is_the_one_and_phrase_restarts(m):
    m.jog()
    m.play(1)
    m.w32(PAT, 0x4700_1000)
    m.w16(STEP, 0)
    for _ in range(3000 * 5):                                 # 5 bars at 120 BPM (a bar = 3000 blocks)
        m.rate()
    assert m.u32("tj_bars") == 5
    for _ in range(700):
        m.rate()
    m.w32(PAT, 0x4700_2000)                                   # a new pattern / song row
    m.rate()
    assert m.u32("tj_bars") == 0 and m.u32("tj_pos") == T120


def test_pattern_restart_is_the_one_and_its_part_bar_counts(m):
    m.jog()
    m.play(1)
    m.w32(PAT, 0x4700_1000)
    m.w16(STEP, 0)
    m.rate()
    for k in range(1, 12):                                    # a 12-step pattern: 3 beats, then it starts again
        m.w16(STEP, k)
        for _ in range(187):
            m.rate()
    pos = m.u32("tj_pos")
    assert pos > 2 * BEAT and m.u32("tj_bars") == 0
    m.w16(STEP, 0)
    m.rate()
    assert m.u32("tj_pos") == T120 and m.u32("tj_bars") == 1  # the one again; the 3-beat bar counted
    for k in range(1, 4):                                     # whole-bar restart right after our own wrap: once
        m.w16(STEP, k)
        m.rate()
    m.uc.mem_write(m.sym["tj_pos"], struct.pack(">I", 4 * BEAT - T120))
    m.rate()                                                  # our bar wraps ...
    assert m.u32("tj_bars") == 2
    m.w16(STEP, 0)
    m.rate()                                                  # ... and the pattern restarts: no double count
    assert m.u32("tj_bars") == 2


def test_phrase_keys(m):
    m.jog()
    m.w32(m.sym["tj_bars"], 13)
    m.fkey(12)                                                # [FUNC] + [YES]: bar 1
    assert m.u32("tj_bars") == 0 and m.u8("tj_mt") == 0
    m.key(1, 1)
    m.knob(8, 1)                                              # [FUNC] + H: PHR 32
    m.knob(8, 5)                                              # ... 64, then stays
    m.knob(8, 1)
    m.knob(7, -1)                                             # [FUNC] + G: GLD 2 bars
    m.key(1, 0)
    assert m.u8("tj_phr") == 3 and m.u8("tj_gld") == 2 and m.s32("tj_debt") == 0


# ---- the pitch ----

def semis_ref(x):
    return max(-24 * 256, 3072 * math.log2(x / 4096)) if x > 1024 else -24 * 256


def run_pitch(m, ratio, machines, tunes=None, vols=None):
    for t in range(12):
        b = COPY + 142 * t
        m.uc.mem_write(0x8000_2F50 + t, bytes([machines[t]]))
        m.w16(b + 64, (tunes or [0x4000] * 12)[t])
        m.w16(b + 124, (vols or [0x6000] * 12)[t])
    m.w32(m.sym["tj_ratio"], ratio)
    m.call(m.sym["tj_copy"], [0x8000_21B0])
    assert m.uc.reg_read(UC_M68K_REG_D0) & 0xFFFFFFFF == COPY
    return [m.r16(COPY + 142 * t + 64) for t in range(12)], [m.r16(COPY + 142 * t + 124) for t in range(12)]


MACH = [37, 0, 36, 44, 32, 7, 38, 6, 8, 11, 19, 31]          # SY BITS, BD MODERN, ..., CY ALLOY, MIDI, analog


def test_pitch_follows_every_tune_track(m):
    for x in (4096 * 103 // 100, 4096 * 90 // 100, 4096 * 150 // 100, 4096 * 6 // 10):
        tu, vo = run_pitch(m, x, MACH)
        want = semis_ref(x)
        for t, mc in enumerate(MACH):
            if mc in (44, 32, 19):
                assert tu[t] == 0x4000                        # no TUNE in slot 18 (CY ALLOY), MIDI, no TUNE
            else:
                assert abs(tu[t] - 0x4000 - want) <= 3, (x, mc, tu[t] - 0x4000, want)   # 1/16-octave table: < 1.2 cent
        assert vo == [0x6000] * 12                            # no brake: no fade


def test_pitch_rest_mt_and_clamp(m):
    tu, _ = run_pitch(m, 4096, MACH)
    assert tu == [0x4000] * 12 and m.s32("tj_semi") == 0      # the jog at rest: stock
    m.set8("tj_mt", 1)
    tu, _ = run_pitch(m, 4096 * 12 // 10, MACH)
    assert tu == [0x4000] * 12 and m.s32("tj_semi") == 0      # MASTER TEMPO on: stock
    m.set8("tj_mt", 0)
    tu, _ = run_pitch(m, 4096 * 2, MACH, tunes=[0x7F00] * 12)
    assert all(v == 0x7FFF or MACH[t] in (44, 32, 19) for t, v in enumerate(tu))   # the TUNE's own end
    tu, _ = run_pitch(m, 900, MACH)
    assert all(v == 0x4000 - 24 * 256 or MACH[t] in (44, 32, 19) for t, v in enumerate(tu))   # floor -24


def test_brake_fades_the_last_quarter(m):
    m.set8("tj_touch", 1)
    for x, f in ((2048, 1.0), (1024, 1.0), (512, 0.5), (0, 0.0)):
        _, vo = run_pitch(m, x, MACH)
        for t, mc in enumerate(MACH):
            want = 0x6000 if mc == 32 else int(0x6000 * f)    # every audio track (CY ALLOY too), not MIDI
            assert abs(vo[t] - want) <= 2, (x, mc, vo[t])
    m.set8("tj_mt", 1)
    _, vo = run_pitch(m, 512, MACH)
    assert vo == [0x6000] * 12                                # MASTER TEMPO on: the brake as TEST33a


def test_the_ratio_is_the_jogs_not_locks(m):
    m.jog()
    m.knob(1, 1)
    for _ in range(100):
        m.rate()
    assert m.s32("tj_ratio") > 4096
    m.uc.mem_write(m.sym["tj_bend"], bytes(4))
    m.uc.mem_write(m.sym["tj_btgt"], bytes(4))
    m.play(1)
    if J.NOLINK:
        return                                                # no LINK: no LOCK correction to tell apart
    m.set8("tl_mode", 1)
    m.uc.mem_write(m.sym["tl_rem"], struct.pack(">i", BEAT // 8))
    m.w32(m.sym["tl_age"], 0)
    r = m.rate()
    assert r != T120 and m.s32("tj_ratio") == 4096            # LOCK's correction: no pitch


# ---- the glide ----

def test_memory_glides_exactly_and_the_setting_takes_over(m):
    m.tempo(130 * 120)
    m.jog()
    m.fkey(25)                                                # [FUNC] + [TRIG 2]: 140
    rates, n = [], 0
    while m.u8("tj_gl") == 1 and n < 20000:
        rates.append(m.rate())
        n += 1
    assert all(a <= b for a, b in zip(rates, rates[1:]))      # never back
    assert max(rates) == 140 * 120 and rates[-1] == 140 * 120 # never past, and there exactly
    bars = 4 * 4 * (BEAT / (135 * 120))
    assert abs(n - bars) / bars < 0.01                        # 4 bars at the mean tempo
    assert m.u8("tj_gl") == 2 and m.set_calls == []
    m.call(m.sym["tj_commit"], [VIEW])                        # the draw stores it through the TEMPO view
    assert m.set_calls == [(VIEW, 140 * 120)]
    assert m.rate() == 140 * 120 and m.u8("tj_gl") == 0       # the setting took over in that same block
    assert m.rate() == 140 * 120


def test_glide_down_cut_and_cancel(m):
    m.tempo(150 * 120)
    m.jog()
    m.fkey(24)                                                # 130: down
    rates = [m.rate() for _ in range(25000)]
    assert min(rates) == 130 * 120 and all(a >= b for a, b in zip(rates, rates[1:]))
    m2 = M()
    m2.tempo(150 * 120)
    m2.jog()
    m2.key(1, 1)
    for _ in range(5):
        m2.knob(7, -1)                                        # GLD: CUT
    m2.key(1, 0)
    m2.fkey(27)                                               # 160 at once
    assert m2.set_calls == [(VIEW, 160 * 120)] and m2.u8("tj_gl") == 0
    m3 = M()
    m3.tempo(130 * 120)
    m3.jog()
    m3.fkey(26)
    for _ in range(100):
        m3.rate()
    m3.knob(9, 1)                                             # LEVEL: the tempo, stock's: the glide gives way
    assert m3.u8("tj_gl") == 0 and m3.rate() == 130 * 120


def test_reset_lock_and_leaving(m):
    m.tempo(132 * 120)
    m.call(m.sym["tj_key"], [VIEW, EV]) if False else None
    m.uc.mem_write(EV, bytes(32))
    m.uc.mem_write(EV + 12, struct.pack(">II", 8, 9))         # hold [TEMPO]: JOG opens at 132
    m.call(m.sym["tj_key"], [VIEW, EV])
    assert m.s32("tj_open_t") == 132 * 120
    m.tempo(140 * 120)
    m.fkey(13)                                                # [FUNC] + [NO]: back to 132
    assert m.u8("tj_gl") == 1 and m.s32("tj_gl_tgt") == 132 * 120 << 8
    for _ in range(50):
        m.rate()
    m.call(m.sym["tj_gone"], [VIEW])                          # leaving mid-glide: the target at once
    assert m.set_calls == [(VIEW, 132 * 120)] and m.rate() == 132 * 120 and m.u8("tj_gl") == 0
    if J.NOLINK:
        return                                                # no LINK: no LOCK to refuse a glide
    m2 = M()
    m2.jog()
    m2.set8("tl_mode", 1)
    m2.w32(m2.sym["tl_mt"], 128 * 120)
    m2.fkey(24)
    assert m2.u8("tj_gl") == 0 and m2.set_calls == []         # LOCK: the master rules


# ---- keys and PERFORM ----

def test_mt_and_pages(m):
    m.jog()
    assert m.key(12, 1) == 1
    m.key(12, 0)
    assert m.u8("tj_mt") == 1 and m.u8("tj_pop") == 10
    m.key(12, 1)
    assert m.u8("tj_mt") == 0
    m.key(17, 1)
    assert m.u8("tj_page") == 1
    m.key(16, 1)
    assert m.u8("tj_page") == 0
    n = len(m.reached)
    m.key(24, 1)                                              # [TRIG 1] without [FUNC]: stock's
    assert m.reached[n:] == [J.STOCK_KEY]


# PERFORM (TEST35: the fine DJ filter, the spectrum): tests/test_perfmods.py


# ---- the screens (booted image) ----

@pytest.fixture(scope="module")
def rig():
    import seqrig as S
    r = S.Rig(("modarea", "tempojog"))                       # TEST35: patch.json is the no-LINK build
    r.g.call(0x401A_A8B0 if P142 else 0x401A_A614, [])
    return r


def shot(rig, setup):
    uc, g, sym = rig.uc, rig.g, rig.sym
    texts = []
    TEXT = 0x400F_8BD0 if P142 else 0x400F_8A0C

    def tx(u, a, s, _):
        sp = u.reg_read(UC_M68K_REG_A7)
        w = struct.unpack(">7I", u.mem_read(sp + 4, 28))
        texts.append(bytes(u.mem_read(w[6], 24)).split(b"\0")[0].decode())
    h = uc.hook_add(UC_HOOK_CODE, tx, begin=TEXT, end=TEXT)
    for n in ("tj_mt", "tj_page", "tj_gl", "tj_touch", "tj_func", "tj_popt", "tj_pop"):
        uc.mem_write(sym[n], bytes(4 if n in ("tj_popt",) else 1))
    uc.mem_write(sym["tj_semi"], bytes(4))
    uc.mem_write(PLAYING, struct.pack(">I", 0))
    uc.mem_write(TEMPO, struct.pack(">i", 130 * 120))
    uc.mem_write(sym["tj_rate"], struct.pack(">i", 130 * 120))
    uc.mem_write(sym["tj_view"], struct.pack(">I", VIEW))
    uc.mem_write(sym["tj_bars"], struct.pack(">I", 0))
    setup(uc, sym)
    can = 0x47C0_0000
    uc.mem_write(can, struct.pack(">5I", 0, 128, 64, 2, can + 0x100))
    uc.mem_write(can + 0x100, bytes(0x400))
    g.call(sym["tj_draw"], [VIEW, can])
    uc.hook_del(h)
    return texts


def test_screens(rig):
    w8 = lambda uc, a, v: uc.mem_write(a, bytes([v]))         # noqa: E731
    w32 = lambda uc, a, v: uc.mem_write(a, struct.pack(">i", v))   # noqa: E731
    assert shot(rig, lambda uc, s: w32(uc, s["tj_bars"], 8))[0] == "9/16"
    t = shot(rig, lambda uc, s: (w8(uc, s["tj_mt"], 1)))
    assert "MT" in t and "(LEV)" in t
    t = shot(rig, lambda uc, s: (w32(uc, s["tj_semi"], 136), w32(uc, s["tj_rate"], 134 * 120)))
    assert "+0.53 ST" in t and "134.00" in t
    t = shot(rig, lambda uc, s: uc.mem_write(PLAYING, struct.pack(">I", 2)))
    assert "PAUSE" in t
    t = shot(rig, lambda uc, s: (w8(uc, s["tj_gl"], 1), w32(uc, s["tj_gl_tgt"], 140 * 120 << 8),
                                 w32(uc, s["tj_gl_cur"], 136 * 120 << 8), w32(uc, s["tj_gl_from"], 130 * 120 << 8)))
    assert "TO 140.00" in t and "GLIDE" in t
    t = shot(rig, lambda uc, s: (w8(uc, s["tj_page"], 1), w32(uc, s["tj_mfp"], 0)))
    assert t == ["NO MASTER FILTER"]                          # TEST35: PERFORM is the whole screen (TEST38b: no slider)
    t = shot(rig, lambda uc, s: (w8(uc, s["tj_func"], 1)))
    assert {"LOAD", "PHR", "GLD", "T2 140", "NO RST", "YES P1", "16", "4B"} <= set(t)
