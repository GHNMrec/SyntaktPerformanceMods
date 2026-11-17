"""midi-guard: the mods' ids are theirs on the FX track and on the FX3 page only; MIDI tracks get the stock
parameters back.

Boots the whole upstream build (stock section 3 + every mod, mod area in RAM) through the real static
initializer, then drives is-kit/get/set and the OS's own ParameterPageView get/set-value (shared by
MidiParameterPageView and FxPageView, the DELAY/REVERB tabs) with the track as the OS passes it (12 = FX
track) and the page vector of the view (REVERB tab = pages 21, 25; 25 = FX3, reachable from any track).
Compares descriptors, objects and formatter texts with a stock boot.
"""

import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools" / "unpack"), str(ROOT / "mods" / "midi-guard")]
import eft  # noqa: E402

SY = ROOT / "firmware" / "Syntakt_OS1.42.syx"
pytestmark = pytest.mark.skipif(not SY.exists(), reason="OS Syntakt assente")
import recipe  # noqa: E402

LOAD = 0x4000_0400
NAMES = ("splash", "modarea", "midi-guard", "vparams", "master-comp", "readable-values", "beat-repeat", "fx3",
         "master-filter")
IDS = list(range(246, 254)) + list(range(262, 270)) + [445, 446] + [443, 402, 406, 412] + [442] + [431, 432]
# + IMPULSE REP/NUM (RPT2, RPT); IMPULSE SHP, COL x3 (master-filter TYPE, FREQ, RESO, DRV); IMPULSE HOLD (FLTR);
# NLEV, NDEC of a fourth drum machine (master-filter TRIM, CMP)
IS_KIT, GET, SET = 0x4000_D870, 0x4000_D94A, 0x4000_DA32
GETV, SETV = 0x4003_7E50, 0x4003_7F9A
HELPER = 0x4003_B4D2                     # ParameterPageView encoder/trig helper (is-kit returns to 0x4003B522)
SITES_A2 = (0x4003_7ED6, 0x4003_8034, 0x4003_A3C4, 0x4003_B522)      # vp_sites reading the view in a2
SITES_TRACK = (0x4004_1F0A, 0x4004_2416, 0x4004_27B2, 0x4004_3274, 0x4004_3D5A, 0x400F_38EE)
REVERB = (21, 25)                        # REVERB tab: stock page 21, fx3 page 25 (FX3 = REVERB page 2)
FX3_IDS = list(range(246, 254))
DESC = lambda i: 0x4022_D83C + 52 * i  # noqa: E731
OBJ = lambda i: 0x41BA_0A24 + 84 * i  # noqa: E731
KIT, BUF, FAKE = 0x47E0_0000, 0x47E1_0000, 0x47D0_0000
STOCK_NAMES = ["CHAN", "BANK", "PROG", "PB", "AT", "MW", "BC", "SBNK"] + [f"SEL{k}" for k in range(1, 9)] + ["REP", "NUM"] \
    + ["SHP", "COL", "COL", "COL"] + ["HOLD"] + ["NLEV", "NDEC"]
VALUES = (0, 0x100, 0x300, 0x4000, 0x7F00)


def specs():
    """TEST26: no gbus in this set: master-comp as built without it (patch_nofxg.json)"""
    f = lambda n: "patch_nofxg.json" if n == "master-comp" and (ROOT / "mods" / n / "patch_nofxg.json").exists() \
        else "patch.json"  # noqa: E731
    return [json.loads((ROOT / "mods" / n / f(n)).read_text(encoding="utf-8")) for n in NAMES]


