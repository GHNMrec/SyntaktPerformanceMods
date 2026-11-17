"""TEST35 Syntakt Performance Mods: the JOG page's new knobs and LOAD, PERFORM's fine DJ filter, its spectrum, and the
perf-filter mod, on the stock image with the mods' patches (mods/tempojog/patch.json is the no-LINK build).

- the sites: no LINK (the MIDI inputs stay stock), no LINK chunk or symbols;
- knobs: B LOAD, C START, D BRAKE, E RANGE, F PHASE; G, H nothing; LOAD and RANGE a step every 3 detents, START,
  BRAKE and PHASE every 2 (a turn back, or another knob, starts over); B no longer sets VINYL / CDJ: PERSONALIZE does;
- LOAD (the jog's weight): from a 2 % bend, back exactly to the set tempo in ~0.28 s (LOAD 1) .. ~2.3 s (LOAD 8), each
  LOAD slower than the one before, and no slow tail;
- PERFORM: B a fine position (63 detents a side at a slow turn), a sweep stops at THRU before crossing, the cutoff is
  a 16-bit word glided by the audio interrupt into the filter's smoothed FREQ (monotonic, at most 1/32 of the way a
  block, off the 256 grid), the knob byte follows rounded; a change from elsewhere gives the filter back; PERFORM
  starts where the filter is;
- the spectrum: the tap's cost (only while PERFORM is up), a sine lands in its own column (100 Hz, 1 kHz, 10 kHz);
- perf-filter: master-filter's audio, bit for bit: the same copy and the same CVs from the same knobs, block after
  block (random kits, every type, ON / OFF, glides, routing masks)."""
import json
import math
import random
import struct

import pytest

import test_tempojog as J
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_D0

P142, BEAT, Q, T120, VIEW = J.P142, J.BEAT, J.Q, J.T120, J.VIEW
COPY_FN = 0x4009_79CA if P142 else 0x4009_7952
COPY, CVS = 0x8000_6348, 0x8000_3160
SPX = 0x8000_DED0
PF = J.ROOT / "mods" / "perf-filter" / "patch.json"
MF = J.ROOT / "mods" / "master-filter" / "patch.json"
pytestmark = pytest.mark.skipif(not (J.SEC3.exists() and J.SPEC.exists() and PF.exists()), reason="needs the image")
VST = 0x454E_4C00 if P142 else 0x454E_3C00                                          # the FX CV routine's voice state (a4 = 0x454E3C5C)
FBUF = 0x47E0_0000                                            # a fake filter: smoothed FREQ at -19, the knob bytes


class M(J.M):
    def __init__(self):
        super().__init__()
        self.uc.mem_write(COPY_FN, b"\x20\x3c" + struct.pack(">I", COPY) + b"\x4e\x75")

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))

    def u8s(self, n):
        return struct.unpack(">b", self.uc.mem_read(self.sym[n], 1))[0]

    def tap(self):
        self.call(self.sym["tj_tap"])

    def count(self, fn):
        n = [0]
        self.uc.ctl_flush_tb()
        h = self.uc.hook_add(UC_HOOK_CODE, lambda *a: n.__setitem__(0, n[0] + 1))
        fn()
        self.uc.hook_del(h)
        return n[0]


@pytest.fixture
def m():
    return M()


# ---- the build ----

def test_no_link():
    spec = json.loads(J.SPEC.read_text())
    assert spec["name"] == "tempojog-nolink" and spec["requires"] == ["modarea"]
    sites = {int(p["addr"], 16) for p in spec["patches"] if not p.get("append")}
    assert not sites & set((0x4008_264A, 0x4008_265A) if P142 else (0x4008_25D2, 0x4008_25E2))
    assert not any(k.startswith("tl_") for k in spec["symbols"])
    assert not any("LINK" in p["what"] for p in spec["patches"])


# ---- knobs ----

