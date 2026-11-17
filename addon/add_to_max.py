"""Option B, the friendly way: add Syntakt Performance Mods to YOUR Syntakt MAX build.

Double-click "Option B - Add to my MAX build.bat" (or: python addon/add_to_max.py). It asks for two files:

  1. your MAX manifest, e.g. max-1.0-manifest.json (MAX 1.0's Windows builder keeps it in its resources folder);
  2. YOUR official Syntakt OS .syx from elektron.se, the one that manifest was made for.

Then it runs the three steps of perfmods_addon.py in order and stops at the first one that fails:

  1. --verify-base  builds your MAX alone and checks it equals the manifest's golden hash (proves the inputs);
  2. --dry-run      merges the Performance Mods and runs every guard without writing anything;
  3. the build      writes ONE new .syx next to your OS file. Nothing is overwritten and nothing is sent anywhere.

Both files can also be given on the command line:  python addon/add_to_max.py MANIFEST.json OS.syx [--tripwire]
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import perfmods_addon as A  # noqa: E402


def pick(title, kinds):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return input(f"{title}\n  path: ").strip().strip('"')
    root = tk.Tk()
    root.withdraw()
    p = filedialog.askopenfilename(title=title, filetypes=kinds)
    root.destroy()
    return p


def has_tripwire():
    """the crash tripwire is offered only by builds whose catalog has it (the public copy's does not)"""
    cat = Path(__file__).resolve().parents[1] / "builder" / "resources" / "catalog.json"
    return any(g.get("id") == "tripwire" for g in json.loads(cat.read_text(encoding="utf-8"))["groups"])


def ask_tripwire():
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        return input("Add the crash tripwire (diagnostic)? [y/N] ").strip().lower().startswith("y")
    root = tk.Tk()
    root.withdraw()
    yes = messagebox.askyesno("Crash tripwire?", "Also add the crash tripwire?\n\nIt is a diagnostic: if the unit "
                              "ever crashes it stops on a screen starting 57AC (photograph it) instead of freezing "
                              "silently. Safe to leave out.", default="no")
    root.destroy()
    return yes


def run(args):
    """perfmods_addon.main, with its sys.exit() messages turned into a printed reason and a failure"""
    try:
        return A.main(args)
    except SystemExit as e:
        if e.code not in (0, None):
            print(e.code if isinstance(e.code, str) else f"stopped ({e.code})")
            return 1
        return 0


def free_name(folder: Path, stem: str) -> Path:
    out = folder / f"{stem}.syx"
    n = 2
    while out.exists():
        out = folder / f"{stem} ({n}).syx"
        n += 1
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    tripwire = "--tripwire" in argv
    print(__doc__.split("\n\n")[0], "\n")
    manifest = args[0] if len(args) > 0 else pick("1/2  Your MAX manifest (e.g. max-1.0-manifest.json)",
                                                  [("MAX manifest", "*.json"), ("All files", "*.*")])
    if not manifest:
        print("No manifest picked: nothing done.")
        return 1
    stock = args[1] if len(args) > 1 else pick("2/2  YOUR official Syntakt OS .syx (from elektron.se)",
                                               [("Syntakt OS", "*.syx"), ("All files", "*.*")])
    if not stock:
        print("No OS file picked: nothing done.")
        return 1
    if len(args) < 2 and "--tripwire" not in argv and has_tripwire():
        tripwire = ask_tripwire()

    m = json.loads(Path(manifest).read_text(encoding="utf-8"))
    osv = m.get("os", "?")
    base = ["--manifest", manifest, "--stock", stock]

    print(f"Manifest: {manifest}  ({m.get('name', 'MAX')}, OS {osv})\nOS file:  {stock}\n")
    print("Step 1/3: does this builder reproduce your MAX exactly?")
    if run(base + ["--verify-base"]) != 0:
        print("\nSTOPPED at step 1: your MAX does not rebuild to its golden hash from these files.\n"
              "Check that the OS file is the official one the manifest names. Nothing was written.")
        return 1
    print("\nStep 2/3: merge the Performance Mods and run every guard (nothing written yet)")
    extra = ["--tripwire"] if tripwire else []
    if run(base + ["--dry-run"] + extra) != 0:
        print("\nSTOPPED at step 2: the Performance Mods don't fit with this MAX (the reason is above).\n"
              "Nothing was written. See docs/COMBINING_WITH_MAX.md.")
        return 1
    out = free_name(Path(stock).resolve().parent,
                    f"Syntakt_MAX_PerfMods_OS{osv}" + ("_tripwire" if tripwire else ""))
    print(f"\nStep 3/3: build {out.name}")
    if run(base + ["--out", str(out)] + extra) != 0:
        print("\nSTOPPED at step 3. Nothing was written.")
        return 1
    print(f"\nDONE. Your new file: {out}\n"
          "Flash it the way you flash any Syntakt OS .syx (follow Elektron's update instructions).\n"
          "Back up your projects and samples first and keep the official OS file for recovery.\n"
          "This file is yours: don't share it. Anyone else builds their own from their own OS file.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