class Boot:
    def __init__(self, sec3, mods):
        sec3 = bytearray(sec3)
        area = {}
        layout = next((m["layout"] for m in mods if m.get("layout", {}).get("compress") == "shlz"), None)
        img, ram = (int(layout["img"], 16), int(layout["ram"], 16)) if layout else (0, 0)
        for m in mods:
            for p in m["patches"]:
                d = bytes.fromhex(p["hex"])
                a = int(p["addr"], 16)
                if p.get("append"):
                    area[ram + a - img] = d
                else:
                    sec3[a - LOAD:a - LOAD + len(d)] = d
        self.allocs = []
        self.uc, _ = recipe.boot(bytes(sec3), area)
        self.uc.mem_map(0, 0x10_0000)

    def call(self, fn, args):
        uc = self.uc
        from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR
        sp = recipe.RET - 0x2000 - 4 * (len(args) + 1)
        uc.mem_write(sp, struct.pack(f">{len(args) + 1}I", recipe.RET, *[a & 0xFFFFFFFF for a in args]))
        uc.reg_write(UC_M68K_REG_SR, 0x2700)
        uc.reg_write(UC_M68K_REG_A7, sp)
        uc.emu_start(fn, recipe.RET, count=5_000_000)
        assert uc.reg_read(UC_M68K_REG_PC) == recipe.RET
        return uc.reg_read(UC_M68K_REG_D0) & 0xFFFFFFFF

    def call_from(self, site, fn, args, a2=0, entry=None):
        """Runs fn as if called by OS code returning to `site`, with a2 = the caller's page view (or, with
        entry, runs the OS function `entry` itself until it gets back to `site`)."""
        uc = self.uc
        from unicorn.m68k_const import UC_M68K_REG_A2, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR
        ret = recipe.RET if entry else site
        sp = recipe.RET - 0x2000 - 4 * (len(args) + 1)
        uc.mem_write(sp, struct.pack(f">{len(args) + 1}I", ret, *[a & 0xFFFFFFFF for a in args]))
        uc.reg_write(UC_M68K_REG_SR, 0x2700)
        uc.reg_write(UC_M68K_REG_A7, sp)
        uc.reg_write(UC_M68K_REG_A2, a2)
        uc.ctl_flush_tb()                       # the stop address only applies to freshly translated code
        try:
            uc.emu_start(entry or fn, site, count=5_000_000)
        finally:
            uc.ctl_flush_tb()                   # ... and must not stay in code that later runs use
        assert uc.reg_read(UC_M68K_REG_PC) == site
        return uc.reg_read(UC_M68K_REG_D0) & 0xFFFFFFFF

    def words(self, a, n):
        return list(struct.unpack(f">{n}I", self.uc.mem_read(a, 4 * n)))

    def u32(self, a):
        return self.words(a, 1)[0]

    def cstr(self, a):
        return bytes(self.uc.mem_read(a, 16)).split(b"\0")[0].decode("latin1")

    def snap(self):
        return {i: (self.words(DESC(i), 13), self.words(OBJ(i), 21)) for i in IDS}

    def fmt(self, i, v):
        fn = OBJ(i) + 20
        self.uc.mem_write(BUF, bytes(32))
        self.call(self.u32(fn + 12), [fn, v, BUF])
        return self.cstr(BUF)

    def texts(self):
        return {i: [self.fmt(i, v) for v in VALUES] for i in IDS}


@pytest.fixture(scope="module")
def boots():
    sec3 = eft.unpack(SY, ROOT / "unpacked" / SY.stem, ids=[3])[3].read_bytes()
    mods = specs()
    sym = {k: int(v, 16) for k, v in mods[NAMES.index("midi-guard")]["symbols"].items()}
    stock = Boot(sec3, [])
    guard = Boot(sec3, mods)
    return stock, guard, sym


UI_VIEW = FAKE + 0x8000                  # ui()'s own fake view: never the one a test is holding


def ui(g, track, pid, pages=(), pos=0):
    """A page view of the given active track, showing pages[pos], reads parameter pid (as when drawing a
    slot). No pages: the view's page vector is empty (the track alone decides)."""
    view, _ = _page_view(g, track, pages, pos, base=UI_VIEW)
    return g.call(GETV, [view, pid, -1])


