"""CPU #1 board model that runs the real audio interrupt (0x400A38CE) of a built image in Unicorn.

- memory: DDR 256 MB at 0x40000000 (the delay ring is at 0x4FC00000), SRAM 1 MB, CPU #2 shared RAM as CPU #1's
  DMA sees it, FPGA/external chips 0xEC000000, peripherals 0xFC000000.., null page;
- boot as the device does it: SRAM data copy 0x4000045C, BSS clear 0x400004B2 (in MAX images it also loads the
  mod area), then the static initializer 0x40188796 with a bump allocator in place of the OS heap;
- an eDMA model (TCDs at 0xFC045000 + 32 n, SSRT 0xFC04401E) as MMIO: minor/major loops, SMOD/DMOD, channel
  linking, scatter/gather; a channel runs to completion as soon as it starts (the delay line, 0x4FC00000, is
  read and written through it);
- EMAC through tools/emu/emac.py at the stock sites (os142_sec3_emac_sites.json) plus the build's mod sites; an
  OS site a mod patched away is dropped.

    b = Board(section3(Path("build.syx")), emac_sites=...)
    run_isr(b)                       # one audio interrupt, up to its final rte, stack balance checked
"""
from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "unpack"), str(ROOT / "tools" / "emu")]
import eft  # noqa: E402
from unicorn import UC_ARCH_M68K, UC_HOOK_CODE, UC_MODE_BIG_ENDIAN, Uc, UcError  # noqa: E402
from unicorn.m68k_const import (UC_CPU_M68K_ANY, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC,  # noqa: E402,F401
                                UC_M68K_REG_SR)

LOAD = 0x4000_0400
INIT = 0x4018_8796
NEW, DELETE = 0x4010_36D0, 0x4010_38d6
RET = 0x4EFF_FF00               # far from everything the OS uses
STACK_TOP = 0x4EFF_0000
HEAP = 0x4E00_0000              # bump allocator for the static initializer (16 MB below the stack)
EDMA, SSRT = 0xFC04_5000, 0xFC04_401E
ISR, ISR_RTE = 0x400A_38CE, 0x400A_5520
DSPI_SR = 0xFC03_C02C


def section3(syx: Path) -> bytes:
    with tempfile.TemporaryDirectory(prefix="isr-") as tmp:
        return eft.unpack(Path(syx), Path(tmp), ids=[3])[3].read_bytes()


