# master-filter

**Analog master filter**: the Syntakt's analog FX block (filter, overdrive, VCA) filters the whole mix, with
its own settings, and gives your routing and FX settings back when you switch it off.

TEST15: the controls moved to the FX track's **SYN page 2**, next to [master-comp](../master-comp)'s BOUM-style page
(SYN page 1: DRIVE COMP ATK REL GATE SC GR LVL). The kit's own FX DRIVE (SYN page 1 A) is the drive when you switch
it on, CMP chooses where COMP, GATE and LVL act, and TRIM became LVL, the output level of the whole chain, filter ON
or OFF. The FX block has one filter: while it is the master filter, the kit's own FX filter settings (type, cutoff,
resonance, envelope) are replaced by the master filter's.

**TEST15b** (after the author's "DEL/REV sends drop out with FLTR on"): **RET** (slot G) chooses whether the delay and
reverb returns go through the master filter (FLTR, as before) or stay where the kit routes them (KIT); and with FLTR
ON the delay keeps feeding the reverb when the FX track's AMP DEL is above 0 (the OS's loop guard used to cut it, see
below). DRV's leftover code is gone (its id is RET's).

## Use

FX track → **SYN** page 2 (the OS's unused page 0, named SYN2 / "Master Filter", made the SYN tab's second page):

| Slot | Knob | Range |
|---|---|---|
| A | FLTR | **OFF** / ON: the master filter's switch (drawn and turned like AENR) |
| B | TYPE | LP4, LP2, BP2, HP2, NO1, NO2, LPN (the FX block's filter modes, drawn with the FX track's own filter icons as on its FLTR page), THRU (through the FX block with its filter's own OFF type, held fully open with no resonance: drive and VCA only; shown as text). Default LP4 |
| C | FREQ | 0 … 127, the FX block's cutoff scale (default 127), **shown in Hz**: `6Hz` … `20k`, about 1.1 semitones per step (see below) |
| D | RESO | 0 … 127, **Polivoks-style** (see below): 0 … 63 as the FX filter's own RESO, 63 … 127 a straight climb past its maximum (passed at about 89) |
| E | CMP | **MAIN** (default) / FX: where master-comp's COMP, GATE and LVL act: every path to the main mix, or only the FX block's output |
| F | IN | master-comp's input meter (read only): the level its detector hears |
| G | RET | **FLTR** (default) / KIT: the delay and reverb returns go through the master filter with everything else, or stay where the kit routes them ([FUNC] + [FX], trig keys 14 and 15). TEST15b |

SYN page 1 H, **LVL** (this mod's TRIM id): −12.0 … +11.8 dB (0.19 dB per step, default 0.0), the output level of the
chain, always on (filter ON or OFF), gliding (~21 ms); applied by master-comp with its gain (CMP MAIN: every path to
the main, FX: the FX block). Use it to make switching the filter or the compressor on level-neutral.
FLTR page 2 (DEL, FENR, FPAN) and AMP page 2 (AENR, MODE) are stock again (up to TEST14c the master filter's knobs
were on FLTR page 2 and TRIM/CMP on AMP page 2).

- **FLTR ON:** tracks 1–12, the delay and reverb returns (RET FLTR) and the external input all go through the FX
  block. Its filter type, FREQ and RESO come from these knobs, its DRIVE stays the kit's (SYN page 1 A, p-locks
  and LFOs included); the FX track's filter envelope depth is held at 0 and its filter pan centred, so FX-track
  trigs, p-locks and LFOs don't move the master filter. FX3's return goes through the FX block either way (fx3
  adds it to the FX block's bus).
- **FLTR OFF:** the next audio block plays the kit's own routing and FX settings again. FREQ, RESO, envelope
  depth and filter pan glide back to the kit's values (at most 0.17 s). While it is OFF, TYPE and the
  other knobs can be set without touching the sound: ON applies them at once, without passing through the
  types in between.
- **Nothing is saved or overwritten:** the kit, the pattern and the routing menu (FUNC + FX) keep showing and
  saving your own routing. The master filter's settings are global, start at FLTR OFF (TYPE LP4, LVL 0.0, CMP
  MAIN, RET FLTR) at power-on and stay the same across pattern changes (the kit's FX block has no free word left:
  fx3, master-comp and beat-repeat use them all). So a power cycle switches the master filter off.
- **What switching on changes** (the FX block becomes the end of the chain): every track and return goes through
  the FX block's drive, filter and amp. The drive is the kit's (SYN page 1 A), so the tracks already on the FX
  block keep their grit and level (the OS keeps the FX path's level flat from DRIVE 0 to 64 and lets it rise above
  64); the tracks that were direct pass the kit's drive too (no added saturation at 64 or below). They also get the
  FX AMP VOL, the mixer's FX level and the FX amp envelope. With CMP MAIN the dynamics' input and gain don't change
  on switching on.
- **The FX AMP page stays yours:** VOL, PAN and the amp envelope apply to everything while the master filter is
  on. In the default AHD- (inverted, ducking) mode FX-track trigs duck the whole mix; muting the FX track
  stops its trigs, so the ducking stops. In AHD or ADSR mode the amp only opens on FX trigs (as for any track
  routed through the FX block in the stock OS), so with the master filter on the mix only sounds on FX trigs.
- **The FX AMP page's own DEL/REV sends** (the FX block's output into the delay/reverb): while a return goes
  through the FX block the OS mutes the FX block's send to it (the manual: no feedback loop). With RET FLTR the
  returns are in the FX block, so those two sends do nothing while the master filter is on. **RET KIT** keeps a
  return the kit routes direct out of the FX block, and its FX AMP send works again (a return the kit routes through
  the FX block is muted as in the stock OS).