def test_boot_starts_in_the_fx_context(boots):
    _, g, sym = boots
    assert g.u32(sym["mg_ctx"]) == 0 and g.u32(sym["mg_built"]) == 0
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in (246, 262, 269)] == ["TYPE", "COMP", "RPT1"]


def test_midi_track_gets_the_stock_parameters(boots):
    s, g, sym = boots
    ui(g, 12, 246)
    fx = g.snap()
    assert ui(g, 3, 246) == 0x5A5A                                     # the track's own CHAN, not fx3
    assert g.u32(sym["mg_ctx"]) == 1 and g.u32(sym["mg_built"]) == 1
    now, ref = g.snap(), s.snap()
    for i in IDS:
        assert now[i][0] == ref[i][0]                                  # descriptor: names, ranges, defaults
        assert now[i][1][0:5] == ref[i][1][0:5]                        # encoder type, value prototype
        for w in (5, 9, 17):                                           # formatter, graphic, style
            assert now[i][1][w + 2:w + 4] == ref[i][1][w + 2:w + 4]
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in IDS] == STOCK_NAMES
    assert g.texts() == s.texts()                                      # e.g. CHAN 1 2 4 ...
    for i in IDS:                                                      # kit functions: stock behaviour
        assert g.call(IS_KIT, [KIT, i, 3]) & 0xFF == 0
        assert g.call(GET, [KIT, i]) == s.call(GET, [KIT, i])
    ui(g, 12, 246)
    assert g.snap() == fx                                              # the mods' state comes back intact


def test_any_page_of_a_midi_track_switches(boots):
    _, g, sym = boots
    ui(g, 12, 300)                                                     # any page of the FX track
    assert g.u32(sym["mg_ctx"]) == 0 and g.cstr(g.u32(DESC(249) + 48)) == "DEL"
    ui(g, 5, 90)                                                       # LFO page of a MIDI track
    assert g.u32(sym["mg_ctx"]) == 1 and g.cstr(g.u32(DESC(249) + 48)) == "PB"   # LFO destinations: PB AT MW BC
    ui(g, 12, 246)


def test_switches_are_stable(boots):
    _, g, sym = boots
    ui(g, 2, 262)
    midi = g.snap()
    n = g.u32(sym["mg_swaps"])
    for k in range(8):
        ui(g, 12, 250)
        ui(g, k, 262 + k)
    assert g.snap() == midi and g.u32(sym["mg_swaps"]) == n + 16 and g.u32(sym["mg_built"]) == 1
    ui(g, 12, 246)


def test_fx_track_keeps_the_mods(boots):
    _, g, sym = boots
    ui(g, 12, 246)
    for i in IDS:
        if i == 412:                                                   # TEST26: MODE, master-comp's only with gbus
            continue
        assert g.call(IS_KIT, [KIT, i, 12]) & 0xFF == 1
    assert g.u32(sym["mg_ctx"]) == 0
    assert g.fmt(246, 0x300) == "CRSH" and g.fmt(266, 0) == "MIX"                # fx3 TYPE, master-comp SC


def test_other_callers_never_switch(boots):
    _, g, sym = boots
    ui(g, 12, 246)
    n = g.u32(sym["mg_swaps"])
    for i in (1, 5, 158, 245, 246, 254, 262, 269, 270, 445, 446, 504):  # MIDI input, FX routing, ...
        for t in (0, 3, 11, 12):
            g.call(IS_KIT, [KIT, i, t])
    assert g.u32(sym["mg_swaps"]) == n and g.u32(sym["mg_ctx"]) == 0


def test_reverb_fx_routing_is_stock_again(boots):
    s, g, _ = boots
    assert g.words(DESC(124), 13) == s.words(DESC(124), 13)            # 'REV' Reverb FX Routing
    o, r = g.words(OBJ(124), 21), s.words(OBJ(124), 21)
    assert o[0:5] == r[0:5] and all(o[w + 2:w + 4] == r[w + 2:w + 4] for w in (5, 9, 13, 17))
    table = [struct.unpack(">H", bytes(g.uc.mem_read(0x444E_C8D0 + 12 * k, 2)))[0] for k in range(32)]
    assert 124 not in table and 445 in table and 446 in table           # no mod answers for id 124


