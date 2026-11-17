# Audio-interrupt emulator (CPU #1)

Runs the **real audio interrupt** (`0x400A3856`) of a built image in Unicorn, block by block, next to the stock
OS 1.41, to check that a mod changes only what it means to change in the mix, the delay and the reverb.

- `board.py`: memory map, boot as the device does it (SRAM data, BSS clear with the MAX mod-area loader, static
  initializer with a bump allocator), an eDMA model as MMIO (the delay line at `0x4FC00000` goes through it), EMAC
  through `tools/emu/emac.py` at every EMAC site (stock sites in `os141_sec3_emac_sites.json`, from
  `gen_sites.py`, plus the build's mod sites).
- `rig.py`: a playable kit as engine words (no project loaded, CPU #2 not running: the digital tracks' audio is
  written where CPU #2's DMA would leave it), probes on the delay and reverb buffers and on both buses (`0x8000DAD0`
  into the analog FX block, `0x8000DFD0` direct). The ADC path is not fed yet: analog tracks, the input and the FX
  block's output (ADC 6/7) are silent, so their sends are checked as gains (`checks.fx_block_sends`), not as audio.
- `checks.py`: the report (`python tools/emu/isr/checks.py BUILD.syx MANIFEST.json`), also run by
  `tests/test_audio_isr.py` when `MAX_SYX` and `MAX_MANIFEST` are set:
  1. delay/reverb inputs and outputs bit-identical to stock, mods at rest and busy;
  2. FLTR ON bit-identical to stock whose copy of the live values gets the same edits by hand (DAC ring, buses,
     delay/reverb, CV struct but the resonance CV);
  3. the OS's loop guards with FLTR ON (delay → reverb kept since TEST15b, the FX block's own DEL/REV sends muted
     with RET FLTR, working with RET KIT on a kit routed direct);
  4. instructions and peak stack per interrupt.

TEST15b figures: stock 68 715 instructions per interrupt, the build 70 058 at rest (+2.0 %: FM4's page-2
publisher ~820, fx3 ~180, Workbench ~180, master-comp ~150, master-filter ~40) and 73 715 with everything busy
(+7.3 %); peak stack 844 B stock, 884 B at rest, 944 B busy (fx3's frames inside the mix). The interrupt runs on
the stack of whatever task it interrupts (tasks run in supervisor mode, one A7; the smallest task stacks are 2 KB
and 4 KB). On the device the interrupt was timed at ~89 % of the CPU at rest (docs/audio-path.md, CPU load): the
UI and every other task share what is left, so each per-block instruction counts. TEST15c: 70 061 at rest and
73 718 busy (+3 per interrupt: master-comp reads the current pattern while the kit pointer is 0), same stacks.

Not modelled: the analog parts (FX block, VCAs, the voices themselves), CPU #2, the sequencer, the UI and MIDI.
