"""Sequencer rig (TEST16): stock OS 1.41 (+ mods) booted through the static initializer (test_midi_guard.Boot),
event / trig / lock pools initialised by the OS's own functions; runs the REAL tempo interrupt (0x4008AB06) and
sequencer tick (0x4008C924) against a pattern and kit in RAM, logging every event the OS schedules (0x4011A648)
or pushes (0x4011A722). The audio side is not run: a scheduled event is logged and freed (event, trig data, lock
set) as the dispatcher would after playing it. The pattern source (0x43BD7534 / 0x43BD7538: function slots
answering {pattern, kit}) is a stub; with per-pattern length, every pattern end is a pattern change in the rig."""
import sys, struct, json
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_ROOT / "tests"), str(_ROOT / "tools" / "unpack"), str(_ROOT / "mods" / "midi-guard")]
import test_midi_guard as T
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR

TEMPO, TICK = 0x4008AB06, 0x4008C924
TEMPO_RTE, TICK_RTE = 0x4008AEA6, None
SCHED, PUSH = 0x4011A648, 0x4011A722
PAT, KIT = 0x47000000, 0x47100000
NT, TRK, PATLEN = 13, 1177, 136076

def u32(uc, a): return struct.unpack(">I", uc.mem_read(a, 4))[0]