class Edma:
    """64 channels as MMIO (0xFC044000..0xFC045FFF): registers kept here; a channel runs when START is set (CSR
    write or SSRT) or when linked (minor ELINK / MAJORELINK); scatter/gather loads the next TCD from memory."""
    BASE, SIZE = 0xFC04_4000, 0x2000

    def __init__(self, uc):
        self.uc = uc
        self.regs = bytearray(self.SIZE)
        self.busy = False
        self.pending = []
        uc.mmio_map(self.BASE, self.SIZE, self._read, None, self._write, None)

    def _read(self, uc, off, size, _):
        return int.from_bytes(self.regs[off:off + size], "big")

    def _write(self, uc, off, size, value, _):
        self.regs[off:off + size] = (value & ((1 << (8 * size)) - 1)).to_bytes(size, "big")
        a = self.BASE + off
        if a == SSRT:
            ch = value & 0x3F
            self._set_csr(ch, self._csr(ch) | 1)
            self.request(ch)
        elif EDMA <= a < EDMA + 64 * 32:
            o = (a - EDMA) % 32
            if o <= 0x1F < o + size:                        # CSR low byte written
                ch = (a - EDMA) // 32
                if self._csr(ch) & 1:
                    self.request(ch)

    def _csr(self, ch):
        o = EDMA - self.BASE + 32 * ch + 0x1E
        return int.from_bytes(self.regs[o:o + 2], "big")

    def _set_csr(self, ch, v):
        o = EDMA - self.BASE + 32 * ch + 0x1E
        self.regs[o:o + 2] = (v & 0xFFFF).to_bytes(2, "big")

    def tcd(self, ch):
        o = EDMA - self.BASE + 32 * ch
        return list(struct.unpack(">IHhIiIHhiHH", bytes(self.regs[o:o + 32])))

    def put(self, ch, t):
        o = EDMA - self.BASE + 32 * ch
        self.regs[o:o + 32] = struct.pack(">IHhIiIHhiHH", *t)

    def set_reg(self, addr, value):
        self.regs[addr - self.BASE:addr - self.BASE + 4] = value.to_bytes(4, "big")

    def request(self, ch):
        self.pending.append(ch)
        if self.busy:
            return
        self.busy = True
        try:
            guard = 0
            while self.pending:
                self.minor(self.pending.pop(0))
                guard += 1
                if guard > 200000:
                    raise RuntimeError("eDMA: endless link chain")
        finally:
            self.busy = False

    @staticmethod
    def _addr(base, off, mod):
        if not mod:
            return (base + off) & 0xFFFF_FFFF
        m = (1 << mod) - 1
        return (base & ~m) | ((base + off) & m)

    def minor(self, ch):
        saddr, attr, soff, nbytes, slast, daddr, citer, doff, dlast, biter, csr = self.tcd(ch)
        smod, ssize, dmod, dsize = attr >> 11, (attr >> 8) & 7, (attr >> 3) & 31, attr & 7
        units = {0: 1, 1: 2, 2: 4, 4: 16, 5: 32}
        su, du = units.get(ssize, 4), units.get(dsize, 4)
        n = nbytes & 0x3FFF_FFFF
        buf = bytearray()
        for _ in range(0, n, su):                            # source reads
            try:
                buf += bytes(self.uc.mem_read(saddr, su))
            except UcError as e:
                raise RuntimeError(f"eDMA ch {ch}: source bus error {saddr:#x}") from e
            saddr = self._addr(saddr, soff, smod)
        for i in range(0, len(buf), du):                     # destination writes
            try:
                self.uc.mem_write(daddr, bytes(buf[i:i + du]))
            except UcError as e:
                raise RuntimeError(f"eDMA ch {ch}: destination bus error {daddr:#x}") from e
            daddr = self._addr(daddr, doff, dmod)
        elink = citer & 0x8000
        mask = 0x1FF if elink else 0x7FFF
        link = (citer >> 9) & 0x3F
        count = ((citer & mask) - 1) & mask
        csr &= ~0x0001
        if count:
            citer = (citer & ~mask) | count
            self.put(ch, [saddr, attr, soff, nbytes, slast, daddr, citer, doff, dlast, biter, csr | 0x40])
            self.pending.append(link if elink else ch)
            return
        saddr = (saddr + slast) & 0xFFFF_FFFF
        csr = (csr | 0x80) & ~0x40
        majorlink, mlch = csr & 0x20, (csr >> 8) & 0x3F
        if elink and link != ch:
            self.pending.append(link)
        if csr & 0x10:                                       # scatter/gather: the next TCD from memory
            nxt = list(struct.unpack(">IHhIiIHhiHH", bytes(self.uc.mem_read(dlast & 0xFFFF_FFFF, 32))))
            self.put(ch, nxt)
            if nxt[10] & 1:
                self.pending.append(ch)
        else:
            daddr = (daddr + dlast) & 0xFFFF_FFFF
            self.put(ch, [saddr, attr, soff, nbytes, slast, daddr, biter, doff, dlast, biter, csr])
        if majorlink:
            self.pending.append(mlch)


