"""Copy the jog's (no LINK), perf-filter's and the tripwire's patches (the ones make_patch.py rebuilt from the C source in os141/ and
os142/) into builder/resources/catalog.json, and check the filter link records still land on them.

    python tools/catalog/refresh_catalog.py          # write
    python tools/catalog/refresh_catalog.py --check  # exit 1 if the catalog differs from the patch.json files"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "builder" / "resources" / "catalog.json"
cat = json.loads(CAT.read_text(encoding="utf-8"))
dirty = False
for osv, tree in (("1.41", "os141"), ("1.42", "os142")):
    o = cat["oses"][osv]
    for name, src in (("tempojog-nolink", "tempojog/patch.json"), ("perf-filter", "perf-filter/patch.json"),
                      ("tripwire", "tripwire/patch.json")):
        if not (ROOT / tree / "mods" / src).exists():      # the public copy has no tripwire source
            continue
        fresh = json.loads((ROOT / tree / "mods" / src).read_text(encoding="utf-8"))
        if fresh.get("os") != osv:
            sys.exit(f"{tree}/mods/{name}/patch.json is for OS {fresh.get('os')}, not {osv}")
        if o["mods"][name] != fresh:
            dirty = True
            o["mods"][name] = fresh
            print(f"OS {osv}: {name} updated")
    for jog in ("tempojog-nolink",):                         # the filter links must still match
        for rec in o["compat"][jog]:
            m = json.loads((ROOT / tree / "mods" / rec["when"] / "patch.json").read_text(encoding="utf-8"))
            sym = "mf_p" if rec["when"] == "master-filter" else "pf_p"
            if rec["new"] != f"{int(m['symbols'][sym], 16):08x}":
                sys.exit(f"OS {osv}: the {rec['when']} link no longer points at its {sym}")
            p = next(p for p in o["mods"][jog]["patches"] if p["addr"] == rec["patch"])
            k = 2 * rec["offset"]
            want = int(o["mods"][jog]["symbols"]["tj_mfp"], 16) - int(p["ram"], 16)
            if rec["offset"] != want and p["hex"][2 * want:2 * want + len(rec["old"])] == rec["old"]:
                rec["offset"], k, dirty = want, 2 * want, True     # the code grew: tj_mfp moved, the record follows
                print(f"OS {osv}: the {rec['when']} link follows tj_mfp to offset {want}")
            if p["hex"][k:k + len(rec["old"])] != rec["old"] or rec["offset"] != want:
                sys.exit(f"OS {osv}: a filter compat record no longer matches {jog}'s patch")
if "--check" in sys.argv:
    sys.exit(1 if dirty else 0)
if dirty:
    CAT.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
else:
    print("catalog already matches os141/ and os142/")
