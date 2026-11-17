# Status: what is checked, and where

**Whole package: EXPERIMENTAL.** Here is how each part stands:

* **Tried on the author's unit:** the earlier JOG-page rounds (the page, VINYL touch, LOAD, RANGE, PHASE, the
  display switch). His notes shaped TEST35.
* **Not yet on a unit:** TEST35a (Syntakt Performance Mods).
* **Shelved:** LINK.

## Checked in the emulator (this repository's tests, per OS tree)

* **The JOG page:**
  * the page and its keys;
  * the ring and VINYL touch;
  * PHASE;
  * the real interrupt path;
  * PERSONALIZE;
  * round 3: pause, phrase counter, pitch and MASTER TEMPO, brake fade, glides, reset;
  * the screens (the CDJ rings turn).
* **TEST35a, the knobs:**
  * the layout: B LOAD, C START, D BRAKE, E RANGE, F PHASE, G and H nothing;
  * the detents: 3 or 2 a step, and a turn back or another knob starts the count over;
  * the mode comes from PERSONALIZE.
* **TEST35a, LOAD:** eight distinct weights. From a 2 % bend, LOAD 1 is back exactly to the set tempo in about
  0.28 s and LOAD 8 in about 2.3 s, with no slow tail.
* **TEST35a, PERFORM's filter:**
  * the fine position;
  * the stop at THRU;
  * the 16-bit cutoff glided into the filter's smoothed FREQ (monotonic, at most 1/32 of the way a block, off the
    256 grid);
  * the knob byte follows, rounded;
  * a change from elsewhere gives the filter back;
  * PERFORM starts where the filter is.
* **TEST35a, the PERFORM screen:**
  * the header's Hz matches master-filter's measured map;
  * a sine at 100 Hz, 1 kHz or 10 kHz lands in its own column.
* **perf-filter:** bit for bit the FX-page master filter's audio. Six random kits × 300 blocks: the same copy of
  the live values and the same CVs from the same knobs, every type, ON / OFF, glides, routing masks.
* **The builder:**
  * every selection is consistent;
  * PERFORM is linked to perf-filter;
  * the trimmed builder gives byte-identical files to the full MAX builder's catalog.
* **The add-on:**
  * reproduces MAX 1.0's golden hash;
  * merges the Performance Mods cleanly (boot margin 16,957);
  * the merged image boots through the OS's own area loader with every chunk in place.

## On the final images (as the unit runs them)

Three TEST35a files were checked: the Performance Mods alone (OS 1.41 and 1.42), and the author's set + crash
tripwire with PERFORM on his master filter (OS 1.41). The image is booted through the area loader.

* The JOG, round-3 and Performance Mods tests pass on all three.
* PERFORM is linked to the right filter in each.
* The spectrum and header tests pass.

In the real audio interrupt (OS 1.41):

* the FREQ word the OS reads glides smoothly to PERFORM's target and lands within 4/256 of a step;
* the tracks are routed into the FX block;
* the spectrum tap fills its ring;
* the TUNE follow, MASTER TEMPO and the brake fade behave as before;
* the peak stack is 844 bytes, the same as stock.

## Not proven on a unit (TEST35a)

* **How the filter sweep feels.** The cutoff now moves in steps 256 times finer than before. Whether the analog
  filter's CV DAC resolves all of that (or a few steps of it) shows only on the unit. Either way the sweep is
  glided.
* **The spectrum's level.** The scale assumes full scale at 2^28 in the OS's main-mix copy (the bus is ×8 before
  the DACs). If the bars sit too low or too high on the unit, it's one constant to move.
* **The screen's pace.** PERFORM redraws 15 times a second. A redraw costs about 66,000 instructions in the UI
  task, which by our estimate is a few percent of what the UI gets while the audio interrupt runs. Check that the
  screen keeps up and other pages stay smooth.
* **The heap block** for the spectrum (about 5 KB, taken once at the first PERFORM). It's the OS's own allocator,
  used the way the PERSONALIZE line already uses it.
* From TEST34a, still open:
  * TUNE's fine steps;
  * the analog tracks following the pitch;
  * [FUNC] + [TRIG] reaching the page;
  * the tempo setter called from the drawing;
  * the brake fade.
* **Without FM4:** the trimmed builder uses the no-FM4 form of the parameter hooks and the MIDI id guard. That form
  is checked in the emulator only.

## Cost (audio interrupt, instructions a block; stock 68,715)

| Build | At rest | PERFORM's filter gliding | + spectrum tap |
|---|---|---|---|
| Performance Mods alone (OS 1.41) | 69,006 | 69,271 | 69,991 |
| Author's set + tripwire (OS 1.41) | 69,459 | 69,743 | 70,463 |

The spectrum tap (about 730 instructions) runs only while PERFORM is on screen. The FFT runs in the drawing, not in
the interrupt.
