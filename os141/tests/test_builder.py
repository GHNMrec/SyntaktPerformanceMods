"""The trimmed builder (builder/): its catalog is consistent for both OSes, needs no firmware to check.
- every selection of the optional groups resolves, every mod's own needs are in the build, links resolve;
- no two patches touch one byte, in section 3 or 7;
- PERFORM links to perf-filter; no LINK build, no FX-page master filter here;
- the jog's, perf-filter's and the tripwire's catalog entries are the patch.json files rebuilt from source (refresh_catalog --check);
- presets name real groups;
- with the official files present: a build of each OS passes its guards and the boot margin (slow, skipped otherwise)."""
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOP = ROOT.parent
sys.path.insert(0, str(TOP / "builder"))
import max_custom as M  # noqa: E402

CAT = M.catalog()


@pytest.mark.parametrize("osv", ["1.41", "1.42"])
def test_every_selection_is_consistent(osv):
    opt = [g["id"] for g in M.groups_for(CAT, osv) if not g.get("locked")]
    n = 0
    for bits in itertools.product((0, 1), repeat=len(opt)):
        sel = M.resolve(CAT, {g for g, b in zip(opt, bits) if b}, osv)
        n += 1
        mods = M.mod_list(CAT, sel, osv)
        for sec in (3, 7):
            iv = sorted((int(p["addr"], 16), int(p["addr"], 16) + p["len"], m["name"])
                        for m in mods for p in m["patches"] if p["section"] == sec)
            for (a0, a1, n0), (b0, b1, n1) in zip(iv, iv[1:]):
                assert a1 <= b0, (osv, sorted(sel), n0, n1, hex(b0))
    assert n == 2 ** len(opt)


@pytest.mark.parametrize("osv", ["1.41", "1.42"])
def test_perform_is_linked_to_perf_filter(osv):
    mods = {m["name"]: m for m in M.mod_list(CAT, M.resolve(CAT, {"perfmods"}, osv), osv)}
    assert {"tempojog-nolink", "perf-filter"} <= set(mods) and "master-filter" not in mods
    tj = mods["tempojog-nolink"]
    rec = next(r for r in CAT["oses"][osv]["compat"]["tempojog-nolink"] if r["when"] == "perf-filter")
    h = next(p for p in tj["patches"] if p["addr"] == rec["patch"])["hex"]
    k = 2 * rec["offset"]
    assert h[k:k + 8] == rec["new"] == f"{int(mods['perf-filter']['symbols']['pf_p'], 16):08x}"


def test_no_link_build_offered():
    names = {m for o in CAT["oses"].values() for m in o["order"]}
    assert "tempojog" not in names and "master-filter" not in names


def test_the_catalog_has_the_rebuilt_patches():
    r = subprocess.run([sys.executable, str(TOP / "tools" / "catalog" / "refresh_catalog.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_presets_name_real_groups():
    ids = {g["id"] for g in CAT["groups"]}
    for p in CAT["presets"]:
        assert p["os"] in CAT["oses"] and set(p["groups"]) <= ids and set(p["except"]) <= ids


STOCK = ROOT / "firmware" / f"Syntakt_OS{'1.42' if ROOT.name == 'os142' else '1.41'}.syx"


@pytest.mark.skipif(not STOCK.exists() or not os.environ.get("EFT_BIN"), reason="needs the official file and EFT_BIN")
def test_a_real_build_passes_its_guards(tmp_path):
    r = M.build(STOCK, tmp_path / "o.syx", {"perfmods"})
    assert r["boot_margin"] >= M.MIN_MARGIN and {"tempojog-nolink", "perf-filter"} <= set(r["mods"])
