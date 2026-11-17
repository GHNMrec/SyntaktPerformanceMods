"""TEST32a tempojog: the JOG page (hold [TEMPO]) and SETTINGS > PERSONALIZE > JOG DISPLAY, on the stock image with
the mod's patches.
- the sites: the audio interrupt's tempo read (internal clock) -> tj_rate_isr; the TEMPO view's encoder entry, its
  vtable slots 0 / 1 (destructors), 2 (keys) and 4 (draw); the boot's call of the PERSONALIZE menu's constructor;
- at rest the clock is stock's, and the TEMPO menu is stock again (keys, knobs and draw of a view that isn't JOG go
  straight to the OS);
- the ring (A): a bend that follows the spin, eases back exactly to the set tempo, capped at RANGE; LOAD = coasting;
- VINYL touch (A pushed): BRAKE to a stop in its time, HOLD fires nothing, START back in its time; turning while held
  walks the beat on by exactly 1/8 beat a click, never backwards; CDJ mode ignores the push;
- PHASE (H): exactly n x 1/360 beat, at most a quarter beat waiting, ahead at most double speed;
- the real interrupt path: 192 subticks a second at 120 BPM; a 90-click PHASE push fires exactly 24 more; a held
  platter fires none;
- keys: hold [TEMPO] (code 8, held, no FUNC) or knob A pushed opens JOG; [FUNC] + hold stays stock's (GROOVE);
  the destructor ends JOG and lets a held platter go;
- the screen (booted image): the JOG page's texts and its marker turning once a bar;
- PERSONALIZE: a tenth line, JOG DISPLAY, built like REMEMBER SUBPAGE's; [YES] / [LEFT] / [RIGHT] set it."""
import json
import os
import struct
import sys
from pathlib import Path

import pytest

pytest.importorskip("unicorn")
from unicorn import UC_ARCH_M68K, UC_HOOK_CODE, UC_MODE_BIG_ENDIAN, Uc  # noqa: E402
from unicorn.m68k_const import UC_CPU_M68K_ANY, UC_M68K_REG_A0, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_SR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P142 = ROOT.name in ("max142", "os142")
OSV = "1.42" if P142 else "1.41"
SEC3 = ROOT / "unpacked" / f"Syntakt_OS{OSV}" / "section_3_MAIN_OS.bin"
SPEC = ROOT / "mods" / "tempojog" / os.environ.get("JOG_SPEC", "patch.json")   # JOG_SPEC=patch_nolink.json: the no-LINK build
NOLINK = SPEC.exists() and json.loads(SPEC.read_text())["name"] == "tempojog-nolink"   # TEST35: the default
pytestmark = pytest.mark.skipif(not (SEC3.exists() and SPEC.exists()), reason="needs the stock image unpacked")
LOAD, RET = 0x4000_0400, 0x4FF0_0000
SH = 0x78 if P142 else 0                                    # code shift 1.41 -> 1.42 in these stretches
TEMPO = 0x402D_7360 if P142 else 0x402D_7010
PLAYING = 0x43BD_83BC if P142 else 0x43BD_73BC
ISR0, ISR_FIRE, ISR_END = 0x400A_5398 + SH, 0x400A_53D4 + SH, 0x400A_5446 + SH
ENC, ENC_REST = 0x4006_DF38 + SH, 0x4006_DF40 + SH
VT = 0x401D_44B4 if P142 else 0x401D_4214
STOCK_KEY, STOCK_DRAW = 0x4006_DD62 + SH, 0x4006_D592 + SH
DTOR0, DTOR1 = (0x4018_7C86, 0x4018_7D64) if P142 else (0x4018_7AC2, 0x4018_7BA0)
REDRAW = 0x400F_FE22 if P142 else 0x400F_FC5E
PERS_SITE, PERS_CTOR = (0x4005_F496, 0x4005_71F8) if P142 else (0x4005_F41E, 0x4005_7180)
BEAT = 10_800_000
T120 = 120 * 120
Q = 65536
VIEW, EV = 0x47A0_0000, 0x47A1_0000


