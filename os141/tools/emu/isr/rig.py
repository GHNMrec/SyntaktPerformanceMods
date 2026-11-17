"""Audio-interrupt rig: a booted board, a playable kit, test audio, and probes on the delay/reverb path.

    r = Rig(syx, manifest=None)    # manifest: the build's mods (their EMAC sites); None for the stock OS
    r.kit()                        # 12 tracks with level, VOL, centre PAN, DEL/REV sends; delay/reverb on
    p = r.block()                  # one audio interrupt; p: this block's delay/reverb/bus buffers

No project is loaded and CPU #2 is not running: the kit is a set of engine words (0x800021B0) written again
before every block's copy routine, the copy's smoothed part starts converged on them, the digital tracks' audio
is written where CPU #2's DMA would leave it (after the OS clears that buffer), the per-track velocity words (high
byte) are set at the mix entry, and the tempo is 120 BPM. Test tones also go into the ADC ring, but the OS does not
pick them up in this rig yet (its ADC path, 0x40096234 -> 0x80004760 -> 0x80003950, reads a double-buffered ring
half the rig does not fill): the analog tracks, the input and the FX block's output (ADC 6/7) are silent here.
"""
from __future__ import annotations

import json
import math
import random
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE

from board import Board, run_isr, section3

HERE = Path(__file__).resolve().parent
OS_SITES = json.loads((HERE / "os141_sec3_emac_sites.json").read_text())["sites"]
ENGINE, COPY = 0x8000_21B0, 0x8000_6348
DELAY_FN, REVERB_FN = 0x4009_6890, 0x4009_6E3C
DLY_IN, DLY_OUT, REV_OUT = 0x8000_DBD0, 0x8000_DCD0, 0x8000_DDD0
FXBUS, DIRECT = 0x8000_DAD0, 0x8000_DFD0      # into the analog FX block (x10) / direct to the mixer (x8)
ADC_RING = 0x8000_1800                         # 8 slots per frame
CV = 0x8000_3160                               # CV struct the CV routines write (analog hardware)
DAC_RING = 0x8000_0000
FX = 12                                        # FX track index in the engine block
# copy / engine offsets of the FX track and the send effects (docs/audio-path.md)
DLY = 1766                                     # delay: TIME X WID FDBK HPF LPF REV VOL routing (1766..1782)
REV = 1786                                     # reverb: PRE DEC FREQ GAIN HPF LPF VOL routing (1786..1800)
DLY_ROUT, REV_ROUT, IN_ROUT = 1782, 1800, 1818
FX_DEL, FX_REV, FX_PAN, FX_VOL = 1858, 1860, 1862, 1864
MIX_FX = 24                                    # mixer FX level


def eng(t, iid):
    """Engine word of an audio track's parameter (internal id)."""
    return ENGINE + 142 * t + 28 + 2 * iid


def mods_sites(manifest):
    out = []
    for m in json.loads(Path(manifest).read_text())["mods"]:
        out += [int(a, 16) for a in m.get("emac_sites", [])]
    return out


