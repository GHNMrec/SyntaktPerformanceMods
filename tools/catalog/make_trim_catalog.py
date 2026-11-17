"""Make builder/resources/catalog.json (the trimmed catalog) from the full MAX-mods catalog.

    python tools/catalog/make_trim_catalog.py FULL_CATALOG.json

Keeps: core (splash, modarea, midi-guard, vparams, workbench-max), Syntakt Performance Mods (the JOG page and
perf-filter, PERFORM's own filter: no page, no MIDI) and the crash tripwire, for OS 1.41 and 1.42. The FX-page
master filter is not offered here (its source stays in os14x/mods/master-filter: midi-guard's and vparams' build
scripts read its ids, and test_perfmods.py checks perf-filter against it). The "without FM4" versions of midi-guard
and vparams are baked in (this catalog has no FM4 group, so the full catalog's `fm4: False` switch would never
fire). Then run refresh_catalog.py to take the jog's, perf-filter's and the tripwire's patches from os141/ and os142/
(the ones rebuilt from the C source). Only needed when the full catalog changes."""
import json, sys
from pathlib import Path

KEEP_GROUPS = ["core", "perfmods", "tripwire"]
KEEP_MODS = {"splash", "modarea", "midi-guard", "vparams", "workbench-max", "perf-filter", "tempojog-nolink", "tripwire"}
BAKED = ("midi-guard", "vparams")

full = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cat = {k: full[k] for k in ("format", "status", "stock_block", "stock_pct")}
cat["groups"] = [dict(g) for g in full["groups"] if g["id"] in KEEP_GROUPS]
for g in cat["groups"]:
    g.pop("requires", None)
cat["oses"] = {}
for osv, o in full["oses"].items():
    n = {k: o[k] for k in ("os", "base", "stock_sha256", "status", "why") if k in o}
    n["order"] = [m for m in o["order"] if m in KEEP_MODS]
    n["mods"] = {m: o["mods"][m] for m in n["order"]}
    n["variants"] = {}
    for m in BAKED:
        v = next(v for v in o["variants"][m] if v["when"] == {"fm4": False})
        n["mods"][m] = v["mod"]
        n["variants"][m] = [{"when": {}, "mod": v["mod"], "status": v["status"],
                             "why": "Built without FM4 (this builder has no FM4): midi-guard and vparams in their no-FM4 form."}]
    n["compat"] = {"tempojog-nolink": o["compat"]["tempojog-nolink"]}   # master-filter's record too: the add-on, for
                                                                         # a MAX build that has one
    n["known"] = []
    cat["oses"][osv] = n
cat["progress"] = [{"build": "Syntakt Performance Mods 1.0 (TEST35a code)", "os": "both", "on_unit": "not yet",
                    "what": "The JOG page (B LOAD, C START, D BRAKE, E RANGE, F PHASE; LOAD = the jog's weight; VINYL / CDJ "
                            "from PERSONALIZE; phrase counter, pitch follow, brake fade, tempo memories) and PERFORM (a "
                            "smooth DJ filter on the analog FX block with its curve over the mix's spectrum). Checked in "
                            "the emulator; see docs/STATUS.md for what is not proven on a unit."}]
cat["next"] = []
cat["presets"] = [
    {"name": "Syntakt Performance Mods (OS %s)" % v, "os": v, "groups": ["perfmods"], "except": []}
    for v in cat["oses"]
] + [
    {"name": "Syntakt Performance Mods + crash tripwire (OS %s)" % v, "os": v, "groups": ["perfmods", "tripwire"],
     "except": []} for v in cat["oses"]
]
Path(__file__).resolve().parents[2].joinpath("builder", "resources", "catalog.json").write_text(
    json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
print("groups", [g["id"] for g in cat["groups"]])
