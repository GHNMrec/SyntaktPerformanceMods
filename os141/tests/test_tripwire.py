"""TEST33b tripwire (diagnostic): the stack tripwire, on the stock image with the mod's patches (both OSes).
- the sites: the task create (0x40001640) -> tw_mk, the audio interrupt right after its register save -> tw_blk_hook,
  and before it restores them -> tw_end_hook;
- a create does exactly what stock's does (the TCB, the initial frame, the registers it leaves), and registers and
  paints the stack; the same stack created again keeps its slot; the 17th stack is counted, not registered;
- the interrupt hook does the instruction it replaced (the interrupt flag cleared with d0) and keeps every
  register but d0 / d1 / a0 / a1 (scratch there: the interrupt reloads them);
- GUARD: room under the interrupted SP >= GUARD returns (and is remembered as the least seen); < GUARD stops with
  the screen words (57AC 1 ii, the SP, the task, the room, PC, SR, callers, the least seen, the counters) on the
  bottom of the largest other stack, still painted;
- CANARY: a word written in a stack's bottom 16 is found within one round (one stack a block) and stops (57AC 2);
- the end of the block: the interrupted stack's bottom 32 words checked (57AC 3), the registers restored from the
  interrupt's frame exactly as the instruction it replaced;
- stacks the OS never registered (the boot stack) are left alone."""
import hashlib
import json
import struct
from pathlib import Path

import pytest


def _h(b):
    """stock OS bytes are compared by their SHA-256 (first 16 hex), so no Elektron bytes live in this file"""
    return hashlib.sha256(bytes(b)).hexdigest()[:16]

pytest.importorskip("unicorn")
from unicorn import UC_ARCH_M68K, UC_HOOK_CODE, UC_MODE_BIG_ENDIAN, Uc  # noqa: E402
from unicorn.m68k_const import (UC_CPU_M68K_ANY, UC_M68K_REG_A0, UC_M68K_REG_A2, UC_M68K_REG_A6,  # noqa: E402
                                UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D2, UC_M68K_REG_D7, UC_M68K_REG_SR)

ROOT = Path(__file__).resolve().parents[1]
P142 = ROOT.name == "os142"
OSV = "1.42" if P142 else "1.41"
SEC3 = ROOT / "unpacked" / f"Syntakt_OS{OSV}" / "section_3_MAIN_OS.bin"
SPEC = ROOT / "mods" / "tripwire" / "patch.json"
pytestmark = pytest.mark.skipif(not (SEC3.exists() and SPEC.exists()), reason="needs the stock image unpacked")
LOAD, RET = 0x4000_0400, 0x4FF0_0000
CREATE = 0x4000_1640
ISR_SITE = 0x400A_38DC if P142 else 0x400A_3864
END_SITE = 0x400A_5518 if P142 else 0x400A_54A0
PAINT, GUARD, CANARY, NT = 0x5AC0FFEE, 844, 16, 16
INTC = 0xFC04_C010


class M:
    def __init__(self, patched=True):
        self.spec = json.loads(SPEC.read_text())
        self.sym = {k: int(v, 16) for k, v in self.spec["symbols"].items()}
        uc = self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, cpu=UC_CPU_M68K_ANY)
        for a, s in ((0x4000_0000, 0x1000_0000), (0x8000_0000, 0x1_0000), (0xFC00_0000, 0x10_0000)):
            uc.mem_map(a, s)
        uc.mem_write(LOAD, SEC3.read_bytes())
        if patched:
            for p in self.spec["patches"]:
                uc.mem_write(int(p["ram"] if p.get("append") else p["addr"], 16), bytes.fromhex(p["hex"]))
        self.illegal = None
        if patched:
            lst = (ROOT / "mods" / "tripwire" / "tw.lst").read_text()
            self.illegal = next(int(l.split(":")[0], 16) for l in lst.splitlines() if "\tillegal" in l)
            self.fired = None
            uc.hook_add(UC_HOOK_CODE, self._fire, begin=self.illegal, end=self.illegal)

    def _fire(self, uc, a, s, _):
        sp = uc.reg_read(UC_M68K_REG_A7)
        self.fired = (sp, self.words(sp, 12))
        uc.emu_stop()

    def words(self, a, n):
        return list(struct.unpack(f">{n}I", self.uc.mem_read(a, 4 * n)))

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))

    def call(self, fn, args, sp=0x4F80_0000, sr=0x2000, regs=()):
        uc = self.uc
        sp -= 4 * (len(args) + 1)
        uc.mem_write(sp, struct.pack(f">{len(args) + 1}I", RET, *[a & 0xFFFFFFFF for a in args]))
        uc.reg_write(UC_M68K_REG_SR, sr)
        uc.reg_write(UC_M68K_REG_A7, sp)
        for r, v in regs:
            uc.reg_write(r, v)
        uc.emu_start(fn, RET, count=2_000_000)
        return uc.reg_read(UC_M68K_REG_A7)

    def create(self, tcb, entry, prio, stack, size, **kw):
        return self.call(CREATE, [tcb, entry, prio, stack, size], **kw)

    def g(self, name, i=None):
        a = self.sym[name] + (4 * i if i is not None else 0)
        return self.words(a, 1)[0]

    def block(self, fp):
        """the interrupt hook, as the audio interrupt calls it (a6 = its frame pointer, d0 = 0x7FFFFFFF)"""
        self.fired = None
        self.call(self.sym["tw_blk_hook"], [], sp=fp - 164, regs=((UC_M68K_REG_A6, fp), (UC_M68K_REG_D0, 0x7FFFFFFF)))
        return self.fired