class M:
    """the raw image with the patches; the OS routines the page calls are stubs that log"""
    def __init__(self):
        self.spec = json.loads(SPEC.read_text())
        self.sym = {k: int(v, 16) for k, v in self.spec["symbols"].items()}
        uc = self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, cpu=UC_CPU_M68K_ANY)
        for a, s in ((0x4000_0000, 0x1000_0000), (0x8000_0000, 0x1_0000), (0xFC00_0000, 0x10_0000)):
            uc.mem_map(a, s)
        uc.mem_write(LOAD, SEC3.read_bytes())
        for p in self.spec["patches"]:
            uc.mem_write(int(p["ram"], 16) if p.get("append") else int(p["addr"], 16), bytes.fromhex(p["hex"]))
        uc.mem_write(RET, b"\x4e\x71" * 4)
        self.reached = []
        self.stubs()
        self.tempo(T120)

    def stubs(self):
        uc = self.uc
        for a in (STOCK_KEY, STOCK_DRAW, REDRAW, DTOR0, DTOR1, ENC_REST):
            uc.mem_write(a, (b"\x4f\xef\x00\x10" if a == ENC_REST else b"") + b"\x70\x07\x4e\x75")   # moveq #7,d0; rts
            uc.hook_add(UC_HOOK_CODE, lambda u, x, s, _: self.reached.append(x), begin=a, end=a)

    def tempo(self, t):
        self.uc.mem_write(TEMPO, struct.pack(">i", t))

    def call(self, fn, args=(), sp=0x4FE0_0000, until=RET):
        uc = self.uc
        frame = struct.pack(">I", RET) + b"".join(struct.pack(">I", a & 0xFFFFFFFF) for a in args)
        uc.mem_write(sp - len(frame), frame)
        uc.reg_write(UC_M68K_REG_SR, 0x2000)
        uc.reg_write(UC_M68K_REG_A7, sp - len(frame))
        uc.emu_start(fn, until, count=5_000_000)

    def d0(self):
        return struct.unpack(">i", struct.pack(">I", self.uc.reg_read(UC_M68K_REG_D0) & 0xFFFFFFFF))[0]

    def rate(self):
        self.call(self.sym["tj_rate_c"])
        return self.d0()

    def s32(self, n):
        return struct.unpack(">i", bytes(self.uc.mem_read(self.sym[n], 4)))[0]

    def u8(self, n):
        return self.uc.mem_read(self.sym[n], 1)[0]

    def set8(self, n, v):
        self.uc.mem_write(self.sym[n], bytes([v]))

    def jog(self):
        self.uc.mem_write(self.sym["tj_view"], struct.pack(">I", VIEW))

    def key(self, code, flags, view=VIEW):
        self.uc.mem_write(EV, bytes(32))
        self.uc.mem_write(EV + 12, struct.pack(">II", code, flags))
        self.call(self.sym["tj_key"], [view, EV])
        return self.d0()

    def knob(self, n, d, held=0, view=VIEW):
        self.uc.mem_write(EV, bytes(32))
        self.uc.mem_write(EV + 12, struct.pack(">ii", n, d))
        self.uc.mem_write(EV + 20, bytes([held]))
        self.call(ENC, [view, EV])
        return self.d0()


@pytest.fixture
def m():
    return M()


def test_sites(m):
    got = {int(p["addr"], 16): p["hex"] for p in m.spec["patches"] if not p.get("append")}
    for site in ((0x4008_264A, 0x4008_265A) if P142 else (0x4008_25D2, 0x4008_25E2)):
        if NOLINK:
            assert site not in got                            # no LINK: the MIDI inputs stay stock
        else:
            got.pop(site)                                     # the MIDI inputs (LINK): test_tempojog_link
    got.pop(0x400A_4A7E if P142 else 0x400A_4A06)             # TEST34: the copy hook (test_tempojog34.py)
    s = m.sym
    assert got == {0x400A_539E + SH: "4eb9%08x" % s["tj_rate_isr"], ENC: "4ef9%08x4e71" % s["tj_enc"],
                   VT: "%08x" % s["tj_dtor0"], VT + 4: "%08x" % s["tj_dtor1"], VT + 8: "%08x" % s["tj_key"],
                   VT + 16: "%08x" % s["tj_draw_v"], PERS_SITE: "4eb9%08x" % s["tj_pers_v"]}
    stock = SEC3.read_bytes()
    assert stock[PERS_SITE - LOAD:PERS_SITE - LOAD + 6].hex() == "4eb9%08x" % PERS_CTOR


