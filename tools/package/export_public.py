"""Export the PUBLIC copy of this repository: only what is listed as shared, scrubbed, checked for firmware.

    python tools/package/export_public.py <empty-or-new folder>

* What goes public is decided by tools/package/share.json (paths and globs). Anything not listed stays private.
* Every file passes the pre-commit hook's firmware check, and the export refuses if one doesn't.
* tools/package/private_words.json (never exported) lists personal words: "scrub" replaces them in the public copy
  only, and any "refuse" word left anywhere in the result stops the export.
* No git history is copied: the public repo gets its own history.
* share.json also says what is private only (private_only: never copied), which catalog entries the public list drops
  (public_catalog_drop), the text edits that keep the public docs in step (public_edits), and the lines about a
  private-only mod that are dropped from the public docs (public_line_drop). After the export the install zip is
  built from the exported files, so it matches the public copy.
"""
from __future__ import annotations
import fnmatch, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "hooks"))
from check_no_firmware import check_blob  # noqa: E402

PRIVATE = ROOT / "tools/package/private_words.json"   # never exported: {"scrub": [[regex, replacement]], "refuse": [...]}
TEXT_EXT = {".py", ".md", ".json", ".c", ".h", ".S", ".txt", ".bat", ".sh", ".ini", ".cpp", ".ino", ".lst", ".yml",
            ".html", ".js", ".css", ".gitignore", ""}


def catalog_public(data: bytes, drop: set) -> bytes:
    """the public mod list: the groups, mods, order, variants and known builds named in `drop` are removed"""
    cat = json.loads(data.decode("utf-8"))
    cat["groups"] = [g for g in cat["groups"] if g["id"] not in drop]
    if "presets" in cat:                             # a preset that needs a dropped group goes too
        cat["presets"] = [p for p in cat["presets"] if not any(g in drop for g in p.get("groups", []))]
    for o in cat["oses"].values():
        o["mods"] = {k: v for k, v in o["mods"].items() if k not in drop}
        o["order"] = [k for k in o.get("order", []) if k not in drop]
        if "variants" in o:
            o["variants"] = {k: v for k, v in o["variants"].items() if k not in drop}
        o["known"] = [k for k in o.get("known", []) if not any(d in k["name"].lower() for d in drop)]
    return json.dumps(cat, indent=1, ensure_ascii=False).encode("utf-8")


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p.decode() for p in out.split(b"\0") if p]


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    dest = Path(argv[0])
    if dest.exists() and any(p.name != ".git" for p in dest.iterdir()):
        sys.exit(f"{dest} is not empty (only a .git folder may be there)")
    share = json.loads((ROOT / "tools/package/share.json").read_text(encoding="utf-8"))
    files = [p for p in tracked() if any(fnmatch.fnmatch(p, g) for g in share["include"])
             and not any(fnmatch.fnmatch(p, g) for g in share.get("exclude", []) + share.get("private_only", []))]
    edits = [(re.compile(rx), rep) for rx, rep in share.get("public_edits", [])]
    line_drop = re.compile(share.get("public_line_drop", "(?!)"), re.M)
    catalog_drop = set(share.get("public_catalog_drop", []))
    words = json.loads(PRIVATE.read_text(encoding="utf-8"))
    SCRUB = [(re.compile(rx), rep) for rx, rep in words["scrub"]]
    REFUSE_WORDS = [w.lower() for w in words["refuse"]]
    files = [p for p in files if p != "tools/package/private_words.json"]
    problems = []
    for p in files:
        data = (ROOT / p).read_bytes()
        if p == "builder/resources/catalog.json" and catalog_drop:
            data = catalog_public(data, catalog_drop)
        if (ROOT / p).suffix in TEXT_EXT or p.endswith(".gitignore"):
            text = data.decode("utf-8")
            for rx, rep in edits:
                text = rx.sub(rep, text)
            if (ROOT / p).suffix in (".md", ".txt"):
                text = line_drop.sub("", text)
            for rx, rep in SCRUB:
                text = rx.sub(rep, text)
            data = text.encode("utf-8")
            low = text.lower()
            problems += [(p, f"contains '{w}'") for w in REFUSE_WORDS if w in low]
        if r := check_blob(p, data):
            problems.append((p, r))
        out = dest / p
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    if problems:
        shutil.rmtree(dest, ignore_errors=True)
        sys.exit("REFUSED:\n" + "\n".join(f"  {p}: {r}" for p, r in problems))
    print(f"exported {len(files)} files to {dest}")
    import importlib.util                            # the install zip, from the exported files
    spec = importlib.util.spec_from_file_location("mrz", ROOT / "tools/package/make_release_zip.py")
    mrz = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mrz)
    mrz.main(["--root", str(dest), "--out", str(dest / "release")])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
