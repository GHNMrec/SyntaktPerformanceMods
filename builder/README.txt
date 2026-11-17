Syntakt Performance Mods builder
================================
Offline. It reads the OFFICIAL Syntakt OS 1.41 or 1.42 .syx you downloaded from elektron.se (recognised by its
SHA-256), applies the mods you tick with every guard of the MAX builder (stock hash, container checks, each patch
checks the stock bytes it replaces, sections 2 and 6 never touched, boot margin >= 4096 bytes) and writes a NEW
.syx next to where you choose. It never sends anything to a unit and never uploads anything.

Needs: Python 3.10+ with Tk (the python.org Windows installer has both), and elektron-firmware-tool.

ONE-TIME SETUP: put elektron-firmware-tool.exe in the resources folder next to catalog.json. If you also have
Syntakt MAX 1.0's Windows builder, copy it from that builder's resources folder (it is the same MIT tool,
see THIRD_PARTY_NOTICES.txt). Linux / WSL: build it (bash ../os141/tools/unpack/setup_eft.sh) and copy or point
EFT_BIN at it.

RUN:  double-click "Start Syntakt Performance Mods builder.bat"   (or: python app.py)

Groups
  Core (always on)          mod area (128 KB), boot splash, parameter hooks, MIDI id guard, Workbench SY CHORD bank
  Syntakt Performance Mods  the JOG page (hold [TEMPO]) and PERFORM ([RIGHT]): a smooth DJ filter on the analog FX
                            block with its curve over the mix's spectrum (perf-filter: no page, no MIDI). No LINK.
                            See docs/USER_GUIDE.md.

Presets: Syntakt Performance Mods (OS 1.41 / 1.42).

Everything is EXPERIMENTAL: back up your projects and samples and keep a known-good official .syx for recovery.
Your own test notes per group are kept in Documents\SyntaktJOG_builder_notes.json.

Adding the Performance Mods to a MAX build someone already has? Use "Option B - Add to my MAX build.bat" (..\addon\add_to_max.py) instead
(docs\COMBINING_WITH_MAX.md).
