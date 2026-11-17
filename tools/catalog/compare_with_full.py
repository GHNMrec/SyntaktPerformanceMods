"""Prove the trimmed builder builds byte-for-byte what the full MAX custom builder builds for the same selection.

    EFT_BIN=... python tools/catalog/compare_with_full.py FULL_INSTALLER_DIR os141/firmware/Syntakt_OS1.41.syx [--all]

FULL_INSTALLER_DIR is the full builder's folder (the one with max_custom.py and resources/catalog.json). By default
the selection with every optional group; --all tries all 4 combinations of Performance Mods / Tripwire.
Slow (a build is a minute or two); it is a check you run when the catalog changes, not part of the tests."""
import itertools, os, sys, tempfile, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]


def load(path):
    for m in ("max_custom", "lz"):
        sys.modules.pop(m, None)
    sys.path.insert(0, str(path))
    import max_custom as M
    sys.path.pop(0)
    return M


full_dir, stock = Path(sys.argv[1]), Path(sys.argv[2])
full, trim = load(full_dir), load(HERE / "builder")
if os.environ.get("EFT_BIN"):                      # the full core finds its tool in its own resources folder
    full.eft = lambda: Path(os.environ["EFT_BIN"])
opts = ["perfmods", "tripwire"]
combos = list(itertools.product((0, 1), repeat=2)) if "--all" in sys.argv else [(1, 1)]
bad = 0
for bits in combos:
    g = {o for o, b in zip(opts, bits) if b}
    d = Path(tempfile.mkdtemp())
    a, b = full.build(stock, d / "a.syx", set(g)), trim.build(stock, d / "b.syx", set(g))
    same = a["sha256"] == b["sha256"]
    bad += not same
    print(sorted(g), "IDENTICAL" if same else "DIFFERENT", b["sha256"][:16], "margin", b["boot_margin"], flush=True)
    shutil.rmtree(d)
sys.exit(1 if bad else 0)
