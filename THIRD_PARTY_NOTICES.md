# Third-party notices

The jog mod is built on top of other people's open work. What comes from where:

| Part | Author / project | Licence | Where |
|---|---|---|---|
| Mod area loader (`modarea`), boot splash (`splash`), parameter hooks (`vparams`), the MIDI id guard (`midi-guard`), the master filter (`master-filter`) and the build/emulator infrastructure they rely on | Angelo-politek and the Syntakt+ / SyntHack contributors, as integrated in Syntakt MAX | MIT | `licenses/SyntHack-MIT.txt` |
| SY CHORD 31-wave bank with pictures, Deja Vu DV-F / DV-T (`workbench-max`) | Bezronczek, Firmware Workbench | MIT | `licenses/Workbench-MIT.txt` |
| Firmware container tool (`elektron-firmware-tool`, not included: you fetch or copy it) | Marcel Bierling / mischa85 | MIT | `licenses/elektron-firmware-tool-MIT.txt` |
| The public Syntakt MAX 1.0 mod list (read by `addon/perfmods_addon.py`, not included) | Kári Garðarsson's MAX integration | MIT (repository) | see MAX's own `ATTRIBUTION.md` |

Déjà Vu's behaviour is inspired by Mutable Instruments Marbles, as credited by Workbench; no Mutable Instruments
code is included. The jog mod itself (JOG page, LINK, PERFORM, LiveLink bridge) is this repository's own work.
Elektron firmware stays Elektron's proprietary work; see `LEGAL.md`.