def test_knob_layout_and_detents(m):
    m.jog()
    m.knob(2, 1)
    m.knob(2, 1)
    assert m.u8("tj_load") == 3 and m.u8("tj_pop") == 3       # B LOAD: 2 detents, not yet (the pop-up shows it)
    m.knob(2, 1)
    assert m.u8("tj_load") == 4                               # the third
    m.knob(2, 1)
    m.knob(2, 1)
    m.knob(2, -1)                                             # a turn back starts over
    m.knob(2, -1)
    assert m.u8("tj_load") == 4
    m.knob(2, -1)
    assert m.u8("tj_load") == 3
    m.knob(3, 1)
    assert m.u8("tj_start") == 2
    m.knob(3, 1)
    assert m.u8("tj_start") == 3 and m.u8("tj_pop") == 5      # C START: 2 detents
    m.knob(3, 2, held=1)
    assert m.u8("tj_start") == 8                              # pressed: 0.5 s a step
    m.knob(4, 1)
    m.knob(5, 1)                                              # another knob: D's detent is forgotten
    m.knob(4, 1)
    assert m.u8("tj_brake") == 4
    m.knob(4, 1)
    assert m.u8("tj_brake") == 5 and m.u8("tj_pop") == 4      # D BRAKE
    for _ in range(3):
        m.knob(5, 1)
    assert m.u8("tj_range") == 2 and m.u8("tj_pop") == 7      # E RANGE: 3 detents
    m.knob(6, 1)
    m.knob(6, 1)
    assert m.s32("tj_debt") == BEAT // 360 and m.u8("tj_pop") == 8   # F PHASE: 2 detents
    pop = m.u8("tj_pop")
    m.reached.clear()
    for n in (7, 8):                                          # G, H: nothing
        for d in (1, -1, 3):
            assert m.knob(n, d) == 1 and m.knob(n, d, held=1) == 1
    assert m.u8("tj_pop") == pop and m.reached == []
    assert m.u8("tj_mode") == 1                               # VINYL: B is not the mode


def bend_back(m, load, clicks=8):
    m.set8("tj_load", load)
    m.w32(m.sym["tj_btgt"], clicks * 2620)
    m.w32(m.sym["tj_bend"], clicks * 2620)
    n, last = 0, None
    while m.s32("tj_btgt") or m.s32("tj_bend"):
        r = m.rate()
        n += 1
        if abs(r - T120) * 1000 > T120:                       # still over 0.1 %
            last = n
        assert n < 6000
    assert m.rate() == T120
    return n / 1500, (last or 0) / 1500


def test_load_is_the_weight(m):
    m.jog()
    t = [bend_back(m, load) for load in range(1, 9)]
    back = [a for a, _ in t]
    assert back == sorted(back) and len(set(back)) == 8       # 8 weights, each heavier than the last
    assert back[0] < 0.32 and 0.5 < back[2] < 0.7 and 2.0 < back[7] < 2.6
    for a, b in t:
        assert a - b < 0.25 + 0.1 * a                         # no slow tail after 0.1 %


# ---- PERFORM's DJ filter ----

def perf(m, on=1, typ=7, freq=127, reso=0, s=None):
    m.w32(m.sym["tj_mfp"], FBUF)
    m.uc.mem_write(FBUF - 19, struct.pack(">i", (freq << 8 if s is None else s) << 16) + bytes(12))
    m.uc.mem_write(FBUF, bytes([typ, freq, reso, 0, on, 64, 0]))
    m.jog()
    m.key(17, 1)


def fl(m):
    return list(m.uc.mem_read(FBUF, 5)), struct.unpack(">i", m.uc.mem_read(FBUF - 19, 4))[0] >> 16