def test_at_rest_the_clock_is_stock(m):
    assert [m.rate() for _ in range(10)] == [T120] * 10


def test_the_tempo_menu_is_stock_again(m):
    other = 0x47A3_0000                                        # a TEMPO view that isn't JOG
    for n in (1, 2, 3, 4, 5, 8, 9):
        m.reached.clear()
        m.knob(n, 1, view=other)
        assert m.reached == [ENC_REST]
    m.reached.clear()
    assert m.key(13, 0x11, view=other) == 7 and m.reached == [STOCK_KEY]
    m.reached.clear()
    m.key(8, 0xB, view=other)                                  # [FUNC] + hold [TEMPO]: stock's (tap tempo -> GROOVE)
    assert m.reached == [STOCK_KEY] and m.s32("tj_view") == 0
    m.reached.clear()
    m.call(m.sym["tj_draw"], [other, 0x47C0_0000])
    assert m.reached == [STOCK_DRAW]


def test_hold_tempo_opens_jog(m):
    assert m.key(8, 0x9) == 1 and m.s32("tj_view") == VIEW      # [TEMPO] held, no FUNC
    m.reached.clear()
    assert m.key(8, 0x0) == 1 and m.reached == [REDRAW] * 0     # its release: ours, nothing happens
    m.key(13, 0x11)
    assert m.reached == [STOCK_KEY]                            # [NO]: the OS closes the view as for TEMPO
    m.call(m.sym["tj_dtor0"], [VIEW])
    assert m.s32("tj_view") == 0 and m.reached[-1] == DTOR0


def test_knob_a_push_opens_jog_and_its_release_is_no_touch(m):
    m.key(40, 1)
    assert m.s32("tj_view") == VIEW
    m.key(40, 0)
    assert m.u8("tj_touch") == 0
    m.key(40, 1)
    assert m.u8("tj_touch") == 1                              # the next push is a touch (VINYL)


