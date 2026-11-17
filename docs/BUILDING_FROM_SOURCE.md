# Building from source and running the tests

Needed once: **your** official OS files (never committed), the firmware container tool, Python 3 with `unicorn`
and `pytest`, and, only to recompile the C, an m68k cross toolchain.

## 1. The stock files

Download Syntakt OS 1.41 and/or 1.42 from elektron.se. Put them in `os141/firmware/Syntakt_OS1.41.syx` and
`os142/firmware/Syntakt_OS1.42.syx` (the expected SHA-256 is in each `firmware/README.md`). They are git-ignored.

## 2. The container tool

`elektron-firmware-tool` (Marcel Bierling / mischa85, MIT). On Linux or WSL: `bash os141/tools/unpack/setup_eft.sh`
clones and builds it at a pinned commit into `third_party/` (git-ignored). On Windows you can instead copy the
`elektron-firmware-tool.exe` that ships in the MAX 1.0 builder's `resources/` folder into `builder/resources/`.
Point `EFT_BIN` at the binary if it is somewhere else.

## 3. Unpack, test

```
cd os141
python tools/unpack/unpack_stock.py            # writes unpacked/ (git-ignored: it IS firmware)
python -m pytest -q                            # JOG, round 3, Performance Mods, perf-filter, builder, tripwire (+ add-on tests with MAX_MANIFEST)
```

Same in `os142`. The tests run the real compiled code in a 68k emulator (`unicorn`) on your stock image. The
add-on tests are described in [COMBINING_WITH_MAX.md](COMBINING_WITH_MAX.md).

## 4. Recompile the jog and perf-filter

`os141/mods/tempojog/make_patch.py` compiles `tj.c` (its main, drawing and pitch/tools chunks) and
`os141/mods/perf-filter/make_patch.py` compiles `pf.c`, with `m68k-linux-gnu-gcc-13`, into their `patch.json`. On Debian/Ubuntu: `apt install gcc-13-m68k-linux-gnu
binutils-m68k-linux-gnu`, then:

```
cd os141
EFT_BIN=... M68K_ROOT=/ python mods/tempojog/make_patch.py 1.41
EFT_BIN=... M68K_ROOT=/ python mods/perf-filter/make_patch.py 1.41
EFT_BIN=... M68K_ROOT=/ python mods/tripwire/make_patch.py 1.41
```

The jog is built with `-DNOLINK` (LINK is shelved: LINK's "no bridge" state becomes constants, so the LINK code and
the MIDI input hooks drop out). `--link` would build the LINK version, which no longer fits its chunks since TEST35.

(`M68K_ROOT` is the prefix whose `usr/bin` holds the cross tools; `/` for the distro packages.) The patch is
byte-for-byte reproducible: rebuilding on the toolchain above gives the `patch.json` files in this repository
(checked for both OSes). Then put the new patch in the builder's catalog:

```
python tools/catalog/refresh_catalog.py            # --check exits 1 if the catalog is out of date
```

## 5. Run the builder

`python builder/app.py` opens the GUI. From Python: `import max_custom as M; M.build(stock, out, {"perfmods"})`
(run it with `builder/` on `sys.path`; `EFT_BIN` set if the tool is not in `builder/resources/`).
