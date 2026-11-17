# Syntakt Performance Mods

Performance mods for the Elektron Syntakt (OS 1.41 and 1.42).

* **JOG page:** hold **[TEMPO]** and the Syntakt gets a CDJ / vinyl jog:
  * a platter that turns once a bar;
  * a jog you nudge and brake like a CDJ or a record, with a weight (LOAD) from light to heavy;
  * pitch that follows the nudge;
  * a phrase counter;
  * tempo memories with an exact glide.
* **PERFORM page** (**[RIGHT]** from JOG): a DJ filter on the analog FX block over the whole mix. It sweeps smoothly
  like an analog knob (THRU is a true bypass), with RESO on B and a DRV knob on C, and the screen draws the filter's
  curve over the mix's live spectrum.

Everything is in [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

> **Status: EXPERIMENTAL.** Every part is checked in an emulator (see [docs/STATUS.md](docs/STATUS.md)), but the
> TEST36 changes have not run on a real unit yet. Before you flash anything:
> * back up your projects and samples;
> * keep a known-good official `.syx` at hand for recovery mode.

## No firmware here, ever

You need **the official Syntakt OS file from elektron.se**, the one you download yourself. This repository contains
no firmware.

* The builder never sends anything to a unit.
* It reads your official file and recognises it by its SHA-256.
* It writes a **new `.syx` on your own disk**, which you then flash the usual way.
* Nobody sends a built `.syx` to anyone else: each person builds their own from their own copy.

See [LEGAL.md](LEGAL.md).

## Build it in your browser (no install)

**https://ghnmrec.github.io/SyntaktPerformanceMods/**

* Drop your official OS file, tick the mods, then build. Building takes about half a minute.
* Save the `.syx` and send it with Elektron Transfer.
* Everything runs in your browser tab. Your OS file is never uploaded, and the site hosts no firmware.
* The page is in `web/`; `tools/web/build_site.sh` assembles it, and `.github/workflows/pages.yml` publishes it.
* It's the same builder as the desktop app, ported to JavaScript. The firmware tool is compiled to WebAssembly from
  its public source. The tests checked that both builders give the same file, byte for byte, for every selection on
  OS 1.41 and 1.42, and for the MAX 1.0 add-on.

## Install


**Read [START HERE.txt](<START HERE.txt>).** It covers both ways to install, with a double-click launcher for each:

* **Option A** (`Option A - Build Performance Mods.bat`): stock OS + Performance Mods.
* **Option B** (`Option B - Add to my MAX build.bat`): add them to the Syntakt MAX you already run. It asks for your
  MAX manifest and your OS file, proves your MAX rebuilds byte for byte, checks the merge, then writes the file.

The same thing as one download: `release/SyntaktPerformanceMods-<version>.zip` (made by
`tools/package/make_release_zip.py`: the builder, the add-on, the launchers, the docs and the licences; no firmware,
no source trees).

## Three ways to use it

### 1. Standalone (the builder)

A small Windows app (or any Python 3 + Tk). Pick your OS file, tick what you want, then build.

```
builder/Start Syntakt Performance Mods builder.bat        (or: python builder/app.py)
```

Groups:

* **Core:** always on. The mod area, the splash, the parameter hooks, the MIDI id guard and Workbench's SY CHORD
  bank.
* **Syntakt Performance Mods:** the JOG page and PERFORM's own filter (*perf-filter*).

One-time setup: put `elektron-firmware-tool.exe` in `builder/resources/` (details in
[builder/README.txt](builder/README.txt)).

### 2. Added to somebody's MAX build

Your buddy already runs Syntakt MAX (the public 1.0, or a later manifest)? `addon/perfmods_addon.py` does this:

* reads *his* MAX mod list;
* adds the Performance Mods next to his mods;
* builds one new `.syx` from *his* official OS file;
* makes the mod area 128 KB (our code sits above MAX 1.0's 64 KB).

Nothing goes on his FX track's pages. Read [docs/COMBINING_WITH_MAX.md](docs/COMBINING_WITH_MAX.md) first.

```
python addon/perfmods_addon.py --manifest max-1.0-manifest.json --stock Syntakt_OS1.41.syx --verify-base
python addon/perfmods_addon.py --manifest max-1.0-manifest.json --stock Syntakt_OS1.41.syx --out my_max_perf.syx
```

### 3. From source

The mods are C, compiled with an m68k cross compiler into the guarded patches the builder uses:

* `os*/mods/tempojog/tj.c`: the JOG and PERFORM pages;
* `os*/mods/perf-filter/pf.c`: the filter.

The emulator tests run the real code against your stock image. See
[docs/BUILDING_FROM_SOURCE.md](docs/BUILDING_FROM_SOURCE.md).

## Layout

| Path | What |
|---|---|
| `builder/` | the offline builder (GUI + core) and its small catalog: core, Performance Mods; OS 1.41 and 1.42 |
| `addon/` | `perfmods_addon.py`: merge the Performance Mods into another MAX manifest |
| `os141/`, `os142/` | the per-OS source trees: `mods/` (tempojog, perf-filter and the core mods), `tests/`, `tools/` (emulator, unpacker, area layout) |
| `livelink/` | the LiveLink CDJ bridge: **shelved**, and not in the public copy. The jog is built without LINK |
| `tools/catalog/` | `refresh_catalog.py` puts the rebuilt patches into the catalog; `make_trim_catalog.py` made the catalog |
| `tools/hooks/` | the pre-commit hook that refuses firmware |
| `docs/` | user guide, combining, building, status |

`os*/mods/master-filter/` is the FX-page master filter's source. It is not offered here. It stays because:

* the core's build scripts read its parameter ids;
* the tests check that perf-filter sounds exactly like it.

## What is not here

The other MAX mods (arp, grid, FM4, Sidtakt, compressor, the FX-page master filter, ...). This repository is only
the Performance Mods and what they need to run, so it can live apart from them. It stays combinable: that is what
the add-on is for.
