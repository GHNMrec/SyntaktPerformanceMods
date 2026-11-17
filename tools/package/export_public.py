"""Export the PUBLIC copy of this repository: only what is listed as shared, scrubbed, checked for firmware.

    python tools/package/export_public.py <empty-or-new folder>

* What goes public is decided by tools/package/share.json (paths and globs). Anything not listed stays private.
* Every file passes the pre-commit hook's firmware check, and the export refuses if one doesn't.
* tools/package/private_words.json (never exported) lists personal words: "scrub" replaces them in the public copy
  only, and any "refuse" word left anywhere in the result stops the export.
* No git history is copied: the public repo gets its own history.
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
             and not any(fnmatch.fnmatch(p, g) for g in share.get("exclude", []))]
    words = json.loads(PRIVATE.read_text(encoding="utf-8"))
    SCRUB = [(re.compile(rx), rep) for rx, rep in words["scrub"]]
    REFUSE_WORDS = [w.lower() for w in words["refuse"]]
    files = [p for p in files if p != "tools/package/private_words.json"]
    problems = []
    for p in files:
        data = (ROOT / p).read_bytes()
        if (ROOT / p).suffix in TEXT_EXT or p.endswith(".gitignore"):
            text = data.decode("utf-8")
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
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