def test_perform_fine_filter(m):
    perf(m, on=0)
    m.knob(2, -1)                                             # B left: on, LP2 at its open end at once
    (t, f, r, _, on), s = fl(m)
    assert (t, on, f, s) == (1, 1, 127, 0x7F00) and m.u8("tj_fown") == 1
    assert m.s32("tj_fqt") == 0x7F00 - 64 * 119 * 256 // 4032
    for _ in range(400):
        m.tap()
    (t, f, r, _, on), s = fl(m)
    assert s == m.s32("tj_fqt") and f == (s + 128) >> 8 and s & 0xFF   # there, 16-bit, the byte rounded
    m.knob(2, -100)
    assert m.s32("tj_fp") == -4032 and m.s32("tj_fqt") == 8 << 8      # closed as far as it goes
    prev, steps, d0 = s, [], s - (8 << 8)
    for _ in range(600):
        m.tap()
        s = fl(m)[1]
        steps.append(prev - s)
        prev = s
    assert s == 8 << 8 and all(0 <= x <= d0 // 32 + 8 for x in steps)   # smooth: monotonic, a 32nd at most
    assert sum(1 for x in steps if x) > 150                    # a long sweep, not a jump
    m.knob(2, 200)                                             # a sweep right stops at THRU
    assert m.s32("tj_fp") == 0 and fl(m)[0][0] == 7 and m.u8("tj_fown") == 0
    m.knob(2, 1)                                               # then HP2 from its open end
    (t, f, r, _, on), s = fl(m)
    assert t == 3 and s == 0 and f == 0
    m.knob(3, 1)
    m.knob(3, 9)                                               # C: RESO, at most 2 a fast event
    assert fl(m)[0][2] == 3
    m.key(41, 1)                                               # B pushed: THRU
    assert fl(m)[0][0] == 7 and fl(m)[0][4] == 1 and m.u8s("tj_fpos") == 0
    m.knob(2, 10)
    m.key(1, 1)
    m.key(41, 1)                                               # [FUNC] + B pushed: the filter off
    m.key(1, 0)
    assert fl(m)[0][4] == 0


def test_perform_gives_the_filter_back(m):
    perf(m, on=0)
    m.knob(2, -20)
    for _ in range(5):
        m.tap()
    m.uc.mem_write(FBUF + 1, bytes([90]))                     # the FX page (or MIDI) sets FREQ
    s = fl(m)[1]
    m.tap()
    assert m.u8("tj_fown") == 0 and fl(m)[1] == s and fl(m)[0][1] == 90   # left alone from then on


def test_perform_starts_where_the_filter_is(m):
    perf(m, on=1, typ=3, freq=55, s=55 << 8 | 0x80)
    assert m.s32("tj_fp") == (55 << 8 | 0x80) * 4032 // (110 * 256) and m.u8s("tj_fpos") == m.s32("tj_fp") // 64
    m2 = M()
    perf(m2, on=1, typ=1, freq=8)
    assert m2.s32("tj_fp") == -4032
    m3 = M()
    m3.w32(m3.sym["tj_mfp"], 0)                               # no filter in the build: nothing
    m3.jog()
    m3.key(17, 1)
    m3.knob(2, 5)
    m3.tap()
    assert m3.s32("tj_fp") == 0


def test_tap_cost(m):
    m.w32(m.sym["tj_mfp"], 0)
    idle = m.count(m.tap)
    buf = 0x47D0_0000
    m.uc.mem_write(buf, bytes(0x2000))
    m.w32(m.sym["tj_spec"], buf)
    m.uc.mem_write(m.sym["tj_spon"], struct.pack(">H", 100))
    busy = m.count(m.tap)
    print(f"tj_tap: {idle} instructions idle, {busy} with PERFORM's spectrum on screen")
    assert idle < 30 and busy < 800                           # ~1 % of the interrupt's ~69,000


# ---- the spectrum (booted image) ----

@pytest.fixture(scope="module")
def rig():
    import seqrig as S
    r = S.Rig(("modarea", "tempojog", "perf-filter"))
    r.g.call(0x401A_A8B0 if P142 else 0x401A_A614, [])
    return r


def spectrum_peak(rig, f, amp=1 << 26):
    uc, g, sym = rig.uc, rig.g, rig.sym
    uc.mem_write(sym["tj_mfp"], struct.pack(">I", sym["pf_p"]))
    uc.mem_write(sym["tj_view"], struct.pack(">I", VIEW))
    uc.mem_write(sym["tj_page"], b"\x01")
    can = 0x47C0_0000

    def draw():
        uc.mem_write(can, struct.pack(">5I", 0, 128, 64, 2, can + 0x100))
        uc.mem_write(can + 0x100, bytes(0x400))
        n = [0]
        uc.ctl_flush_tb()
        h = uc.hook_add(UC_HOOK_CODE, lambda *a: n.__setitem__(0, n[0] + 1))
        g.call(sym["tj_draw"], [VIEW, can])
        uc.hook_del(h)
        return n[0]
    draw()                                                    # the first PERFORM: the buffers
    spec = struct.unpack(">I", uc.mem_read(sym["tj_spec"], 4))[0]
    assert spec
    ph = 0.0
    for _ in range(80):                                       # 80 blocks of a sine (L = R)
        fr = b""
        for _ in range(32):
            v = int(amp * math.sin(ph))
            ph += 2 * math.pi * f / 48000
            fr += struct.pack(">ii", v, v)
        uc.mem_write(SPX, fr)
        g.call(sym["tj_tap"], [])
    cost = [draw() for _ in range(4)]
    col = struct.unpack(">128h", uc.mem_read(spec + COL_OFF, 256))
    return col.index(max(col)), max(cost)


NFFT = 256
COL_OFF = 2 * NFFT * 2 + 2 * NFFT * 4 + NFFT // 2 * 2 * 2 + NFFT * 2 + 2 * NFFT // 2 * 2   # spec_t.col


@pytest.mark.parametrize("f,col", [(100, 30), (1000, 72), (10000, 114)])
def test_a_sine_lands_in_its_column(rig, f, col):
    x, cost = spectrum_peak(rig, f)
    print(f"{f} Hz: column {x} (want {col}); PERFORM redraw {cost} instructions")
    assert abs(x - col) <= 2
    assert cost < 120_000


# ---- perf-filter: master-filter's audio, bit for bit ----

class F:
    """the image with master-filter and perf-filter in the mod area (their code side by side, called directly)"""
    def __init__(self):
        self.m = J.M.__new__(J.M)
        from unicorn import UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, Uc
        from unicorn.m68k_const import UC_CPU_M68K_ANY
        uc = self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, cpu=UC_CPU_M68K_ANY)
        for a, s in ((0x4000_0000, 0x1000_0000), (0x8000_0000, 0x1_0000)):
            uc.mem_map(a, s)
        uc.mem_write(J.LOAD, J.SEC3.read_bytes())
        self.sym = {}
        for f in (MF, PF):
            spec = json.loads(f.read_text())
            for p in spec["patches"]:
                if p.get("append"):
                    uc.mem_write(int(p["ram"], 16), bytes.fromhex(p["hex"]))
            self.sym.update({k: int(v, 16) for k, v in spec["symbols"].items()})
        uc.mem_write(J.RET, b"\x4e\x71" * 4)
        uc.mem_write(0x43BD_D044 if P142 else 0x43BD_C044, b"\x02")   # the table resonance path (Polivoks)

    def call(self, fn, args):
        J.M.call(self, fn, args)


