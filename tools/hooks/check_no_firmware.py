"""Check the staged files and stop the commit if any looks like Elektron firmware.

The second line of defence after .gitignore: it covers a ``git add -f`` or an unpacked section renamed to
a harmless extension.
"""

from __future__ import annotations

import subprocess
import sys

# SysEx (F0) + the Elektron manufacturer ID (00 20 3C): the start of every Elektron .syx.
ELEKTRON_SYSEX = b"\xf0\x00\x20\x3c"
CONTAINER_MAGICS = (b"ELE3", b"ELE2", b"ELEK")
FORBIDDEN_EXT = (".syx", ".bin", ".raw", ".elf", ".img")
MAX_BINARY_BYTES = 256 * 1024


def is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def check_blob(path: str, data: bytes) -> str | None:
    """The reason for refusing, or None if the file is fine."""
    if path.lower().endswith(FORBIDDEN_EXT):
        return "a firmware / binary extension"
    if ELEKTRON_SYSEX in data:
        return "contains an Elektron SysEx header (F0 00 20 3C)"
    if is_binary(data):
        if any(m in data for m in CONTAINER_MAGICS):
            return "a binary with an Elektron container magic"
        if len(data) > MAX_BINARY_BYTES:
            return f"a binary of {len(data)} B (> {MAX_BINARY_BYTES} B)"
    return None


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        capture_output=True, check=True,
    ).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def main() -> int:
    problems = []
    for path in staged_files():
        data = subprocess.run(["git", "show", f":{path}"], capture_output=True, check=True).stdout
        if reason := check_blob(path, data):
            problems.append((path, reason))
    if not problems:
        return 0
    print("pre-commit: commit blocked, possible Elektron firmware in the staging area:", file=sys.stderr)
    for path, reason in problems:
        print(f"  {path}: {reason}", file=sys.stderr)
    print("Remove it with: git rm --cached <file>   (see LEGAL.md)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