- **Delay into reverb (TEST15b):** the OS also cuts the delay's REV send (delay → reverb) while the reverb return
  goes through the FX block and the FX AMP DEL is above 0 (`0x4008F838`: reverb → FX block → FX DEL → delay →
  reverb could loop). With the delay's return in the FX block too, that loop can't close (its FX DEL send is muted
  already), so the master filter sets the copy's FX AMP DEL to 0 then: the delay keeps feeding the reverb. Up to
  TEST15, FLTR ON with FX AMP DEL above 0 (a kit value, a p-lock or an LFO) silently removed the delay's reverb.
- **Routing settings are respected:** a track, the delay or the reverb taken off the main mix in the routing
  settings keeps its own routing (through the FX block it would reach the main again). If the FX block itself
  is off the main mix the master filter does nothing.
- **Polivoks-style RESO:** the OS sets the analog filter's resonance CV from a table per filter type that
  flattens out at the top (RESO 64–127 covers only 16 % of its range, so the top half of the stock knob barely
  changes the sound) and stops below the point where the filter screams. With the master filter on, RESO 0–63
  is exactly the stock CV; from 63 the CV climbs in a straight line to the stock maximum **plus a quarter of the
  type's whole table range** (LP2 930 → 2412, LP4 1250 → 1818, BP2 450 → 1812, HP2 366 → 1707, LPN 560 → 1950,
  NO1 −3000 → 250, NO2 −300 → 875), passing the stock maximum at about RESO 89. The OS's cutoff compensation
  (less resonance at the highest cutoffs) still applies. **Experimental:** the analog circuit was never driven
  past the stock maximum by the OS, so keep the volume down the first time you turn RESO past ~90 (it can
  self-oscillate and get loud, especially with the FX DRIVE up). The `hot` build (`MF_PUSH=hot`) pushes twice as far
  (LP2 → 3895, passed at about RESO 80). Units whose calibration selects the older linear resonance path
  (`0x43BDC044 & 31` ≤ 1) keep the stock behaviour.