def snap(f):
    return bytes(f.uc.mem_read(0x8000_0000, 0x1_0000))


@pytest.mark.skipif(not MF.exists(), reason="no master-filter")
@pytest.mark.parametrize("seed", range(6))
def test_perf_filter_is_master_filters_audio(seed):
    f = F()
    r = random.Random(seed)
    mfp, pfp = f.sym["mf_p"], f.sym["pf_p"]
    hook_m, hook_p = f.sym["mf_fx_hook"], f.sym["pf_fx_hook"]
    ram = bytearray(r.randbytes(0x1_0000))
    struct.pack_into(">h", ram, 0x3148, r.choice([0, 0, 0x0003, 0x1000, 0x2000, 0x4000, -0x8000]))
    struct.pack_into(">h", ram, 0x314C, r.choice([0, 0x0101]))
    for off in range(0, 1876, 2):
        struct.pack_into(">H", ram, 0x6348 + off, r.randrange(0x7F01))
    for t in range(12):
        struct.pack_into(">H", ram, 0x6348 + 142 * t + 126, r.choice([0, 0x100, 0x100]))
    knobs = [0, 127, 0, 0, 0, 64, 0]
    vst = bytes(0x100)
    for blk in range(300):
        if blk % 23 == 0:
            knobs[0] = r.randrange(8)
            knobs[1] = r.randrange(128)
            knobs[2] = r.randrange(128)
            knobs[4] = r.random() < 0.8
        out = []
        for hook, p in ((hook_m, mfp), (hook_p, pfp)):
            f.uc.mem_write(0x8000_0000, bytes(ram))
            f.uc.mem_write(VST, vst)                          # the OS routine's own state (per analog voice)
            f.uc.mem_write(p, bytes(knobs))
            f.call(hook, [CVS, COPY])
            out.append(snap(f) + bytes(f.uc.mem_read(VST, 0x100)))
        assert out[0] == out[1], (seed, blk)                  # the same copy, the same CVs
        ram, vst = bytearray(out[1][:0x1_0000]), out[1][0x1_0000:]
        for off in range(0, 1876, 2):                         # the next block: the OS rebuilds the copy
            struct.pack_into(">H", ram, 0x6348 + off, r.randrange(0x7F01))
        for t in range(12):
            struct.pack_into(">H", ram, 0x6348 + 142 * t + 126, r.choice([0, 0x100, 0x100]))
    assert struct.unpack(">I", f.uc.mem_read(f.sym["pf_blocks"], 4))[0] > 0


