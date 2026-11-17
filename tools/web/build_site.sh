#!/usr/bin/env bash
# Assemble the web builder (GitHub Pages) into a folder: the page (web/), the catalog the desktop builder uses,
# and elektron-firmware-tool compiled to WebAssembly from its public source at a pinned commit.
#   bash tools/web/build_site.sh _site
# No firmware goes in: the script refuses any file that looks like an Elektron .syx.
set -euo pipefail
OUT="${1:?usage: build_site.sh <out-folder>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EFT_REPO="https://github.com/mischa85/elektron-firmware-tool"
EFT_COMMIT="a5bce9a6af644386d900924082993a805e812874"     # the same commit the desktop tools pin
ZIG_VERSION="0.17.1"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

git clone --quiet "$EFT_REPO" "$WORK/eft"
git -C "$WORK/eft" -c advice.detachedHead=false checkout --quiet "$EFT_COMMIT"
python3 -m pip install --quiet "ziglang==$ZIG_VERSION"
python3 -m ziglang cc -target wasm32-wasi -Os -s -Wl,-z,stack-size=1048576 -o "$WORK/eft.wasm" "$WORK"/eft/*.c

rm -rf "$OUT"; mkdir -p "$OUT/engine"
cp "$ROOT"/web/index.html "$ROOT"/web/app.js "$ROOT"/web/worker.js "$OUT/"
cp "$ROOT"/web/engine/*.js "$OUT/engine/"
cp "$WORK/eft.wasm" "$OUT/engine/eft.wasm"
cp "$ROOT/builder/resources/catalog.json" "$OUT/catalog.json"
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_NOTICES.md" "$OUT/"
cp "$ROOT/licenses/elektron-firmware-tool-MIT.txt" "$OUT/engine/eft-LICENSE.txt"

want="$(cat "$ROOT/tools/web/eft.wasm.sha256")"
got="$(sha256sum "$OUT/engine/eft.wasm" | cut -d' ' -f1)"
if [ "$got" = "$want" ]; then echo "eft.wasm: reproducible build, sha256 $got"
else echo "::warning::eft.wasm sha256 $got differs from the recorded $want (another compiler build?)"; fi

python3 - "$OUT" <<'PY'
import sys, pathlib
bad = [p for p in pathlib.Path(sys.argv[1]).rglob("*") if p.is_file()
       and (p.suffix.lower() in (".syx", ".bin", ".raw", ".img", ".elf") or b"\xf0\x00\x20\x3c" in p.read_bytes())]
if bad:
    sys.exit("REFUSED, looks like firmware: " + ", ".join(map(str, bad)))
print("site checked: no firmware")
PY
echo "site ready in $OUT"
