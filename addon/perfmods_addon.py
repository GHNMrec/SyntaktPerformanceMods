"""Add Syntakt Performance Mods (the JOG page + PERFORM's filter) to somebody else's MAX build.

    python addon/perfmods_addon.py --manifest max-1.0-manifest.json --stock Syntakt_OS1.41.syx --out my_max_perf.syx
    python addon/perfmods_addon.py --manifest max-1.0-manifest.json --stock Syntakt_OS1.41.syx --verify-base

It reads a MAX manifest (format 1: the mod list MAX's own builder uses), puts the Performance Mods next to the mods
that are already in it, runs every guard the MAX builder has (stock hash, patch-by-patch stock checks, no two patches
on one byte, boot margin) and writes ONE new .syx from the OFFICIAL Syntakt OS file you already own. It never
reads, writes or sends a .syx anyone else built, and it never talks to the unit.

What it changes in the MAX mod list, and nothing else:
  1. modarea: MAX 1.0's mod area is 64 KB (0xFFF0). The jog's code sits above it, so the area is made 128 KB
     (0x1FFF0), the size the full MAX test builds use. The loader holds that size three times; the script changes
     exactly those three constants in the MAX loader and checks the result equals ours byte for byte, else refuses.
  2. the JOG page (tempojog-nolink: no LINK) is added, and perf-filter, PERFORM's own filter (the analog FX block over
     the whole mix; no page, no MIDI, nothing on the FX track's pages); a build that already has master-filter keeps
     that one and PERFORM drives it instead. With --tripwire the crash tripwire as well.
It refuses (and says which mods) when the jog's patches land on bytes another mod already patches, when the
mod area overflows, or when the build's boot margin is unsafe.

--verify-base builds the manifest alone through this builder's core and compares the result with the manifest's
own golden hash: proof that this builder reproduces that MAX byte for byte before anything is added."""
from __future__ import annotations
import argparse, copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "builder"))
import max_custom as M  # noqa: E402

JOG, PF = "tempojog-nolink", "perf-filter"                       # TEST35a: LINK is shelved
OURS = (JOG, PF, "tempojog")


def int_of(x):
    return int(x, 16) if isinstance(x, str) else x


def area_map(mods, layout):
    """(offset in the area, end, mod) of every appended chunk, sorted"""
    img = int_of(layout["img"])
    out = []
    for m in mods:
        for p in m["patches"]:
            if p["section"] == 3 and p.get("append"):
                a = int_of(p["addr"]) - img
                out.append((a, a + p["len"], m["name"]))
    return sorted(out)


def swap_modarea(mods, ours):
    """replace the manifest's modarea by ours if (and only if) they differ in the size constant alone"""
    theirs = next((m for m in mods if m["name"] == "modarea"), None)
    if theirs is None:
        raise M.BuildError("the manifest has no modarea mod, so there is no mod area to put the jog in")
    for k in ("img", "ram", "heap_block", "compress"):
        if theirs["layout"][k] != ours["layout"][k]:
            raise M.BuildError(f"modarea layout differs in {k} ({theirs['layout'][k]} vs {ours['layout'][k]}): "
                               "this is not the area the jog was built for")
    if theirs["symbols"] != ours["symbols"]:
        raise M.BuildError("modarea symbols differ: not the area the jog was built for")
    if int_of(theirs["layout"]["size"]) >= int_of(ours["layout"]["size"]):
        return "already large enough (0x%X)" % int_of(theirs["layout"]["size"])
    a, b = theirs["patches"], ours["patches"]
    if [(p["addr"].upper(), p["len"]) for p in a] != [(p["addr"].upper(), p["len"]) for p in b]:
        raise M.BuildError("modarea patches are laid out differently")
    # the loader holds the area's size three times: RAM+SIZE (twice, 'clear the rest of the area') and the heap
    # block size (once, 'the first request'). Make exactly those three changes to their loader and compare the
    # result with ours byte for byte: anything else that differs is refused.
    ram, so, sn = int_of(theirs["layout"]["ram"]), int_of(theirs["layout"]["size"]), int_of(ours["layout"]["size"])
    swaps = [((ram + so).to_bytes(4, "big"), (ram + sn).to_bytes(4, "big"), 2),
             ((so + 0x10).to_bytes(4, "big"), (sn + 0x10).to_bytes(4, "big"), 1)]
    patched = copy.deepcopy(theirs)
    data = bytearray.fromhex(patched["patches"][0]["hex"])
    for old, new, n in swaps:
        at = [i for i in range(len(data) - 3) if data[i:i + 4] == old]
        if len(at) != n:
            raise M.BuildError(f"expected {n} x {old.hex()} in the area loader, found {len(at)}")
        for i in at:
            data[i:i + 4] = new
    patched["patches"][0]["hex"] = data.hex()
    if any(x["hex"] != y["hex"] for x, y in zip(patched["patches"], ours["patches"])):
        raise M.BuildError("modarea loaders differ in more than the area size")
    theirs["patches"] = patched["patches"]
    theirs["layout"] = copy.deepcopy(ours["layout"])
    theirs["description"] = (theirs.get("description", "") + " [area made 128 KB for the jog]").strip()
    return "64 KB -> 128 KB (the loader's three size constants only)"


