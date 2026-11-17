# Combining the Performance Mods with someone else's MAX

**Goal:** a friend who already runs Syntakt MAX adds the Performance Mods (the JOG page and PERFORM's filter) to *his own* build, from *his own* official OS file.
Nothing built by anyone else changes hands: the add-on edits a **mod list** (a JSON manifest), never a `.syx`.

## How MAX builds, and where the Performance Mods plug in

A MAX build is: the official OS section 3 plus a list of *guarded patches* (each in-place patch names the SHA-256
of the stock bytes it replaces; appended chunks live in a compressed **mod area** that the OS's own area loader
unpacks into the first heap block at boot). MAX 1.0 publishes that list as `max-1.0-manifest.json`. The add-on
adds two mods to that list, the JOG page (`tempojog-nolink`) and PERFORM's filter (`perf-filter`), links PERFORM to
that filter, and rebuilds with the same guards. If the manifest already has a mod named `master-filter`, perf-filter is
left out and PERFORM drives that one.

Two things have to be true for that to work, and the add-on checks both:

1. **Bytes.** No two patches may touch the same byte. The jog patches 8 sites in the OS (the tempo read in the
   audio interrupt, the TEMPO view's entry and its vtable slots, the PERSONALIZE menu's constructor call and the
   copy hook; no MIDI input hooks: LINK is shelved) and appends three code chunks; perf-filter patches one site (the
   audio interrupt's call of the FX filter CV routine, `0x400A4F24`) and appends one chunk. Nothing goes on the FX
   track's pages, nothing on MIDI. If any of those lands on a byte another mod patches,
   the build is refused and names the mods.
2. **Space.** MAX 1.0's mod area is 64 KB (`0xFFF0`); its mods end at +`0xD6B2`. Our chunks sit at
   +`0x15100` .. +`0x1FCC6` (perf-filter at +`0x15100`, the jog from +`0x1B480`), above it, so the area is made **128 KB** (`0x1FFF0`). The area's RAM start and its image
   address do not move, so every MAX mod's absolute addresses stay valid. The 128 KB area is what the full MAX test
   builds use; the heap block simply takes 64 KB more. The add-on changes exactly three constants in the area loader
   (`RAM+SIZE` twice, the heap block size once) and checks the result equals this repository's 128 KB loader byte
   for byte; any other difference and it refuses.

## Use

```
python addon/perfmods_addon.py --manifest max-1.0-manifest.json --stock Syntakt_OS1.41.syx --verify-base
python addon/perfmods_addon.py --manifest max-1.0-manifest.json --stock Syntakt_OS1.41.syx --dry-run
python addon/perfmods_addon.py --manifest max-1.0-manifest.json --stock Syntakt_OS1.41.syx --out my_max_perf.syx
```

* `--verify-base` builds the manifest **alone** through this repository's builder and compares it with the
  manifest's golden hash. Do this first: it proves the builder reproduces your MAX byte for byte (for the public
  MAX 1.0 it prints `IDENTICAL`).
* `--dry-run` merges and runs every check without writing a file. `--write-manifest merged.json` also saves the
  merged list so you can read exactly what changed. `--tripwire` adds the crash tripwire too.
* `--stock` must be the official file the manifest names (its SHA-256 is checked).
* It needs `elektron-firmware-tool` (see [BUILDING_FROM_SOURCE.md](BUILDING_FROM_SOURCE.md) or copy the `.exe` from
  MAX's own builder `resources/` folder; point `EFT_BIN` at it or put it in `builder/resources/`).

## What happens when something collides

`REFUSED: ...` with the reason and, for a byte clash, the two mod names. Typical causes: the manifest already has a
mod named `tempojog`, `tempojog-nolink` or `perf-filter`; another mod patches the same OS site (a different master
filter on `0x400A4F24`, say); a mod's chunks start inside our range; the area
overflows; the boot margin is under 4096 bytes. Nothing is written when it refuses.

## What was verified (public MAX 1.0, OS 1.41)

* This builder reproduces MAX 1.0's golden SHA-256 (`7cb4bfd3...`) exactly.
* MAX 1.0 + Performance Mods (TEST36 code): every patch guard passes, no byte is patched twice, boot margin 16,973
  bytes; PERFORM is linked to perf-filter; nothing in MAX 1.0 hooks the FX filter CV call.
* In the emulator, section 3 of that build goes through the OS's own area loader: every chunk of every MAX mod and
  of ours ends up at its RAM address, the rest of the 128 KB area is zero and the BSS around it is cleared
  (`os141/tests/test_addon.py`, set `MAX_MANIFEST`).
* On the final merged image (booted through the area loader, as on the unit): the JOG, round-3 and Performance Mods
  tests pass, a sine lands in its own spectrum column, and in the real audio interrupt PERFORM's cutoff glides
  smoothly into the FX filter (the add-on's merged manifest: `--write-manifest`).

## What is NOT verified

* **On a unit.** Neither the merged build nor the stand-alone one has run on hardware in this exact combination.
* **Mods that are not in MAX 1.0.** A later MAX manifest may add mods that patch the same OS sites or use bytes in
  the area above +`0x15100`. The add-on catches byte clashes and range clashes, but not two mods that hook the same
  *function* at different bytes in incompatible ways: only the emulator or the unit would show that. Run
  `--dry-run`, read the merged manifest, run the tests with `JOG_MERGED_MANIFEST`.
* **Runtime RAM.** The area is zero after boot except the image. The jog's state lives inside its own chunks. The
  add-on found no symbol of a MAX 1.0 mod pointing into the area outside that mod's own chunks; a mod that
  allocates scratch RAM in the area beyond its image would need a manual check.
* **OS 1.42.** MAX 1.0 is OS 1.41 only; the add-on works from the manifest's OS, and the jog exists for both.
* **Another master filter.** perf-filter takes over the FX block like the FX-page master filter does: the FX track's
  DRIVE and AMP page apply to the whole mix while it is on (see the user guide). A MAX mod that also drives the FX
  block's filter from a different hook would fight it; the add-on can't see that.