- **Overbridge:** the FX block's output is digitised and mixed into the main stream, so the master filter is
  on Overbridge main L/R too (LVL and the compressor's gain are not: they work on the analog VCAs); the per-track
  streams stay unfiltered, as in the stock OS.
- Turning it on/off and changing TYPE flip analog switches in the FX block, as routing changes in the stock
  OS do: they can click. Turning TYPE while ON steps through the types in between, like the FX track's own
  TYPE.

### MIDI

On the **FX CONTROL CH** (SETTINGS > MIDI CONFIG > CHANNELS), with RECEIVE CC/NRPN on:

| Knob | CC | NRPN | In | Out |
|---|---|---|---|---|
| FLTR | 3 | 1:48 | 0–63 OFF, 64–127 ON | 0 / 127 |
| TYPE | 9 | 1:49 | 0–15 LP4, 16–31 LP2, 32–47 BP2, 48–63 HP2, 64–79 NO1, 80–95 NO2, 96–111 LPN, 112–127 THRU | 0, 18, 36, 54, 73, 91, 109, 127 |
| FREQ | 12 | 1:50 | 0–127 | 0–127 |
| RESO | 13 | 1:51 | 0–127 | 0–127 |

- LVL (TRIM), CMP and RET have no MIDI numbers (knob turns send nothing). TEST15: DRV's CC 14 / NRPN 1:52 are gone;
  the OS handles them as stock (nothing on the FX channel).
- **In:** these numbers do nothing in the stock OS on the FX channel; every other CC/NRPN works as before. On
  AUTO CHANNEL they reach the master filter while the FX track is the active track (stock behaviour). NRPN: the
  data entry MSB (CC 6) is the value. FREQ keeps its glide, so CC steps are smooth.
- **Out:** turning the knobs on SYN page 2 sends them like the stock knobs: only with ENCODER DEST = INT+EXT
  (MIDI CONFIG > PORT CONFIG), CC or NRPN as PARAM OUTPUT says, on the channel the OS uses for the FX track's own
  knobs (OUTPUT CH = TRK CH: the FX CONTROL CH; AUTO CH: the AUTO CHANNEL; OFF: nothing). Incoming messages are
  not sent back out.

## How it works

- The audio interrupt (`0x400A3856`) rebuilds a copy of the live parameter values at `0x80006348` every block:
  `0x40097952` smooths the engine words (`0x800021B0`) into it, then the LFOs and modifiers are
  applied to the copy. Every routine that programs the analog hardware and the mix reads only that copy:
  FX filter CVs `0x40095DA4`, CVs/switches/levels `0x400903CA` (analog voices `0x4008FF48`), `0x40095794`,
  mix `0x4008F1CA`.
- `mf_fx_hook` replaces the call of the first of them (`jsr 0x40095DA4` at `0x400A4F24`): `mf_apply` edits the
  copy, then it jumps to `0x40095DA4` with the stack as the OS built it. Words (byte offsets in the copy):
  track *t* ROUT `142t + 126`, delay/reverb/input FX routing `1782`/`1800`/`1818` (0 = through the FX block),
  FX filter TYPE `1820` (0–7, 7 = OFF), FREQ `1822`, RESO `1824`, ENV `1826` (0x4000 = 0), FPAN `1840`
  (0x4000 = centre), FX AMP DEL `1858` (0 while the delay's return is in the FX block, TEST15b). DRIVE (`1856`)
  stays the kit's. RET KIT leaves `1782`/`1800` as they are. The OS keeps its smoothing state elsewhere
  (`0x8000E9B0`), so the edits last one block and OFF gives the kit's words back at once.
- Routing to main: kit word `0x80003148` (bit 15 set → global word `0x8000314C`), bits 0–11 tracks, 12 delay,
  13 reverb, 14 FX block; set bit = off the main mix (the mix gates only the direct path with it, so a track
  routed through the FX block would be on the main again).
- FREQ, RESO, ENV and FPAN glide (one-pole, 1/32 per block, ~21 ms, like the OS's own smoothing; snap
  within 1/16 of a step): switching on jumps to the master values, knob moves glide, switching off glides back
  to the kit's values of each block (at most 256 blocks). Routing and TYPE switch at once.
- **FREQ in Hz:** the OS has no Hz scale for the analog FX filter (it shows 0.00–127.00) and the cutoff depends on each unit's factory calibration. The display comes from cutoffs measured on a Syntakt (BP2, high RESO, noise, spectrum analyser; `MEASURED` in `make_patch.py`): the least-squares line in octaves, about 5.9 Hz × 2^(0.0926 · FREQ), within 0.18 octave of every measured point. Other units can differ by a few percent; below ~15 Hz it is extrapolated.
- **DRIVE:** always the kit's word (p-locks and LFOs included). Up to TEST15 a DRV knob (KIT or 1–127, with a glide)
  could replace it; TEST15 removed the knob, TEST15b the code, and its id became RET.
- **LVL (TRIM):** `mf_post_gain` (Q12), set at the start of `mf_apply` every block, filter ON or OFF:
  `TRIM_Q12[TRIM]`, one-pole glide (1/32 per block, snap within 1/256; nothing to do once there). [master-comp](../master-comp)
  folds it into its gain (`k_g` = G × LVL), later in the same audio block: CV 35/36 in both modes, and in CMP MAIN the
  direct analog VCAs and the direct digital bus too. Up to TEST14c it was unity while the filter was OFF.
- **CMP:** `mf_p[6]` (exported as `mf_cmp`), 0 MAIN, 1 FX, read by master-comp every block.
- **Cost per block** (instructions, emulator; 1500 blocks/s): ~20 with the switch OFF (the LVL check, then
  `filter_block` only while ON or gliding back), ~280 on, ~70 for the resonance. No audio processing, no EMAC.
- **Controls:** ids 442 (IMPULSE HOLD: FLTR), 443 (IMPULSE SHP: TYPE), 402, 406, 412 (COL of three drum
  machines: FREQ, RESO, RET), 431, 432 (NLEV, NDEC of a fourth, group 31: TRIM/LVL, CMP): no CC/NRPN of their own in
  the OS's tables, not LFO destinations, only on those machines' SYN pages (vparams slots 18–24).
  [vparams](../vparams) routes them here and [midi-guard](../midi-guard) gives those machines their stock knobs back
  on their own tracks. The TYPE and FLTR objects are set at boot (`mf_page_stub` at `0x40194BC0`; FLTR is a copy of
  AENR's object made with the OS's `std::function` copy constructor); TYPE's graphic calls the FX filter TYPE's stock
  graphic `0x40070B10` (frame of the 21 × 17 icon strip `0x444E100C`, filled at run time by the resource loader from
  ROM) for LP4…LPN. TRIM/LVL keeps NLEV's 0..127 knob with a dB text; CMP and RET are copies of AENR's object with
  MAIN / FX and FLTR / KIT texts. Code at mod area `+0x6300` (`+0x6000`–`+0x62A4` is left free for the FM4 port).
- **SYN page 2 (TEST15):** the FX track's SYN tab is a generic ParameterPageView (vtable `0x401C8D94`, built at
  `0x40035D1E`) whose page vector the OS fills from a one-entry array, {32} (`moveq #1` at `0x40035CF4`, array operand
  at `0x40035CFA`). The patch makes it two pages, {32, 0} (`moveq #2`, `mf_syn_pages`): page 0 is the OS's NONE page,
  in no tab and empty in the stock OS, so the SYN button now steps SYN 1 → SYN 2 like the audio tracks' two SYN
  pages (same base view). `mf_page_stub` writes page 0's slots (A–G above), and the page initializer's two string
  copies for page 0 (operands at `0x401942CE` / `0x401942FE`) take `mf_page0_s` / `mf_page0_l` ("SYN2", "Master
  Filter") instead of "NONE" / "None": they show in the page header and in the COPY/PASTE/CLEAR PAGE messages. The
  mod area is unpacked at the BSS clear, before the initializers run, so those strings are there. Page 0 is drawn by
  the OS's generic 8-slot draw `0x4003A244`, as page 12 was. FLTR page 2 (page 12) and AMP page 2 (page 19) are no
  longer touched, and TEST9/TEST14's AMP-view branch at `0x40041EC2` (`601e` → `601a`) is gone.
- **Resonance:** `mf_fx_hook` calls the OS's FX filter CV routine `0x40095DA4` (instead of jumping to it) and
  then `mf_post` with the same two arguments. The OS writes the resonance CV at CV struct `+78` as
  `table[type][RESO >> 8] − comp[FREQ >> 8]` (tables `0x40249718`–`0x40249E18`, 128 words each, higher = more
  resonance; compensation `0x40249A18`; OFF/THRU −20000) when `(0x43BDC044 & 31) ≥ 2`, else `0x7E6F − RESO`.
  `mf_post` (switch ON, type ≠ THRU, table path only) writes it again: the table (interpolated between steps)
  up to RESO 63, then the line to `table[127] + (table[127] − table[0]) >> 2` (`>> 1` hot), minus the same
  compensation, clamped to 16 bits. Nothing else in the CV struct changes; no other routine writes `+78` in
  normal play (the other writers are the MFILTER calibration steps).

- **MIDI:** the OS maps incoming CC/NRPN numbers to parameters with tables it builds once at boot from the
  descriptors (`0x400A5E4C`). `mf_cc_lookup` / `mf_nrpn_lookup` replace the table lookups of the CC handler
  `0x4001C12C` (`jsr 0x400A671E` at `0x4001C17A`) and the NRPN handler `0x4001C262` (`jsr 0x400A679E` at
  `0x4001C2B4`): for the FX track (12) and the numbers above `mf_midi_in` sets the knob and the handler leaves
  through its own exit (`0x4001C256` / `0x4001C418`), as after a parameter change; anything else goes on to the
  OS's lookup with the stack as the handler built it. Out: `mf_set`, called from the page view's set-value
  (return address `0x400380E4`, or `0x40037F92`), checks ENCODER DEST (`0x4002151E`), takes the OS's channel
  for parameter changes (`0x40013298`) and PARAM OUTPUT (`0x4002149A`) and sends through `0x401066B4` (CC) or
  `0x401066FC` (NRPN), as the OS's own parameter send `0x4001316C` does. MIDI settings: project object
  (`0x4016E804`) + 48, data via its method +40: +88 AUTO CHANNEL, +92 + 4·t track channels, +140 FX CONTROL CH
  (−1 = OFF), +168 PARAM OUTPUT (0 NRPN, 1 CC), +208 ENCODER DEST (0 INT, 1 INT+EXT), +216 OUTPUT CH (0 AUTO CH,
  1 TRK CH).

## Build / test

```sh
python mods/midi-guard/make_patch.py
python mods/vparams/make_patch.py
python mods/master-filter/make_patch.py
python mods/master-comp/make_patch.py      # it links master-filter's CMP byte and TRIM word
python -m pytest tests/test_master_filter.py tests/test_master_filter_midi.py tests/test_midi_guard.py tests/test_master_bus.py
```

`tests/test_master_filter.py`: the hook enters the OS routine with the OS's stack and registers; OFF leaves the
copy bit-exact; ON edits exactly the routing and FX filter words (route-to-main settings kept, global setting,
FX block off main); jumps, glides and the glide back; parameters and texts; cost; and the stock CV routines run
on the edited copy switch all four analog voices and the input into the FX block, set the filter mode and the
cutoff CVs, exactly as for a kit routed and set that way by hand. The DRIVE word stays the kit's (any value, ON and
OFF); RET KIT keeps the kit's return routing; FX AMP DEL is 0 only while the delay's return is in the FX block (RET,
off-main delay, switch OFF); RET, FLTR and CMP are drawn and turned like AENR; LVL's gain glides with the filter ON or
OFF and stays when the filter or the FX block's main routing changes (TEST15); TRIM/LVL, CMP and RET texts.

`tests/test_master_filter_midi.py`: CC and NRPN through the OS's own handlers (every value of every knob; the
handler returns with its stack and registers as after a parameter change); every other message, on every track,
DRV's old CC 14 / NRPN 1:52 included, gets exactly the OS's lookup result (tables built by the OS's own builder);
the numbers are unused in the OS's FX-channel tables; knob turns send byte for byte what a stock FX knob sends (the
OS's own `0x4001316C`, FX FREQ), with our number, on the channel the OS picks (TRK CH / AUTO CH / OFF), CC or NRPN,
nothing with ENCODER DEST = INT, for other callers, unchanged values, incoming messages, TRIM/LVL, CMP or RET.

`tests/test_audio_isr.py` (opt-in, `MAX_SYX`/`MAX_MANIFEST` = a built image; [tools/emu/isr](../../tools/emu/isr)):
the whole audio interrupt with FLTR ON is bit-identical to stock set up the same way by hand (RET FLTR/KIT, returns
direct / in the FX block), the delay keeps feeding the reverb with FX AMP DEL above 0, the FX block's own sends
follow RET.

`tests/test_midi_guard.py::test_master_filter_page_and_names`: SYN page 1 (page 32) and page 2 (page 0) slots and
page 0's names on a full boot, pages 11, 12 and 19 identical to stock.