def test_perf_filter_patch():
    spec = json.loads(PF.read_text())
    assert spec["name"] == "perf-filter" and spec["requires"] == ["modarea"]
    sites = [p for p in spec["patches"] if not p.get("append")]
    assert len(sites) == 1 and int(sites[0]["addr"], 16) == (0x400A_4F9C if P142 else 0x400A_4F24)
    stock = J.SEC3.read_bytes()
    a = int(sites[0]["addr"], 16) - J.LOAD
    assert stock[a:a + 6].hex() == ("4eb940095e1c" if P142 else "4eb940095da4")
    sym = {k: int(v, 16) for k, v in spec["symbols"].items()}
    assert sym["pf_p"] - 19 == sym["pf_s"]                    # master-filter's layout (the jog writes there)


@pytest.mark.parametrize("w", [8 << 8, 0x2A80, 0x3456, 0x5C40, 0x7000, 0x7E00])
def test_perform_header_shows_the_cutoff_in_hz(rig, w):
    """the header's Hz follows the filter's smoothed FREQ: 5.9 Hz x 2^(0.0926 FREQ) (master-filter's measured map)"""
    uc, g, sym = rig.uc, rig.g, rig.sym
    p = sym["pf_p"]
    uc.mem_write(sym["tj_mfp"], struct.pack(">I", p))
    uc.mem_write(sym["tj_view"], struct.pack(">I", VIEW))
    uc.mem_write(sym["tj_page"], b"\x01")
    uc.mem_write(p, bytes([1, w >> 8, 30, 0, 1, 64, 0]))
    uc.mem_write(p - 19, struct.pack(">i", w << 16))
    texts = []
    TEXT = 0x400F_8BD0 if P142 else 0x400F_8A0C
    from unicorn.m68k_const import UC_M68K_REG_A7

    def tx(u, a, s, _):
        sp = u.reg_read(UC_M68K_REG_A7)
        q = struct.unpack(">7I", u.mem_read(sp + 4, 28))
        texts.append(bytes(u.mem_read(q[6], 24)).split(b"\0")[0].decode())
    h = uc.hook_add(UC_HOOK_CODE, tx, begin=TEXT, end=TEXT)
    can = 0x47C0_0000
    uc.mem_write(can, struct.pack(">5I", 0, 128, 64, 2, can + 0x100))
    g.call(sym["tj_draw"], [VIEW, can])
    uc.hook_del(h)
    assert texts[0] == "LP2" and texts[2] == "RES 30" and texts[3:] == ["LP", "HP"]
    t, want = texts[1], 5.9 * 2 ** (0.0926 * w / 256)
    got = float(t[:-2]) if t.endswith("HZ") else float(t[:-1]) * 1000
    tol = 1.5 if want < 1000 else 100 if want < 10000 else 500
    assert abs(got - want) <= tol + want * 0.004, (t, want)