def test_the_ring_follows_the_spin_and_eases_back(m):
    """TEST34: a click = 0.25 % target whatever the turn's speed; the bend glides to it (no step) while the target eases
    back (TEST35: LOAD 3 gives most of it back within ~0.1 s, so a click peaks under its quarter percent)"""
    m.jog()
    m.knob(1, 1)
    first = m.rate()
    assert T120 <= first < T120 * 1.0015                      # it glides in: not the whole click at once
    peak = max(m.rate() for _ in range(300))
    assert T120 * 1.0008 < peak <= T120 * 1.0025 + 1          # up to a quarter percent
    m2 = M()
    m2.jog()
    m2.knob(1, 9)                                             # an accelerated event: still one click
    assert max(m2.rate() for _ in range(300)) == peak
    slow, fast = [], []
    for speed, out in ((1, slow), (4, fast)):
        m.uc.mem_write(m.sym["tj_bend"], bytes(4))
        m.uc.mem_write(m.sym["tj_btgt"], bytes(4))
        for b in range(1500):
            if b % (40 // speed) == 0:
                m.knob(1, 1)
            out.append(m.rate())
    assert max(fast) > max(slow) > T120                        # spinning faster bends further
    for _ in range(6000):
        r = m.rate()
    assert r == T120 and m.s32("tj_bend") == 0 and m.s32("tj_btgt") == 0   # back exactly to the set tempo
    for _ in range(200):                                      # a wild spin backwards: capped at RANGE (10 %)
        m.knob(1, -1)
    assert m.s32("tj_btgt") == -10 * (Q // 100) * 16      # Q20
    for _ in range(3):
        m.knob(5, 1)                                          # TEST35: E RANGE, 3 detents: 16 %
    for _ in range(300):
        m.knob(1, -1)
    assert m.s32("tj_btgt") == -16 * (Q // 100) * 16


def test_load_is_the_jogs_weight(m):
    """light eases back quickly, heavy coasts on: after letting go for 0.2 s"""
    m.jog()
    left = {}
    for load in (1, 8):
        m.uc.mem_write(m.sym["tj_bend"], bytes(4))
        m.uc.mem_write(m.sym["tj_btgt"], bytes(4))
        m.set8("tj_load", load)
        for b in range(1500):                                 # one second of steady spinning, 20 clicks a second
            if b % 75 == 0:
                m.knob(1, 1)
            m.rate()
        for _ in range(300):                                  # let go for 0.2 s
            m.rate()
        left[load] = m.s32("tj_bend")
    assert 0 <= left[1] < left[8] / 3                         # light has mostly gone, heavy coasts on


def test_touch_brakes_holds_and_starts(m):
    m.jog()
    m.key(40, 1)                                              # VINYL (default): touch
    rates = [m.rate() for _ in range(700)]
    stop = rates.index(0)
    assert 595 <= stop <= 605                                 # BRAKE 0.4 s = 600 blocks
    assert all(a >= b for a, b in zip(rates, rates[1:]))      # slowing all the way
    assert [m.rate() for _ in range(1000)] == [0] * 1000      # HOLD
    m.key(40, 0)
    rates = [m.rate() for _ in range(400)]
    back = rates.index(T120)
    assert 295 <= back <= 305 and rates[-1] == T120           # START 0.2 s = 300 blocks, then exactly stock
    m.knob(4, -8)                                             # TEST35: D BRAKE, 2 detents a step: 0, stops at once
    m.key(40, 1)
    assert m.rate() == 0


def test_cdj_mode_ignores_the_push(m):
    """TEST35: knob B is LOAD now; SETTINGS > PERSONALIZE > JOG DISPLAY sets the look and the behaviour"""
    m.jog()
    m.knob(2, -1)
    assert m.u8("tj_mode") == 1                               # B: not the mode any more
    fn, box = 0x47B0_0000, 0x47B0_0010
    m.uc.mem_write(fn, struct.pack(">I", box))
    m.uc.mem_write(box, struct.pack(">I", 0x47B1_0000))
    m.call(m.sym["tj_inv_delta"], [fn, 0, 1])                 # PERSONALIZE: CDJ
    assert m.u8("tj_disp") == 1 and m.u8("tj_mode") == 0
    m.key(40, 1)
    assert m.u8("tj_touch") == 0 and [m.rate() for _ in range(100)] == [T120] * 100


def test_crank_walks_the_beat_on_never_back(m):
    m.jog()
    m.knob(4, -8)                                             # BRAKE 0
    m.key(40, 1)
    assert m.rate() == 0
    m.knob(1, 8, held=1)                                      # 8 clicks forward while held: one beat
    moved = sum(m.rate() for _ in range(3000))
    assert moved == BEAT
    m.knob(1, -8, held=1)                                     # backwards: nothing (it can't run in reverse)
    assert m.s32("tj_debt") == 0 and sum(m.rate() for _ in range(100)) == 0


@pytest.mark.parametrize("clicks", [5, -5, 90, -90, 100, -100])
def test_phase_moves_exactly(m, clicks):
    """TEST35: F, a step every 2 detents (pressed: 10), caught up at no more than 4 % faster or slower"""
    m.jog()
    one = 1 if clicks > 0 else -1
    for _ in range(2 * abs(clicks)):
        m.knob(6, one)
    want = max(-BEAT // 4, min(BEAT // 4, clicks * (BEAT // 360)))
    moved, rates = 0, []
    for _ in range(6000):
        r = m.rate()
        rates.append(r)
        moved += r - T120
    assert moved == want and m.s32("tj_debt") == 0
    assert T120 * 96 // 100 <= min(rates) and max(rates) <= T120 * 104 // 100


def test_phase_pressed_is_ten_clicks(m):
    m.jog()
    m.knob(6, 1, held=1)
    assert m.s32("tj_debt") == 0                              # one detent: not yet
    m.knob(6, 1, held=1)
    assert m.s32("tj_debt") == 10 * (BEAT // 360)


def test_bar_position_while_playing(m):
    m.uc.mem_write(PLAYING, struct.pack(">I", 1))
    for _ in range(1500):                                     # 120 BPM: half a bar a second
        m.rate()
    assert m.s32("tj_pos") == 1500 * T120 == 2 * BEAT
    for _ in range(1500):
        m.rate()
    assert m.s32("tj_pos") == 0                               # wrapped at the bar
    m.uc.mem_write(PLAYING, struct.pack(">I", 0))
    m.rate()
    assert m.s32("tj_pos") == 0


def isr_seconds(m, blocks, act=None):
    """the real internal-clock path, block by block: count the subticks it fires (the tempo interrupt's own reload
    of the countdown done here: 225,000 a subtick, keeping the overshoot)"""
    uc = m.uc
    fires = [0]

    def fire(u, a, s, _):
        fires[0] += 1
    h = uc.hook_add(UC_HOOK_CODE, fire, begin=ISR_FIRE, end=ISR_FIRE)
    uc.mem_write(0x8000_46F4, struct.pack(">i", 225_000))
    uc.mem_write(0x8000_46EC, struct.pack(">i", 0))
    for b in range(blocks):
        if act:
            act(b)
        uc.reg_write(UC_M68K_REG_SR, 0x2700)
        uc.reg_write(UC_M68K_REG_A7, 0x4FE0_0000)
        uc.emu_start(ISR0, ISR_END, count=100_000)
        cd = struct.unpack(">i", bytes(uc.mem_read(0x8000_46F4, 4)))[0]
        if cd == 0x7FFF_FFFF:
            rem = struct.unpack(">i", bytes(uc.mem_read(0x8000_46F0, 4)))[0]
            uc.mem_write(0x8000_46F4, struct.pack(">i", 225_000 + rem))
    uc.hook_del(h)
    return fires[0]


def test_the_real_interrupt_path(m):
    assert isr_seconds(m, 1500) == 192                         # 120 BPM: 96 subticks a beat, 2 beats a second
    for clicks, extra in ((15, 4), (-15, -4)):                 # 15 x 1/360 beat = 4 subticks, at 4 %: 1 beat
        m2 = M()
        m2.jog()
        one = 1 if clicks > 0 else -1
        assert isr_seconds(m2, 1500, lambda b: [m2.knob(6, one) for _ in range(2 * abs(clicks))] if b == 100
                           else None) == 192 + extra
    m3 = M()
    m3.jog()
    m3.knob(4, -8)                                            # BRAKE 0
    m3.key(40, 1)                                             # held for the whole second: nothing fires
    assert isr_seconds(m3, 1500) == 0


def test_the_destructor_lets_go(m):
    m.jog()
    m.key(40, 1)
    for _ in range(50):
        m.rate()
    m.call(m.sym["tj_dtor1"], [VIEW])
    assert m.s32("tj_view") == 0 and m.u8("tj_touch") == 0
    for _ in range(400):
        r = m.rate()
    assert r == T120                                          # START brings it back by itself


# ---- on the booted image (fonts, text, the PERSONALIZE menu) ----

@pytest.fixture(scope="module")
def rig():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import seqrig as S
    r = S.Rig(("modarea", "tempojog"))
    r.g.call(0x401A_A8B0 if P142 else 0x401A_A614, [])          # the fonts
    return r


def test_screen(rig):
    uc, g, sym = rig.uc, rig.g, rig.sym
    texts = []
    TEXT = 0x400F_8BD0 if P142 else 0x400F_8A0C

    def tx(u, a, s, _):
        sp = u.reg_read(UC_M68K_REG_A7)
        w = struct.unpack(">7I", u.mem_read(sp + 4, 28))
        arg = bytes(u.mem_read(w[6], 24)).split(b"\0")[0].decode()
        texts.append(arg)
    h = uc.hook_add(UC_HOOK_CODE, tx, begin=TEXT, end=TEXT)
    can = 0x47C0_0000
    uc.mem_write(TEMPO, struct.pack(">i", 130 * 120 + 30))     # 130.25 BPM
    uc.mem_write(sym["tj_view"], struct.pack(">I", VIEW))
    uc.mem_write(sym["tj_rate"], struct.pack(">i", 130 * 120 + 30))

    def shot(pos):
        texts.clear()
        uc.mem_write(sym["tj_pos"], struct.pack(">I", pos))
        uc.mem_write(can, struct.pack(">5I", 0, 128, 64, 2, can + 0x100))
        uc.mem_write(can + 0x100, bytes(0x400))
        g.call(sym["tj_draw"], [VIEW, can])
        buf = bytes(uc.mem_read(can + 0x100, 1024))
        return lambda x, y: (buf[x * 8 + y // 8] >> (7 - y % 8)) & 1
    p = shot(0)
    assert texts == ["1/16", "VINYL", "130.25", "(LEV)", " 0.00%"]   # TEST35: no "(B)" (PERSONALIZE sets it)
    on = lambda p, ys: [p(30, 35 + y) for y in ys]             # noqa: E731
    assert on(p, (12, 17)) == [1, 1] and on(p, (-12, -17)) == [0, 0]   # the marker at 12 o'clock on the one
    p = shot(2 * BEAT)                                        # half a bar on: 6 o'clock
    assert on(p, (-12, -17)) == [1, 1] and on(p, (12, 17)) == [0, 0]
    uc.mem_write(sym["tj_disp"], b"\x01")                   # TEST35: CDJ, its rings turn with the platter
    rings = lambda p: {(x, y) for x in range(4, 57) for y in range(9, 62)   # noqa: E731
                       if 19.5 <= ((x - 30) ** 2 + (y - 35) ** 2) ** 0.5 <= 24.5 and p(x, y)}
    a, b = rings(shot(0)), rings(shot(BEAT // 3))
    assert len(a) > 40 and len(a ^ b) > 20                    # lit, and different a moment later
    uc.mem_write(sym["tj_disp"], b"\x00")
    uc.hook_del(h)


def test_personalize_line(rig):
    uc, g, sym = rig.uc, rig.g, rig.sym
    new = 0x4010_394C if P142 else 0x4010_3788
    g.call(new, [0x1C4])
    view = uc.reg_read(UC_M68K_REG_D0)
    g.call(sym["tj_pers"], [view])
    u32 = lambda a: struct.unpack(">I", uc.mem_read(a, 4))[0]  # noqa: E731
    b, e = u32(view + 4), u32(view + 8)
    assert (e - b) // 8 == 10
    items = [struct.unpack(">21I", uc.mem_read(u32(b + 8 * i), 84)) for i in range(10)]
    ours, rem = items[9], items[2]                            # REMEMBER SUBPAGE: the same shape
    assert ours[0] == rem[0] and ours[1] == rem[1] and ours[2] == 9 and ours[19:] == rem[19:]
    assert [ours[k] for k in (5, 9, 13, 17)] == [rem[k] for k in (5, 9, 13, 17)]          # the managers
    assert [ours[k] for k in (6, 10, 14, 18)] == [sym[n] for n in ("tj_inv_name", "tj_inv_tog", "tj_inv_draw",
                                                                   "tj_inv_delta")]
    sret = 0x47E0_0000
    uc.reg_write(UC_M68K_REG_A0, sret)
    g.call(ours[6], [u32(b + 8 * 9) + 12])
    assert bytes(uc.mem_read(u32(sret), 12)) == b"JOG DISPLAY\0"
    it = u32(b + 8 * 9)
    uc.mem_write(sym["tj_disp"], b"\0")
    g.call(ours[10], [it + 28])
    assert uc.mem_read(sym["tj_disp"], 1)[0] == 1             # [YES]: CDJ
    g.call(ours[18], [it + 60, 0, 1])
    assert uc.mem_read(sym["tj_disp"], 1)[0] == 1             # [RIGHT] at the end: stays
    g.call(ours[18], [it + 60, 0, -1])
    assert uc.mem_read(sym["tj_disp"], 1)[0] == 0             # [LEFT]: VINYL