def merge(manifest, cat, tripwire=False, notes=print):
    osv = manifest["os"]
    if osv not in cat["oses"]:
        raise M.BuildError(f"this add-on has the jog for OS {' / '.join(cat['oses'])}, the manifest is OS {osv}")
    o = cat["oses"][osv]
    mods = copy.deepcopy(manifest["mods"])
    names = {m["name"] for m in mods}
    want = ([] if "master-filter" in names else [PF]) + [JOG] + (["tripwire"] if tripwire else [])
    for n in OURS + (("tripwire",) if tripwire else ()):
        if n in names:
            raise M.BuildError(f"the manifest already has a mod called {n}")
    if "master-filter" in names:
        notes("master-filter is in this build: PERFORM drives it (perf-filter not added)")
    notes("modarea: " + swap_modarea(mods, o["mods"]["modarea"]))
    layout = next(m["layout"] for m in mods if m["name"] == "modarea")
    before = area_map(mods, layout)
    top = max((b for _, b, _ in before), default=0)
    for n in want:
        m = copy.deepcopy(o["mods"][n])
        for r in m.get("requires", []):
            if r not in names | set(want):
                raise M.BuildError(f"{n} needs {r}")
        mods.append(m)
    present = {m["name"] for m in mods}
    for i, m in enumerate(mods):                                  # the jog's link to a master filter, if there is one
        if m["name"] in o.get("compat", {}):
            mods[i] = M._with_compat(m, o["compat"][m["name"]], present)
            if present & {r["when"] for r in o["compat"][m["name"]]}:
                notes(f"{m['name']}: PERFORM linked to " + " / ".join(sorted(present & {r["when"] for r in o["compat"][m["name"]]})))
    after = area_map(mods, layout)
    size = int_of(layout["size"])
    jog_lo = min(a for a, _, n in after if n in want)
    if jog_lo < top:
        raise M.BuildError(f"the jog's chunks start at +{jog_lo:#x}, inside the other mods' area (+{top:#x})")
    notes(f"mod area: other mods end at +{top:#x}; the jog's chunks run +{jog_lo:#x}..+{max(b for _, b, _ in after):#x} "
          f"of +{size:#x}")
    return osv, mods


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest", required=True, help="a MAX manifest (format 1), e.g. max-1.0-manifest.json")
    ap.add_argument("--stock", required=True, help="the OFFICIAL Syntakt OS .syx for the manifest's OS")
    ap.add_argument("--out", help="where to write the new .syx (must not exist)")
    ap.add_argument("--tripwire", action="store_true", help="also add the crash tripwire (diagnostic)")
    ap.add_argument("--nolink", action="store_true", help=argparse.SUPPRESS)   # TEST34b's flag: LINK is shelved now
    ap.add_argument("--dry-run", action="store_true", help="merge and run every check except writing the file")
    ap.add_argument("--verify-base", action="store_true",
                    help="build the manifest alone and compare it with its golden hash")
    ap.add_argument("--write-manifest", help="also write the merged manifest here, to read")
    a = ap.parse_args(argv)
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    if manifest.get("format") != 1:
        sys.exit("only MAX manifests of format 1 are understood")
    if M.digest_path(a.stock) != manifest["stock_sha256"]:
        sys.exit("--stock is not the official OS file this manifest was made for (SHA-256 differs)")
    cat = M.catalog()
    try:
        if a.verify_base:
            out = Path(a.out or Path(a.stock).with_name("base_check.syx"))
            got, margin = M.assemble(a.stock, out, copy.deepcopy(manifest["mods"]), manifest["os"], print)
            out.unlink()
            ok = got == manifest.get("golden_sha256")
            print(f"base build {got[:16]}..., golden {str(manifest.get('golden_sha256'))[:16]}...: "
                  + ("IDENTICAL" if ok else "DIFFERENT"))
            return 0 if ok else 1
        osv, mods = merge(manifest, cat, a.tripwire)
        if a.write_manifest:
            merged = dict(manifest, mods=mods, name=manifest.get("name", "MAX") + " + Performance Mods")
            merged.pop("golden_sha256", None)
            Path(a.write_manifest).write_text(json.dumps(merged, indent=1), encoding="utf-8")
        if a.dry_run or not a.out:
            sections = {3: bytearray(), 7: bytearray()}                 # apply() needs the stock sections for its guards
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                files = M.unpack(a.stock, Path(td), [3, 7])
                sections = {k: bytearray(v.read_bytes()) for k, v in files.items()}
                M.apply(sections, mods, osv)
            print("dry run OK: every patch guard passes, no byte is patched twice, the mod area fits.")
            return 0
        got, margin = M.assemble(a.stock, a.out, mods, osv, print)
        print(f"wrote {a.out}\nsha256 {got}\nboot margin {margin} bytes (the builder refuses below {M.MIN_MARGIN})")
        print("Checked here: the patches, the guards, the boot margin. NOT checked: on a unit. Back up first.")
        return 0
    except M.BuildError as e:
        print("REFUSED: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