TASKS = [(0x4700_0000 + 0x100 * i, 0x4710_0000 + 0x100 * i, 5, 0x4800_0000 + 0x10_0000 * i, sz)
         for i, sz in enumerate((0x800, 0x1000, 0x4000, 0x8000, 0x28000))]


def setup_tasks(m):
    for t in TASKS:
        m.create(*t)


def test_sites():
    spec = json.loads(SPEC.read_text())
    sym = {k: int(v, 16) for k, v in spec["symbols"].items()}
    sec3 = SEC3.read_bytes()
    fixed = {int(p["addr"], 16): bytes.fromhex(p["hex"]) for p in spec["patches"] if not p.get("append")}
    assert fixed == {CREATE: b"\x4e\xf9" + struct.pack(">I", sym["tw_mk"]),
                     ISR_SITE: b"\x4e\xb9" + struct.pack(">I", sym["tw_blk_hook"]),
                     END_SITE: b"\x4e\xb9" + struct.pack(">I", sym["tw_end_hook"])}
    assert _h(sec3[END_SITE - LOAD:END_SITE - LOAD + 10]) == "4d85180a0f3ee33c"
    assert _h(sec3[CREATE - LOAD:CREATE - LOAD + 6]) == "a3c4dbcdce0dda5f"
    assert _h(sec3[ISR_SITE - LOAD - 14:ISR_SITE - LOAD + 6]) == "92d9733cdc1821e8"
    app = [p for p in spec["patches"] if p.get("append")]
    assert len(app) == 1 and int(app[0]["ram"], 16) + app[0]["len"] <= int(app[0]["ram"], 16) - 0x10B00 + 0x11000
    assert _h(sec3[ISR_SITE - LOAD + 6:ISR_SITE - LOAD + 12]) == "c9cf06c221c15f36"   # d0 reloaded right after


def test_create_is_stock_and_registers_and_paints():
    m, s = M(), M(patched=False)
    for x in (m, s):
        for a in range(0x4800_0000, 0x4800_0800, 4):
            x.w32(a, 0x11111111)
    sp_m = m.create(0x4700_0000, 0x4710_0000, 7, 0x4800_0000, 0x802)       # odd size: rounded down as stock
    sp_s = s.create(0x4700_0000, 0x4710_0000, 7, 0x4800_0000, 0x802)
    assert sp_m == sp_s
    assert m.words(0x4700_0000, 21) == s.words(0x4700_0000, 21)              # the TCB
    assert m.words(0x4800_0800 - 12, 3) == s.words(0x4800_0800 - 12, 3)      # the task's first frame
    for r in (UC_M68K_REG_D0, UC_M68K_REG_A0):
        assert m.uc.reg_read(r) == s.uc.reg_read(r)
    assert m.words(0x4800_0000, 0x200 - 3) == [PAINT] * (0x200 - 3)          # painted up to the frame
    assert m.g("tw_n") == 1 and m.g("tw_base", 0) == 0x4800_0000 and m.g("tw_end", 0) == 0x4800_0800
    assert m.g("tw_entry", 0) == 0x4710_0000
    m.create(0x4700_0000, 0x4710_0000, 7, 0x4800_0000, 0x800)               # the same stack again: same slot
    assert m.g("tw_n") == 1
    for i in range(20):
        m.create(0x4700_1000 + 0x60 * i, 0x4710_0000 + i, 3, 0x4900_0000 + 0x1000 * i, 0x400)
    assert m.g("tw_n") == NT and m.g("tw_skip") == 20 - (NT - 1)


def test_create_never_paints_under_its_own_feet():
    m = M()
    m.w32(0x4800_0F00, 0x22222222)
    m.create(0x4700_0000, 0x4710_0000, 7, 0x4800_0000, 0x1000, sp=0x4800_0F40)   # created on the stack itself
    assert m.words(0x4800_0F00, 1) == [0x22222222]
    assert m.words(0x4800_0000, 4) == [PAINT] * 4


def test_isr_hook_does_the_replaced_instruction_and_keeps_registers():
    m = M()
    setup_tasks(m)
    m.w32(INTC, 0xFFFFFFFF)
    fp = 0x4830_0000 - 0x2000
    regs = ((UC_M68K_REG_D2, 0x12345678), (UC_M68K_REG_D7, 0x9ABCDEF0), (UC_M68K_REG_A2, 0x47474747),
            (UC_M68K_REG_A6, fp), (UC_M68K_REG_D0, 0x7FFFFFFF))
    sp = m.call(m.sym["tw_blk_hook"], [], sp=fp - 164, regs=regs)
    assert sp == fp - 164                                                   # balanced
    assert m.words(INTC, 1) == [0x7FFFFFFF]                                  # the flag cleared as stock clears it
    for r, v in regs[:4]:                                                   # d0: reloaded by the next instruction
        assert m.uc.reg_read(r) == v
    assert m.fired is None and m.g("tw_blk") == 1