def test_fx_trig_page_and_impulse_pages(boots):
    _, g, sym = boots
    slots = struct.unpack(">8I", bytes(g.uc.mem_read(0x41BA_0924, 32)))
    assert slots == (269, 445, 23, 33, 28, 27, 26, 446)                 # RPT1 RPT2 ... RPT in slot H
    ui(g, 12, 445)
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in (269, 445, 446)] == ["RPT1", "RPT2", "RPT"]
    assert g.fmt(445, 0x100) == "1/8" and g.fmt(446, 0) == "OFF" and g.fmt(446, 0x100) == "ON"
    ui(g, 7, 446)                                                       # an IMPULSE track's SRC page
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in (445, 446)] == ["REP", "NUM"]
    assert g.call(IS_KIT, [KIT, 445, 7]) & 0xFF == 0
    ui(g, 12, 246)


def test_other_callers_need_the_fx_track(boots):
    _, g, sym = boots
    ui(g, 12, 246)                                                      # FX context...
    for i in (246, 262, 269, 445, 446):
        assert g.call(IS_KIT, [KIT, i, 12]) & 0xFF == 1
        assert g.call(IS_KIT, [KIT, i, 4]) & 0xFF == 0                  # ...but not for another track
    assert g.u32(sym["mg_ctx"]) == 0


VEC = FAKE + 0x1800                                                     # the default view's page vector


def _page_view(g, track, pages=(), pos=0, raw=None, base=FAKE):
    """Fake page view at base: active track `track` (view +116), model lookup (vtable +196), page vector
    pages (+124 begin, +128 end) and position pos (+144). raw = (begin, end, pos) written as is.
    Track model: get = 0x5A5A, set logged, value step (vtable +32, set-value's kit branch) = current + delta."""
    w = lambda a, v: g.uc.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))  # noqa: E731
    view, vt1, tsel, vt2, ptrk, model, vt3 = (base + o for o in (0, 0x400, 0x800, 0x900, 0xA00, 0xB00, 0xC00))
    f_trk, f_model, f_get, f_set, f_step, vec, log = (base + o for o in (0x1000, 0x1040, 0x1080, 0x10C0, 0x1100,
                                                                          0x1800, 0x2000))
    w(view, vt1), w(view + 116, tsel), w(view + 104, base + 0x3000)
    g.uc.mem_write(vec, struct.pack(">64I", *([25] * 64)))              # garbage reads would find page 25
    g.uc.mem_write(vec, struct.pack(f">{len(pages)}I", *pages))
    begin, end, p = raw or ((vec, vec + 4 * len(pages), pos) if pages else (0, 0, 0))
    w(view + 124, begin), w(view + 128, end), w(view + 144, p)
    w(tsel, vt2), w(vt2 + 40, f_trk), w(ptrk + 8, track)
    g.uc.mem_write(f_trk, bytes.fromhex("203c") + struct.pack(">I", ptrk) + bytes.fromhex("4e75"))
    w(vt1 + 196, f_model)
    g.uc.mem_write(f_model, bytes.fromhex("203c") + struct.pack(">I", model) + bytes.fromhex("4e75"))
    w(model, vt3), w(vt3 + 32, f_step), w(vt3 + 40, f_get), w(vt3 + 44, f_set)
    g.uc.mem_write(f_get, bytes.fromhex("203c00005a5a4e75"))                   # track model: 0x5A5A
    g.uc.mem_write(f_set, bytes.fromhex("206f000823c8" + f"{log:08x}" + "206f000c23c8" + f"{log + 4:08x}"
                                        + "70004e75"))
    g.uc.mem_write(f_step, bytes.fromhex("202f000cd0af00104e75"))              # 12(sp) + 16(sp)
    g.uc.mem_write(log, bytes(8))
    return view, log