class Board:
    def __init__(self, sec3: bytes, emac_sites=()):
        uc = self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, cpu=UC_CPU_M68K_ANY)
        uc.mem_map(0x4000_0000, 0x1000_0000)
        uc.mem_write(LOAD, sec3)
        uc.mem_map(0x8000_0000, 0x0010_0000)
        uc.mem_map(0x1000_0000, 0x0001_0000)               # CPU #2 shared RAM as CPU #1 sees it (DMA source)
        uc.mem_map(0xEC00_0000, 0x0100_0000)               # FPGA / external chip registers
        uc.mem_map(0xFC00_0000, Edma.BASE - 0xFC00_0000)
        uc.mem_map(Edma.BASE + Edma.SIZE, 0xFF00_0000 - Edma.BASE - Edma.SIZE)
        uc.mem_map(0x0000_0000, 0x0010_0000)
        uc.mem_write(RET, b"\x4e\x75")
        self.edma = Edma(uc)
        self.heap = HEAP
        self.call(0x4000_045C, count=20_000_000)          # SRAM data image
        self.call(0x4000_04B2, count=80_000_000)          # BSS clear (+ mod-area loader)
        uc.hook_add(UC_HOOK_CODE, self._new, begin=NEW, end=NEW)
        uc.hook_add(UC_HOOK_CODE, self._del, begin=DELETE, end=DELETE)
        self.call(INIT, count=120_000_000)                # static initializer
        self.dropped = []
        if emac_sites:
            from emac import UnicornEmac, is_emac
            live = [a for a in sorted(set(emac_sites))                 # OS sites a mod hook replaced are gone
                    if is_emac(int.from_bytes(uc.mem_read(a, 2), "big"))]
            self.dropped = sorted(set(emac_sites) - set(live))
            self.emac = UnicornEmac(uc, live)

    # ---- allocator stand-in (static initializer and later allocations)
    def _ret(self, uc):
        sp = uc.reg_read(UC_M68K_REG_A7)
        uc.reg_write(UC_M68K_REG_PC, struct.unpack(">I", uc.mem_read(sp, 4))[0])
        uc.reg_write(UC_M68K_REG_A7, sp + 4)

    def _new(self, uc, addr, size, _):
        sp = uc.reg_read(UC_M68K_REG_A7)
        n = struct.unpack(">I", uc.mem_read(sp + 4, 4))[0]
        p = self.heap
        self.heap += (n + 15) & ~15
        uc.reg_write(UC_M68K_REG_D0, p)
        self._ret(uc)

    def _del(self, uc, addr, size, _):
        self._ret(uc)

    def call(self, fn, args=(), count=5_000_000):
        uc = self.uc
        sp = STACK_TOP - 4 * (len(args) + 1)
        uc.mem_write(sp, struct.pack(f">{len(args) + 1}I", RET, *[a & 0xFFFF_FFFF for a in args]))
        uc.reg_write(UC_M68K_REG_SR, 0x2700)
        uc.reg_write(UC_M68K_REG_A7, sp)
        uc.emu_start(fn, RET, count=count)
        if uc.reg_read(UC_M68K_REG_PC) != RET:
            raise RuntimeError(f"{fn:#x} did not return: pc {uc.reg_read(UC_M68K_REG_PC):#x}")
        return uc.reg_read(UC_M68K_REG_D0) & 0xFFFF_FFFF

    def longs(self, a, n):
        return list(struct.unpack(f">{n}i", self.uc.mem_read(a, 4 * n)))


def run_isr(b: Board, count=20_000_000):
    """One audio interrupt: a format/SR + PC frame on the stack, run up to the final rte."""
    uc = b.uc
    sp = STACK_TOP - 0x100
    uc.mem_write(sp, struct.pack(">II", 0x4000_2000, RET))
    uc.mem_write(DSPI_SR, struct.pack(">I", 1 << 28))      # DSPI transfer done (EOQF)
    uc.reg_write(UC_M68K_REG_SR, 0x2500)
    uc.reg_write(UC_M68K_REG_A7, sp)
    uc.emu_start(ISR, ISR_RTE, count=count)
    pc = uc.reg_read(UC_M68K_REG_PC)
    if pc != ISR_RTE:
        raise RuntimeError(f"ISR stopped at {pc:#x}")
    if uc.reg_read(UC_M68K_REG_A7) != sp:
        raise RuntimeError(f"ISR stack unbalanced: {uc.reg_read(UC_M68K_REG_A7):#x} != {sp:#x}")
