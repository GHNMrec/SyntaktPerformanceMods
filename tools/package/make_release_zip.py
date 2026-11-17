"""Make the install zip (Option A builder + Option B add-on) from the files git tracks.

    python tools/package/make_release_zip.py [--version 1.1-test35a] [--out release/]

Only what a user needs goes in: the builder, the add-on, the launchers, the docs and the licences. No source trees,
no LiveLink, no tools. Every file passes the same firmware check as the pre-commit hook, and the zip refuses to be
made if one doesn't. elektron-firmware-tool.exe is NOT included (see START HERE.txt: one-time setup).
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "hooks"))
from check_no_firmware import check_blob  # noqa: E402

INCLUDE = ("START HERE.txt", "README.md", "LEGAL.md", "THIRD_PARTY_NOTICES.md",
           "Option A - Build Performance Mods.bat", "Option B - Add to my MAX build.bat",
           "builder/", "addon/", "docs/", "licenses/")
FIXED_TIME = (2026, 11, 15, 0, 0, 0)          # same bytes every time for the same files


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p.decode() for p in out.split(b"\0") if p]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.1-test35a")
    ap.add_argument("--out", default=str(ROOT / "release"))
    a = ap.parse_args(argv)
    files = sorted(p for p in tracked() if any(p == i or (i.endswith("/") and p.startswith(i)) for i in INCLUDE))
    missing = [i for i in INCLUDE if not i.endswith("/") and i not in files]
    if missing:
        sys.exit(f"not tracked by git yet: {missing}")
    bad = [(p, r) for p in files if (r := check_blob(p, (ROOT / p).read_bytes()))]
    if bad:
        sys.exit("REFUSED, possible firmware: " + "; ".join(f"{p}: {r}" for p, r in bad))
    top = f"SyntaktPerformanceMods-{a.version}"
    dest = Path(a.out) / f"{top}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            info = zipfile.ZipInfo(f"{top}/{p}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (ROOT / p).read_bytes())
    print(f"{dest}  ({dest.stat().st_size:,} bytes, {len(files)} files)")
    for p in files:
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