def test_page_view_routes_by_track(boots):
    _, g, sym = boots
    view, log = _page_view(g, 3)
    assert g.call(GETV, [view, 246, -1]) == 0x5A5A                       # MIDI track: the track's CHAN
    g.call(SETV, [view, 246, 0x300, 0, 0, 0])
    assert g.words(log, 2) == [246, 0x300]                               # ... and turning it writes CHAN
    view, log = _page_view(g, 12)
    assert g.call(GETV, [view, 246, -1]) != 0x5A5A                       # FX track: fx3 TYPE
    g.call(SETV, [view, 246, 0x200, 0, 0, 0])
    assert g.words(log, 2) == [0, 0] and g.u32(sym["mg_ctx"]) == 0


def test_fx3_page_shows_fx3_from_any_track(boots):
    """REVERB page 2 (FX3) is on the DELAY/REVERB tabs, which every track opens: the mods' context."""
    _, g, sym = boots
    vals = {i: ui(g, 12, i, REVERB, 1) for i in FX3_IDS}                # FX track, REVERB page 2
    fx = g.snap()
    for t in (0, 3, 4, 7, 11):
        ui(g, t, 246)                                                   # e.g. its SRC page first: stock
        assert g.u32(sym["mg_ctx"]) == 1
        assert [ui(g, t, i, REVERB, 1) for i in FX3_IDS] == [vals[i] for i in FX3_IDS]   # fx3's values
        assert g.u32(sym["mg_ctx"]) == 0 and g.snap() == fx             # fx3 names, ranges, formatters
    assert 0x5A5A not in vals.values()                                  # never the track's own CHAN, BANK...
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in (246, 249)] == ["TYPE", "DEL"]


def test_turning_fx3_knobs_from_a_midi_track(boots):
    """Set-value (relative, as the encoders send it) from a MIDI track's REVERB page 2 changes fx3, exactly
    as from the FX track, and never the track's own MIDI parameter."""
    _, g, sym = boots
    for pid in (246, 247, 251):                                         # TYPE (0..3), SPD, WID
        view, log = _page_view(g, 12, REVERB, 1)                        # FX track: the reference
        v0 = g.call(GETV, [view, pid, -1])
        d = -0x200 if v0 >= 0x200 else 0x200
        g.call(SETV, [view, pid, d, 0, 0, 0])
        v1 = g.call(GETV, [view, pid, -1])
        g.call(SETV, [view, pid, -d, 0, 0, 0])
        assert v1 != v0 and g.call(GETV, [view, pid, -1]) == v0 and g.words(log, 2) == [0, 0]
        view, log = _page_view(g, 4, REVERB, 1)                         # a MIDI track's REVERB page 2
        assert g.call(GETV, [view, pid, -1]) == v0
        g.call(SETV, [view, pid, d, 0, 0, 0])
        assert g.call(GETV, [view, pid, -1]) == v1                      # same turn, same fx3 result
        assert g.words(log, 2) == [0, 0]                                # track 4's CHAN/BANK/... untouched
        assert ui(g, 12, pid, REVERB, 1) == v1                          # one fx3 value for every track
        g.call(SETV, [view, pid, -d, 0, 0, 0])
        assert g.call(GETV, [view, pid, -1]) == v0 and g.u32(sym["mg_ctx"]) == 0


def test_other_pages_of_a_midi_track_stay_stock(boots):
    _, g, sym = boots
    ui(g, 12, 246, REVERB, 1)
    assert ui(g, 4, 246, (27, 28, 29), 0) == 0x5A5A                     # MIDI SRC page: the track's CHAN
    assert g.u32(sym["mg_ctx"]) == 1 and g.cstr(g.u32(DESC(246) + 48)) == "CHAN"
    ui(g, 12, 246, REVERB, 1)
    ui(g, 4, 246, REVERB, 0)                                            # REVERB page 1 from a MIDI track
    assert g.u32(sym["mg_ctx"]) == 1
    ui(g, 12, 246, REVERB, 0)                                           # REVERB page 1 of the FX track
    assert g.u32(sym["mg_ctx"]) == 0


