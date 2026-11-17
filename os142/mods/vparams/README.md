# vparams

Shared "virtual parameters" for mods: hidden parameter ids that a mod reads and writes its own way (RAM state, free kit words…) instead of the OS.

- Hooks the three central kit-parameter functions: is-kit `0x4000D870`, get `0x4000D94A`, set `0x4000DA32`.
- Table at mod-area offset `+0x8000`: 32 entries `{id, get, set}`. Each mod writes its entries with `vparams.entry(slot, id, get, set)` (an appended patch). Registered ids report "kit = 1"; get/set jump to the mod with the OS stack layout. Other ids resume the original code unchanged.
- Slots: 0–6 master-comp, 7–8 and 17 beat-repeat, 9–16 fx3, 18–24 master-filter.
- Borrowed ids (246–269, 445, 446, 442, 443, 402, 406, 412, 431, 432; see [midi-guard](../midi-guard)) are the mod's only in midi-guard's FX context. v4: the page views switch to it on the FX track or when they show the FX3 page (REVERB page 2) from any track; stock context otherwise.
- With midi-guard's SY FM4 scope ([fm4](../fm4)): every page-view is-kit also calls `mg_fm4_view(view or 0, id)` (view = a2 at the sites that pass it, else 0). FM4's rows for 254–261 when a SourcePageView asks about one of them; stock rows from any other view and from the sites without a view; no change when a SourcePageView asks about another id.

Tested through `tests/test_master_comp.py` (including "other ids behave exactly like the original"), `tests/test_beat_repeat.py` and `tests/test_midi_guard.py`.
