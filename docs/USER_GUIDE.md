# Syntakt Performance Mods: user guide

The jog lives on its own page.

* To open it: **hold [TEMPO]**, or push knob **A** in the TEMPO menu.
* The TEMPO menu itself is stock.
* **PERFORM** is the page next to it: **[RIGHT]** goes there, **[LEFT]** comes back.

This guide matches the TEST35a code. [STATUS.md](STATUS.md) marks each item as checked in the emulator and/or on a
unit.

## The platter

A platter turns once a bar; 12 o'clock is the one. It follows the sequencer:

* a new pattern starts it at the top;
* [STOP] resets it;
* **[PLAY] while playing pauses it exactly where it is**; [PLAY] again carries on from there, still on the bar.

SETTINGS > PERSONALIZE > **JOG DISPLAY** picks **VINYL** or **CDJ**. It's the look only: in both, pushing A
touches the platter (BRAKE, HOLD, START).

* **VINYL:** a record with grooves and strobe dots. The strobe dots stand still at the set tempo and turn while the
  jog moves it.
* **CDJ:** a CDJ jog display. The inside (the marker) turns with the platter. The outer ring of strobe dots (the
  same as VINYL's) and the tick ring stand still and turn only while the jog moves the tempo.

## Knobs

| Knob | Job |
|---|---|
| **A** | The jog. Spinning bends the tempo by how fast you spin; the bend eases back by LOAD when you stop. Each click is a fixed 0.25 %. **Pushing A touches the platter**: BRAKE to a stop, HOLD, START back up. Turning while pushed walks the beat on. |
| **B** | **LOAD**, the jog's weight, 1–8. From a 2 % bend, LOAD 1 is back in about 0.3 s and LOAD 8 coasts about 2.3 s, with no slow tail at the end. Default 3 (about 0.6 s). |
| **C** | **START** time (0–3 s; pushed while turning: 0.5 s a step). |
| **D** | **BRAKE** time (0–3 s; pushed while turning: 0.5 s a step). |
| **E** | **RANGE**: the bend cap (6 / 10 / 16 % / WIDE). |
| **F** | **PHASE**: an exact nudge. One step is 1/360 of a beat; pushed while turning, ten times that. |
| **G**, **H** | Nothing. |

The selection knobs don't skip:

* LOAD moves one step every **3 detents**, RANGE (only four choices) every **6**;
* START, BRAKE and PHASE move one step every **2 detents**;
* turning back, or turning another knob, starts the count over.

A pop-up shows each setting with its knob letter.

### Pitch follows the nudge (like a CDJ)

Spinning A, or holding the platter, bends the tempo **and** the pitch together. The line under the BPM shows how
far it has bent, in semitones (`+0.53 ST`).

**[YES] = MASTER TEMPO**: a pop-up confirms it, an `MT` box sits top left, and only the tempo moves.

How it works: every audio block, the jog adds the same pitch offset to each track's TUNE in the live copy that the
voices read, not in your pattern. Nothing is saved, and the offset is gone the moment you are back on tempo. A few
machines have no TUNE (CY ALLOY, for one) and keep their pitch.

In VINYL, below about a quarter of normal speed, the brake also turns the tracks' volume down with the speed, like
a platter running down. Again this is on the live copy: your AMP VOL is untouched.

## DJ tools

**Phrase counter** under the platter: `9/16` is bar 9 of a 16-bar phrase.

* In the last 4 bars it blinks in brackets (`[14/16]`).
* **[FUNC] + H** sets the length: 8, 16, 32 or 64 bars.
* **[FUNC] + [YES]** restarts it at bar 1.

**Tempo memories:** **[FUNC] + [TRIG 1 / 2 / 3 / 4]** glides to **130 / 140 / 150 / 160 BPM**.

* The glide takes 4 bars by default. **[FUNC] + G** sets its length: CUT (jump), 1, 2, 4, 8 or 16 bars.
* It moves in equal steps and never overshoots. You land on exactly `140.00`.
* While it glides, the screen shows `GLIDE`, a progress bar and `TO 140.00`.
* LEVEL, [UP] or [DOWN] cancels it where it is. Spinning A doesn't (you can nudge on top of a glide).

**Tempo reset:** **[FUNC] + [NO]** glides back to the tempo the page had when you opened it.

**[FUNC] held** shows all the settings in knob order (LOAD, STRT, BRK, RNG, PHR, GLD) and the memories.

## PERFORM page

**[RIGHT]** on the JOG page opens PERFORM, which takes the whole screen; **[LEFT]** goes back. PERFORM has its own
knobs, shown in the header as on the OS's own pages: the cutoff with **(A)**, RESO with **(B)**. No other knob does
anything on PERFORM, so nothing there changes the JOG page.

* **A = the DJ filter.** Left of centre is LP2, closing as you turn; right of centre is HP2, opening; the centre
  is THRU.
  * A turn that crosses the centre stops at THRU; the next detent goes on to the other side.
  * Each side ends with a hard stop: turning on past the end does nothing.
  * A slow turn takes about 96 detents from the centre to the end of one side. A fast turn moves twice as far per
    detent; one move of the knob counts 4 detents at most, however fast it is spun.
* **B = RESO**, a step a detent. Above about 90 it climbs past the stock maximum into self-oscillation (Polivoks
  style). Keep the volume down the first time.
* **Push A:** snaps to THRU. **[FUNC] + push A:** filter off.

### Why it sweeps like an analog knob

* The cutoff is a 16-bit value, 256 times finer than the FX filter's knob steps; the analog cutoff takes all 16
  bits.
* It glides to where you turned it (about 21 ms), and then glides again in the filter itself.
* Crossing to the other side starts that side at its open end, so there is no jump.

### The screen

* **Top line:** the type, the cutoff in Hz and RES.
* **The graph:** 20 Hz to 20 kHz, with dotted lines at 100 Hz, 1 kHz and 10 kHz and at 0 dB.
  * **The solid line is the filter's curve.** It is drawn from the 2-pole shape at the cutoff and RESO: an
    illustration, not a measurement of the analog circuit. The Hz scale comes from cutoffs measured on one
    Syntakt; other units can be a few percent off.
  * **The bars are the mix's real spectrum after the filter:** the OS's digital copy of the main mix (the one sent
    to Overbridge), so you see the bass drop away as you close the low-pass. They rise at once and fall about
    20 dB a second. The scale is fixed and tilted +3 dB an octave around 1 kHz, the way analyzers show a mix.
* **Bottom:** the knob position (LP / centre / HP).

The spectrum only runs while PERFORM is on screen; no other page pays for it.

### Which filter is it?

* **In a build with the FX-page master filter** (a full MAX set that has it): PERFORM drives that filter. Its FX
  SYN page 2 keeps working. Turning its FREQ there (or by MIDI) takes the filter back from PERFORM.
* **Otherwise, this repository's builds:** **perf-filter**, the same audio with no page, no parameters and no MIDI.

Either way, the filter is the analog FX block over the whole mix: tracks 1–12, the delay and reverb returns, and
the input. While it's on:

* routing that takes something off the main mix is kept;
* the FX track's DRIVE and **FX AMP page apply to the whole mix**, as with the master filter. In the default
  inverted (ducking) AMP mode, FX-track trigs duck everything. In AHD or ADSR mode the mix only sounds on FX trigs;
* levels stay level: the FX path is flat from DRIVE 0 to 64.

A build without either filter shows `NO MASTER FILTER` and B does nothing.

## LINK (shelved)

The LiveLink CDJ bridge is shelved (its source is not in the public copy) for now. The JOG page is built without LINK, so the
Syntakt's MIDI inputs are not hooked and stay stock. The LINK code is still in `tj.c` (`#ifndef NOLINK`), but it no
longer fits its chunks with TEST35's additions. Bringing it back means making room first.

## Check list for your first flash

1. Hold [TEMPO]: JOG opens. Play a pattern: the marker passes 12 o'clock on the one.
2. B, C, D, E, F: LOAD, START, BRAKE, RANGE, PHASE, each a step every 2–3 detents (RANGE 6), nothing skipping. G
   and H do nothing.
3. LOAD 1 against LOAD 8: spin A and let go. Light snaps back, heavy coasts, and neither crawls at the end.
4. PERSONALIZE > JOG DISPLAY = CDJ: the outer rings stand still until you spin A, and a push of A brakes, as in
   VINYL.
5. Spin A both ways: tempo and pitch bend together; [YES]: tempo only.
6. [FUNC] + [TRIG 2] from 130: a 4-bar glide landing on 140.00.
7. [RIGHT]: PERFORM. Turn A slowly both ways: no steps, a stop at THRU, a hard stop at each end. Turn B (RESO).
   Push A; [FUNC] + push A. Turn C–H: nothing happens, and back on JOG ([LEFT]) nothing has changed.
8. Play while on PERFORM: the bars move, and closing the low-pass drops the highs. Does the screen keep up? Are the
   other pages as smooth as before?
9. If the unit stops on an exception screen starting `57AC` (the tripwire), photograph the whole screen.
