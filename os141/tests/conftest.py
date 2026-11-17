import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools" / "unpack"), str(ROOT / "tools" / "hooks"), str(ROOT / "tools" / "emu")]

# test_midi_guard.py and test_modarea.py are used here as libraries (their Boot / boot helpers start the OS image for every rig);
# their own tests build sets with mods that are not part of this repo (master-comp, fx3, ...) and live in the full MAX repository.
collect_ignore = ["test_midi_guard.py", "test_modarea.py"]
