# midi-guard

Keeps the mods' controls off the stock pages whose parameter ids they borrow. Needs [vparams](../vparams) v4.

The Syntakt has no unused parameter id: every one is on a page, MIDI-mapped or used by code. The mods
therefore borrow ids that only appear **off the FX track**:

| Ids | Stock (other tracks) | Mod (FX track; FX3 page from any track) |
|---|---|---|
| 246–253 | MIDI machine SRC page: CHAN BANK SBNK PROG PB AT MW BC | fx3 page (REVERB page 2) |
| 262–268 | MIDI machine CC SELECT 1–7 | master-comp (SYN page) |
| 269 | MIDI machine CC SELECT 8 | beat-repeat RPT1 (TRIG page A) |
| 445, 446 | IMPULSE machine REP, NUM (no CC/NRPN, not LFO destinations) | beat-repeat RPT2, RPT on/off (TRIG page B, H) |
| 442, 443, 402, 406, 412 | IMPULSE HOLD, SHP; COL of three drum machines (no CC/NRPN, not LFO destinations) | master-filter FLTR, TYPE, FREQ, RESO, DRV (FLTR page 2: B, C, D, F, G) |
| 431, 432 | NLEV, NDEC of a fourth drum machine (group 31; no CC/NRPN, not LFO destinations) | master-filter TRIM, CMP (AMP page 2: A, B) |
| 254–261 | MIDI machine CC VALUE VAL1–VAL8 (CC 70–77) | SY FM4 page 2 ([fm4](../fm4)), only while that page is on screen: see "SY FM4 scope" |

Up to MAX 1.0 these ids were the mods' everywhere: a MIDI track's SRC page showed FX3, its CC SELECT page the
compressor, and beat-repeat's RPT2 sat on id 124 (**Reverb FX Routing**), breaking the FUNC+FX routing toggle,
the routing shown on the reverb sends and that LFO destination. Id 124 is now stock again.

## How it works

- **Two contexts.** FX: the mods' descriptors and objects are live, exactly as before. Stock: the stock
  descriptors (names, ranges, defaults) and per-parameter objects (encoder type, value prototype, formatter,
  graphic, style) are live and vparams lets the OS answer is-kit, get and set.
- **The context follows what the page views show**: every page view calls is-kit (0x4000D870) with the
  project's active track (view +116 = project + 48) before reading or writing a slot. vparams calls
  `mg_ensure()` only from those call sites (`vp_sites`) and picks FX when the track is the FX track (12)
  **or** the calling view shows the FX3 page (REVERB page 2, page 25: the DELAY/REVERB tabs open from any
  track), stock otherwise. The page is `pages[pos]` of the view (vector +124/+128, position +144, as the OS's
  own id-under-slot reads it), read only at the four ParameterPageView sites where the view is in a2, with
  the pointers checked first. MIDI CC/NRPN input and the FX routing code never switch.
- **is-kit for a borrowed id** says "kit parameter" in the FX context to the page views (FX track or FX3
  page, whatever the active track), and to any other caller only for track 12.
- **Switching** exchanges the words that differ (descriptor min/max/default/names; object type, value
  prototype, formatter, graphic, style) with a shadow copy, so each `std::function` keeps one owner. The stock
  objects are built once, on the first switch, with the OS copy constructor from the OS prototypes, as the
  static initializer builds them (recipe extracted by emulating the stock initializer, `recipe.py`).
- **Safety:** no formatter, graphic or style of these ids calls is-kit (checked in the emulator for both
  versions), so a switch never happens while one of them runs; switches happen in UI code only.

## SY FM4 scope (with [fm4](../fm4))

FM4's page 2 (SY TONE's second SYN page) uses ids 254–261, the MIDI machine's CC VALUE knobs. They keep the
stock descriptors and objects; while FM4's page 2 is on screen `mg_fm4_ensure(1)` exchanges them with FM4's:

- **Rows:** RC2's descriptor rows.
- **Objects:** copied with the OS copy constructor from FM4's SY TONE donors (192 191 192 194 191 192 194 369), as FM4's own page-2 setup would. mods/fm4 presets FM4's flag, so FM4 itself never touches OBJ(254–261).
- **Exchange:** the 13 descriptor words and object words 0–20 are swapped, so each `std::function` keeps one owner.

What decides:

- **The generic page draw prologue** `0x4003A244`, hooked (`mg_draw_hook`) before any slot is read. The context is FM4 when the view is a SourcePageView (vtable `0x401CA0DC`) whose slot A (its own slot-id function, as the draw asks next) is one of the ids, and stock otherwise.
- **vparams' `vp_ctx`** at every page-view is-kit call (`mg_fm4_view(view or 0, id)`):
  - a SourcePageView (view in a2) asking about one of the ids: FM4;
  - any other view, whatever the id (the MIDI pages' view `0x401C8838` included): stock;
  - the page-view sites that don't pass the view (AMP, FILTER, LFO, MASTER; none of them shows FM4's page): stock;
  - a SourcePageView asking about another id: no change (the next draw decides).

So FM4's rows are live only while FM4's page 2 is the page on screen. Is-kit calls from anything but a page view never switch.

The OS's CC/NRPN tables are built at boot from the stock rows, so CC 70–77 reach VAL1–VAL8 on MIDI tracks; the stock OS maps no NRPN to them. While FM4's rows are live, the OS's CC and NRPN lookups `0x400A671E` / `0x400A679E` (hooked: `mg_cc_filter`, `mg_nrpn_filter`) report no parameter for 254–261. Such a message is ignored rather than written to FM4's keys, and MIDI input never swaps anything.

Limits (the swap exchanges whole rows, storage key included: group 57 / logical 0x19–0x20 for VAL1–VAL8,
group 4 / logical 0x36–0x3D for FM4):

- **While FM4's page 2 is on screen**, OS code that reaches a MIDI track's VAL1–VAL8 *by id* uses FM4's rows: the
  MIDI track's unused slots 0x36–0x3D, FM4's ranges. MIDI input is filtered (above). Not filtered: Overbridge/USB
  parameter control (the RPC handler `0x40089688` sets parameters by id). Not traced: whether the MIDI tracks' LFO
  and p-lock output look these ids up by descriptor. If they do, a MIDI track's VAL1–VAL8 modulation misbehaves
  while that page is open and is back to normal when you leave it; the stored VAL values are not touched.
- **The rest of the time** the stock rows are live, so code that reached FM4's knobs on an SY TONE track by id
  would land on logical 0x19–0x20. FM4's sound does not depend on that: the voice update (`0x400A3052`), FM4's
  publisher, its lock lanes 0x50–0x57 and sound save/load all work by logical index. FM4's own page reaches them
  by id with FM4's rows live.
- **cc-labels** links at `+0x8800` too (and labels the same ids 254–261), so it needs a new address and a look at
  the FM4 scope before it can be built in with FM4.

The code is in the mod area at `+0x8800`; `+0x5000` is FM4's since TEST12. `tests/test_fm4_scope.py` covers:

- the boot state, compared with a stock boot;
- the CC/NRPN tables;
- the swap both ways, back to the exact boot state;
- the draw hook, and the is-kit decision at every kind of page-view site (and none from other callers);
- the lookups while FM4's rows are live.

## Build / test

```sh
python mods/fm4/make_patch.py             # first, for the SY FM4 scope
python mods/midi-guard/make_patch.py      # then: vparams reads its symbols
python mods/vparams/make_patch.py
python mods/beat-repeat/make_patch.py
python -m pytest tests/test_midi_guard.py tests/test_beat_repeat.py
```

`tests/test_midi_guard.py` boots the whole build through the real static initializer and drives the OS's own
ParameterPageView get/set-value: stock descriptors, objects and texts on MIDI/IMPULSE tracks, the mods' state
intact on the FX track, REVERB page 2 showing and turning fx3 from any track (never the track's MIDI
parameters), every `vp_sites` entry, unusable page vectors, id 124 identical to stock, no switch from other
callers.