@pytest.mark.parametrize("raw", [
    (0, 0, 0),                                                          # empty vector
    (VEC + 2, VEC + 10, 1),                                             # misaligned
    (VEC, VEC + 8, 2), (VEC, VEC + 8, -1),                              # position out of range
    (VEC + 8, VEC, 0),                                                  # end before begin
    (VEC, VEC + 4 * 65, 1),                                             # not a page vector
    (0x8000_1000, 0x8000_1008, 1),                                      # outside DDR
])
def test_unusable_page_vectors_leave_the_track_to_decide(boots, raw):
    _, g, sym = boots
    ui(g, 12, 246)
    view, _ = _page_view(g, 4, raw=raw)
    assert g.call(GETV, [view, 246, -1]) == 0x5A5A and g.u32(sym["mg_ctx"]) == 1


def test_each_page_view_site(boots):
    """vp_sites: the four ParameterPageView sites read the view in a2, the others only the track."""
    _, g, sym = boots
    for site in SITES_A2:
        view, _ = _page_view(g, 4, REVERB, 1)
        ui(g, 3, 246)
        assert g.call_from(site, IS_KIT, [KIT, 246, 4], a2=view) & 0xFF == 1 and g.u32(sym["mg_ctx"]) == 0
        view, _ = _page_view(g, 4, REVERB, 0)
        assert g.call_from(site, IS_KIT, [KIT, 246, 4], a2=view) & 0xFF == 0 and g.u32(sym["mg_ctx"]) == 1
        for bad in (0, 1, 0x8000_0000, FAKE + 2):                       # not a view: the track decides
            ui(g, 12, 246)
            assert g.call_from(site, IS_KIT, [KIT, 246, 4], a2=bad) & 0xFF == 0 and g.u32(sym["mg_ctx"]) == 1
    for site in SITES_TRACK:
        view, _ = _page_view(g, 4, REVERB, 1)
        ui(g, 12, 246)
        assert g.call_from(site, IS_KIT, [KIT, 246, 4], a2=view) & 0xFF == 0 and g.u32(sym["mg_ctx"]) == 1
        assert g.call_from(site, IS_KIT, [KIT, 246, 12], a2=view) & 0xFF == 1 and g.u32(sym["mg_ctx"]) == 0


def test_encoder_helper_reads_its_own_view(boots):
    """The real OS helper 0x4003B4D2 (page views' encoder/trig handling) up to its is-kit call."""
    _, g, sym = boots
    view, _ = _page_view(g, 4, REVERB, 1)
    ui(g, 3, 246)
    assert g.call_from(0x4003_B522, None, [view, 246, 0], entry=HELPER) & 0xFF == 1
    assert g.u32(sym["mg_ctx"]) == 0
    view, _ = _page_view(g, 4, (27, 28, 29), 0)
    assert g.call_from(0x4003_B522, None, [view, 246, 0], entry=HELPER) & 0xFF == 0
    assert g.u32(sym["mg_ctx"]) == 1
    ui(g, 12, 246)


MF = (442, 443, 402, 406, 412, 431, 432)                     # master-filter FLTR TYPE FREQ RESO RET TRIM CMP