class Rig:
    def __init__(self, syx, manifest=None):
        sites = list(OS_SITES) + (mods_sites(manifest) if manifest else [])
        self.b = Board(section3(Path(syx)), emac_sites=sites)
        self.uc = self.b.uc
        self.probe = {}
        self.uc.hook_add(UC_HOOK_CODE, self._at_delay, begin=DELAY_FN, end=DELAY_FN)
        self.uc.hook_add(UC_HOOK_CODE, self._at_reverb, begin=REVERB_FN, end=REVERB_FN)
        self.uc.hook_add(UC_HOOK_CODE, self._voices, begin=0x400A_4ABE, end=0x400A_4ABE)  # after memclr(0x80003D50)
        self.uc.hook_add(UC_HOOK_CODE, self._engine, begin=0x400A_4A00, end=0x400A_4A00)  # before the copy routine
        self.uc.hook_add(UC_HOOK_CODE, self._converged, begin=0x400A_4A0C, end=0x400A_4A0C)  # after it
        self.uc.hook_add(UC_HOOK_CODE, self._mix, begin=0x4008_F1CA, end=0x4008_F1CA)  # mix entry
        self.engine_words = {}
        self.voices = [0] * 256
        self.n = 0
        self.rnd = random.Random(1)

    def w16(self, a, v):
        """An engine word of the kit: written now and again before every block's copy routine."""
        self.engine_words[a] = v
        self.uc.mem_write(a, struct.pack(">h", v if v < 0x8000 else v - 0x10000))

    def word(self, off, v):
        """Engine (kit) word at copy offset `off`."""
        self.w16(ENGINE + off, v)

    def copy_word(self, off):
        return struct.unpack(">H", self.uc.mem_read(COPY + off, 2))[0]

    def _converged(self, uc, addr, size, _):
        """The copy as if the one-pole smoothing had long converged on the kit's words."""
        for a, v in self.engine_words.items():
            if ENGINE <= a < ENGINE + 1876:
                uc.mem_write(COPY + a - ENGINE, struct.pack(">H", v & 0xFFFF))

    def _engine(self, uc, addr, size, _):
        for a, v in self.engine_words.items():
            uc.mem_write(a, struct.pack(">H", v & 0xFFFF))
        uc.mem_write(0x8000_2F58, bytes([32] * 4))                       # analog tracks: a machine with unity gain

    def _mix(self, uc, addr, size, _):
        uc.mem_write(0x8000_4670, struct.pack(">12h", *[0x7F00] * 12))  # per-track velocity (high byte; no sequencer)

    def _voices(self, uc, addr, size, _):
        uc.mem_write(0x8000_3D50, struct.pack(">256i", *self.voices))

    def _at_delay(self, uc, addr, size, _):
        self.probe["dly_in"] = self.b.longs(DLY_IN, 64)

    def _at_reverb(self, uc, addr, size, _):
        self.probe["rev_in"] = self.b.longs(DLY_IN, 64)              # the OS reuses 0x8000DBD0 for the reverb
        self.probe["dly_out"] = self.b.longs(DLY_OUT, 64)

    def kit(self, sends=(0x5000, 0x5000), rout_direct=True, delay_vol=0x6000, reverb_vol=0x6000, returns=0x100):
        """Engine words for a playable kit (the copy of the live values converges to them). `returns`: the delay
        and reverb FX routing (0x100 direct, 0 through the FX block)."""
        for t in range(12):
            self.w16(ENGINE + 2 * t, 100 << 8)                         # track level
            self.w16(eng(t, 45), sends[0])                             # DEL send
            self.w16(eng(t, 46), sends[1])                             # REV send
            self.w16(eng(t, 47), 0x4000)                               # PAN centre
            self.w16(eng(t, 48), 110 << 8)                             # VOL
            self.w16(eng(t, 49), 0x100 if rout_direct else 0)          # ROUT: direct
        self.word(MIX_FX, 100 << 8)                                    # mixer FX level
        for i, v in enumerate((8 << 8, 0, 0x7F00, 0x5000, 0, 0x7F00, 0, delay_vol, returns)):
            self.word(DLY + 2 * i, v)
        for i, v in enumerate((0x1000, 0x6000, 0x7F00, 0x4000, 0, 0x7F00, reverb_vol, returns)):
            self.word(REV + 2 * i, v)
        self.word(FX_VOL, 110 << 8)                                    # FX AMP VOL (default 110)
        self.word(FX_PAN, 0x4000)                                      # FX AMP PAN centre
        self.uc.mem_write(0x402D_7010, struct.pack(">I", 120 * 120))   # tempo 120 BPM
        # audio DMA positions (MMIO): ADC ring write position (ch 52 DADDR), DAC ring read position (ch 54 SADDR)
        self.b.edma.set_reg(0xFC04_5690, ADC_RING + 0x400)
        self.b.edma.set_reg(0xFC04_56C0, 0x8000_0400)
        self.sync()

    def sync(self):
        """After changing kit words: start the copy converged on them."""
        self.uc.mem_write(COPY, bytes(self.uc.mem_read(ENGINE, 1876)))

    def audio(self):
        """Test audio: digital tracks (bursts of noise, every 8th block); tones for ADC 0-3 (not picked up yet)."""
        k = self.n
        rnd = self.rnd
        voices = []
        for t in range(8):
            on = (k + t) % 8 == 0
            voices += [rnd.randrange(-1 << 28, 1 << 28) if on else 0 for _ in range(32)]
        self.voices = voices
        ring = []                                                  # 2 KB ring: 64 frames x 8 slots
        for f in range(64):
            for ch in range(8):
                ring.append(int(0.2 * 2**31 * math.sin(2 * math.pi * (110 + 40 * ch) * (k * 32 + f) / 48000))
                            if ch < 4 else 0)
        self.uc.mem_write(ADC_RING, struct.pack(">512i", *ring))

    def block(self):
        self.probe = {}
        self.audio()
        run_isr(self.b)
        for key, a in (("rev_out", REV_OUT), ("direct", DIRECT), ("fxbus", FXBUS)):
            self.probe[key] = self.b.longs(a, 64)
        self.n += 1
        return self.probe


def rms(v):
    return math.sqrt(sum(x * x for x in v) / max(1, len(v))) / 2**31