class Rig:
    def __init__(self, mods=(), boot=None, specs=None):
        """mods: names under mods/ (their patch.json); or boot = a ready test_midi_guard.Boot (a final image)
        with specs = the manifest's mod entries (for the symbols)."""
        mods = specs if boot is not None else [json.load(open(_ROOT / "mods" / m / "patch.json")) for m in mods]
        if boot is None:
            sec3 = T.eft.unpack(T.SY, T.ROOT / "unpacked" / T.SY.stem, ids=[3])[3].read_bytes()
            boot = T.Boot(sec3, list(mods))
        self.g = boot
        self.sym = {}
        for m in mods: self.sym.update({k: int(v, 16) for k, v in m.get("symbols", {}).items()})
        uc = self.uc = self.g.uc
        self.g.call(0x4010E658, [])
        self.g.call(0x4011A3A0, [0x8E])
        self.events = []
        self.pending = []
        uc.hook_add(UC_HOOK_CODE, self._sched, begin=SCHED, end=SCHED)
        uc.hook_add(UC_HOOK_CODE, self._push, begin=PUSH, end=PUSH)
        # find the tick handler's rte
        self.tick_rte = self._find_rte(TICK)
        uc.mem_write(PAT, bytes(PATLEN)); uc.mem_write(KIT, bytes(0x2000))
        self.pattern_defaults()
        uc = self.uc
        # pattern source object (0x43BD7534): every slot answers (a0) = {PAT, KIT}
        obj, vt, stub = 0x47200000, 0x47200100, 0x47200200
        uc.mem_write(stub, b"\x20\xbc" + struct.pack(">I", PAT) + b"\x21\x7c" + struct.pack(">I", KIT) + b"\x00\x04\x4e\x75")
        uc.mem_write(vt, struct.pack(">16I", *([stub] * 16)))
        uc.mem_write(obj, struct.pack(">9I", *([stub] * 9)))
        uc.mem_write(0x43BD7534, struct.pack(">I", obj)); uc.mem_write(0x43BD7538, struct.pack(">I", obj))
    def _find_rte(self, a):
        while True:
            if bytes(self.uc.mem_read(a, 2)) == b"\x4e\x73": return a
            a += 2
    def _ev(self, ev):
        uc = self.uc
        typ = u32(uc, ev)
        d = {"type": typ, "ev": ev}
        if typ == 3:
            fp = u32(uc, ev + 16)
            d.update(track=u32(uc, ev + 8), fp=fp, flags=u32(uc, fp + 12), n=u32(uc, fp + 16),
                     notes=list(uc.mem_read(fp + 20, 4)), len=u32(uc, fp + 24), vel=u32(uc, fp + 28),
                     locks=u32(uc, fp + 36))
        elif typ == 0:
            d.update(track=u32(uc, ev + 8), notes=[u32(uc, ev + 24)], n=1,
                     len=u32(uc, ev + 48), vel=struct.unpack(">H", uc.mem_read(ev + 20, 2))[0] >> 8, flags=u32(uc, ev + 36), locks=u32(uc, ev + 68),
                     sound=u32(uc, ev + 40))
        return d
    def _sched(self, uc, a, s, _):
        sp = uc.reg_read(UC_M68K_REG_A7)
        ev, t = struct.unpack(">II", uc.mem_read(sp + 4, 8))
        d = self._ev(ev); d["time"] = t; d["how"] = "sched"
        self.events.append(d)
        # the audio side would play and free it: free it now (event + trig data / lock set), return
        self.pending.append(ev)
        sp2 = sp
        uc.reg_write(UC_M68K_REG_PC, struct.unpack(">I", uc.mem_read(sp, 4))[0]); uc.reg_write(UC_M68K_REG_A7, sp + 4)
    def _push(self, uc, a, s, _):
        sp = uc.reg_read(UC_M68K_REG_A7)
        ev = struct.unpack(">I", uc.mem_read(sp + 4, 4))[0]
        d = self._ev(ev); d["how"] = "push"
        self.events.append(d)
    def pattern_defaults(self, length=16, per_track=False, plen=64):
        uc = self.uc
        uc.mem_write(PAT + 136052, struct.pack(">H", plen if per_track else length))
        uc.mem_write(PAT + 136057, (b"\x01" if per_track else b"\x00") + b"\x02")  # length mode, master scale 1X
        for t in range(NT):
            b = PAT + TRK * t
            uc.mem_write(b + 128, b"\xff" * 64)            # no velocity locks
            uc.mem_write(b + 192, b"\xff" * 64)            # no length locks
            uc.mem_write(b + 512, b"\xff" * 64)            # no conditions
            uc.mem_write(b + 704, b"\xff" * 256)           # no note locks
            uc.mem_write(b + 576, b"\xff" * 64)            # no sound locks
            uc.mem_write(b + 960, bytes([100, 30, 0x07, 0x80, 0, 60, 64, 64, 64]))  # vel, len, flags, notes
            uc.mem_write(b + 969, struct.pack(">H", length))
            uc.mem_write(b + 972, bytes([2, 100, 5]))
    def trig(self, t, s, on=True):
        a = PAT + TRK * t + 2 * s
        w = struct.unpack(">H", self.uc.mem_read(a, 2))[0]
        w = (w | 1) if on else (w & ~1)
        self.uc.mem_write(a, struct.pack(">H", w))
    def note(self, t, s, n):
        self.uc.mem_write(PAT + TRK * t + 704 + s, bytes([n]))
    def chord(self, t, s, notes):            # notes 2..4 as offsets (64 + offset)
        for i, o in enumerate(notes):
            self.uc.mem_write(PAT + TRK * t + 704 + 64 * (i + 1) + s, bytes([64 + o]))
    def start(self):
        uc = self.uc
        for a in (0x43BD7430, 0x43BD7438, 0x43BD74D0): uc.mem_write(a, struct.pack(">I", PAT))
        for a in (0x43BD743C, 0x43BD7444, 0x43BD74D4): uc.mem_write(a, struct.pack(">I", KIT))
        uc.mem_write(0x43BCB3B0, struct.pack(">I", 1))   # start request (tempo handler)

    def run_isr(self, fn, rte):
        uc = self.uc
        sp = 0x47FF0000
        uc.reg_write(UC_M68K_REG_SR, 0x2000); uc.reg_write(UC_M68K_REG_A7, sp)
        uc.ctl_flush_tb()
        uc.emu_start(fn, rte, count=3_000_000)
        assert uc.reg_read(UC_M68K_REG_PC) == rte, hex(uc.reg_read(UC_M68K_REG_PC))
    def interrupt(self):
        """one tempo interrupt + the sequencer tick it fires"""
        self.run_isr(TEMPO, TEMPO_RTE)
        self.run_isr(TICK, self.tick_rte)
    def drain(self):
        for ev in self.pending:
            typ = u32(self.uc, ev)
            fp = u32(self.uc, ev + 16) if typ == 3 else 0
            self.g.call(0x4011A4F8, [ev])
            if fp: self.g.call(0x4010D4CA, [fp])
        self.pending = []
    def full_tick(self):
        """interrupts until the tick handler did a full (24 PPQN) tick"""
        for _ in range(8):
            full = u32(self.uc, 0x43BCB3AC) == 0
            self.interrupt()
            self.drain()
            if full: return
        raise RuntimeError("no full tick")
    def notes(self, track=None):
        return [(e["time"], e["track"], e["notes"][0], e["len"]) for e in self.events
                if e["type"] in (0, 3) and e.get("how") == "sched" and (track is None or e["track"] == track)]
    def steps(self):
        return list(self.uc.mem_read(0x43BD73FC, NT))
    def playing(self):
        return [u32(self.uc, 0x43BD73C8 + 4 * t) for t in range(NT)]