def test_master_filter_page_and_names(boots):
    """TEST15: FX track SYN page 1 (page 32, master-comp's page stub): A DRIVE (stock FX DRIVE), B COMP, C ATK,
    D REL, E GATE, F SC, G GR, H LVL (master-filter's TRIM id). SYN page 2 = page 0 (the OS's NONE page, in no tab:
    master-filter's page stub, names SYN2 / Master Filter): A FLTR, B TYPE, C FREQ, D RESO, E CMP, F IN (master-comp's
    meter), G RET (TEST15b, on DRV's old id 412). FLTR pages 1-2 and AMP page 2 (pages 11, 12, 19) are stock again."""
    s, g, sym = boots
    page = lambda u, p: struct.unpack(">8I", bytes(u.mem_read(0x41BA_03C8 + 44 * p + 8, 32)))  # noqa: E731
    names = lambda e, p: (e.cstr(e.u32(0x41BA_03C8 + 44 * p)), e.cstr(e.u32(0x41BA_03C8 + 44 * p + 4)))  # noqa: E731
    assert page(s.uc, 12) == (137, 0, 142, 0, 143, 0, 0, 0)               # stock: DEL, FENR, FPAN
    assert page(s.uc, 19) == (0, 0, 157, 156, 0, 0, 0, 0)                 # stock: AENR, MODE
    for p in (11, 12, 19):
        assert page(g.uc, p) == page(s.uc, p), p
    assert page(s.uc, 0) == (0,) * 8 and names(s, 0)[0] == "NONE"
    assert page(g.uc, 0) == (442, 443, 402, 406, 432, 268, 0, 0)          # FLTR TYPE FREQ RESO CMP IN (TEST17: no RET)
    assert names(g, 0) == ("SYN2", "Master Filter")
    assert page(g.uc, 32) == (150, 262, 263, 264, 265, 266, 267, 431)
    ui(g, 12, 402)
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in MF if i != 412] == ["FLTR", "TYPE", "FREQ", "RESO", "LVL", "CMP"]
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in (150, 262, 263, 264, 265, 266, 267, 268)] == \
        ["DRIVE", "COMP", "ATK", "REL", "GATE", "SC", "GR", "IN"]
    assert [g.fmt(443, v << 8) for v in range(8)] == ["LP4", "LP2", "BP2", "HP2", "NO1", "NO2", "LPN", "THRU"]
    assert [g.fmt(442, v) for v in (0, 0x100)] == ["OFF", "ON"]
    assert g.fmt(402, 0) == "6Hz" and g.fmt(402, 0x7F00) == "20k" and g.fmt(406, 0x4000) == "64"
    assert [g.fmt(431, v) for v in (0, 0x3F00, 0x4000, 0x4100, 0x7F00)] == ["-12.0", "-0.2", "0.0", "+0.2", "+11.8"]
    assert [g.fmt(432, v) for v in (0, 0x100)] == ["MAIN", "FX"]
    assert [g.words(DESC(i) + 8, 3) for i in MF if i != 412] == [[0, 0x100, 0], [0, 0x700, 0], [0, 0x7F00, 0x7F00],
                                                                 [0, 0x7F00, 0], [0, 0x7F00, 0x4000], [0, 0x100, 0]]
    for i in MF:
        if i == 412:                                                   # TEST26: not master-filter's any more
            continue
        assert g.call(IS_KIT, [KIT, i, 12]) & 0xFF == 1
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in (156, 157)] == ["MODE", "AENR"]   # still the OS's own


def test_master_filter_ids_stock_on_their_machines(boots):
    """A track playing one of those drum machines (IMPULSE, or a machine with COL) shows its own knobs."""
    s, g, sym = boots
    ui(g, 12, 402)
    assert ui(g, 2, 402) == 0x5A5A and g.u32(sym["mg_ctx"]) == 1        # the track's own COL value
    assert [g.cstr(g.u32(DESC(i) + 48)) for i in MF] == ["HOLD", "SHP", "COL", "COL", "COL", "NLEV", "NDEC"]
    for i in MF:
        assert g.words(DESC(i), 13) == s.words(DESC(i), 13)
        assert [g.fmt(i, v) for v in VALUES] == [s.fmt(i, v) for v in VALUES]
        assert g.call(IS_KIT, [KIT, i, 2]) & 0xFF == 0
    ui(g, 12, 402)
    assert g.cstr(g.u32(DESC(402) + 48)) == "FREQ" and g.fmt(443, 0x300) == "HP2"
    assert g.cstr(g.u32(DESC(442) + 48)) == "FLTR" and g.fmt(442, 0x100) == "ON"
