# Legal

- This repository contains **no Elektron firmware** and never will. No `.syx`, no section unpacked from one, no
  disassembly of the OS. `.gitignore` excludes them and `tools/hooks/pre-commit` refuses a commit that contains
  anything that looks like one. Turn the hook on once per clone: `git config core.hooksPath tools/hooks`.
- The builder works only on the **official Syntakt OS file you download yourself from Elektron**. It recognises it
  by its SHA-256, validates the container, and writes a new `.syx` on your own disk. It never sends anything to a
  unit and never uploads anything.
- The patches in `builder/resources/catalog.json` and `os*/mods/*/patch.json` are our own bytes plus the guards
  (each one names the SHA-256 of the stock bytes it replaces). They are not a copy of Elektron's code.
- Syntakt and Elektron are trademarks of their owners. No Elektron affiliation or endorsement is claimed.
- Third-party code and credits: see `THIRD_PARTY_NOTICES.md` and `licenses/`.
- **This repository has no licence of its own yet.** Until its owner adds one, the jog mod's own code
  (`os*/mods/tempojog`, `livelink/`, `addon/`, `tools/`) is "all rights reserved". If you are
  a collaborator on the private repository, that means: use it, don't republish it.