def test_guard():
    m = M()
    setup_tasks(m)
    base, end = TASKS[0][3], TASKS[0][3] + TASKS[0][4]                      # the 2 KB stack
    fp = base + GUARD - 12                                                   # room under the interrupted SP = GUARD
    assert m.block(fp) is None
    assert m.g("tw_least") == GUARD and m.g("tw_lix") == 0
    m.w32(fp, 0x0000_1234)
    m.w32(fp + 4, 0x2000_2000)                                               # format / SR
    m.w32(fp + 8, 0x4008_C930)                                               # the interrupted PC
    m.w32(fp + 12, 0x0000_0007)
    m.w32(fp + 16, 0x4010_3EF0)                                              # callers up the stack
    m.w32(fp + 20, 0x4000_2DD4)
    f = m.block(fp - 4)                                                      # 4 B less: GUARD - 4
    assert f is not None
    sp, w = f
    big = TASKS[4]                                                           # the largest other stack, painted
    assert big[3] <= sp < big[3] + 4096 + 64
    assert w[0] == 0x57AC_1000 and w[1] == fp + 8 and w[2] == base and w[3] == 0x800 and w[4] == TASKS[0][1]
    assert w[5] == GUARD - 4 and w[6] == m.words(fp - 4 + 8, 1)[0]
    assert w[8:10] != [0, 0]
    assert w[10] >> 16 == GUARD - 4 and (w[10] >> 8) & 0xFF == 0 and w[10] & 0xFF == len(TASKS)
    assert w[11] >> 8 == 2 and w[11] & 0xFF == 0
    assert m.words(big[3], 64) == [PAINT] * 64                               # the screen's stack: room below


def test_canary_found_within_a_round():
    m = M()
    setup_tasks(m)
    fp = TASKS[3][3] + 0x6000                                                # plenty of room: no GUARD
    for _ in range(len(TASKS)):
        assert m.block(fp) is None
    victim = TASKS[2]
    m.w32(victim[3] + 8, 0)
    m.w32(victim[3] + 12, 0)
    hit = None
    for k in range(len(TASKS)):
        hit = m.block(fp)
        if hit:
            break
    assert hit is not None and k < len(TASKS)
    w = hit[1]
    assert w[0] == 0x57AC_2002 and w[1] == victim[3] + 8 and w[5] == 2 and w[2] == victim[3]


def test_unregistered_stack_left_alone():
    m = M()
    setup_tasks(m)
    assert m.block(0x4F00_0100) is None                                      # the boot stack: not a task's
    assert m.g("tw_least") == 0xFFFF


def test_no_tasks_yet_costs_nothing():
    m = M()
    assert m.block(0x4F00_0100) is None and m.g("tw_blk") == 1


def end_block(m, fp, regs=()):
    """the start of the block (which finds the interrupted stack), then its end"""
    assert m.block(fp) is None
    m.fired = None
    m.call(m.sym["tw_end_hook"], [], sp=fp - 200, regs=((UC_M68K_REG_A6, fp),) + tuple(regs))
    return m.fired


def test_end_of_block_restores_registers_like_stock():
    m = M()
    setup_tasks(m)
    fp = TASKS[3][3] + 0x6000
    saved = [0x1000 + i for i in range(14)]                                  # d0-d7, a0-a5 at -164(fp)
    m.uc.mem_write(fp - 164, struct.pack(">14I", *saved))
    assert end_block(m, fp) is None
    from unicorn.m68k_const import UC_M68K_REG_D1, UC_M68K_REG_A5
    assert [m.uc.reg_read(r) for r in (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D7,
                                       UC_M68K_REG_A0, UC_M68K_REG_A2, UC_M68K_REG_A5)] == \
        [saved[0], saved[1], saved[2], saved[7], saved[8], saved[10], saved[13]]
    assert m.uc.reg_read(UC_M68K_REG_A6) == fp


def test_end_of_block_catches_an_overrun_of_the_interrupted_stack():
    m = M()
    setup_tasks(m)
    t = TASKS[0]
    fp = t[3] + 1500                                                          # the 2 KB stack, interrupted here
    assert end_block(m, fp) is None
    m.w32(t[3] + 100, 0x4008_0000)                                           # word 25 of the bottom 32: overrun
    f = end_block(m, fp)
    assert f is not None
    w = f[1]
    assert w[0] == 0x57AC_3000 and w[1] == t[3] + 100 and w[5] == 1 and w[2] == t[3] and w[3] == 0x800
    m2 = M()
    setup_tasks(m2)
    m2.w32(TASKS[1][3] + 4, 0)                                               # another stack's bottom: not this check's
    assert end_block(m2, fp) is None
