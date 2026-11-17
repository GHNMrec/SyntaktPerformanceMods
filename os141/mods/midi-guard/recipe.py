"""How the stock OS 1.41 builds the per-parameter objects of the MIDI machine's ids.

Runs the stock static initializer (0x401885D2) in Unicorn with a bump allocator in place of the OS
heap and records, for each object of interest, the encoder type written at +0, the source of the
16-byte value prototype copied to +4 (memcpy 0x40115F78) and the prototypes copy-constructed into
+20 (formatter), +36 (graphic), +52 and +68 (style). Used by make_patch.py and tests/test_midi_guard.py.
"""

from __future__ import annotations

import struct

from unicorn import UC_ARCH_M68K, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_BIG_ENDIAN, Uc
from unicorn.m68k_const import UC_CPU_M68K_ANY, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR

LOAD = 0x4000_0400
OBJS, OBJ_SIZE = 0x41B9_FA24, 84
INIT = 0x4018_85D2                      # static initializer: prototypes, objects, pages
NEW, DELETE = 0x4010_350C, 0x4010_3712  # buddy allocator / free
MEMCPY = 0x4011_5F78
COPIES = (0x4018_82BE, 0x4018_82F0, 0x4018_8322, 0x4018_8354)  # identical std::function copy ctors
RET, HEAP = 0x47FF_FF00, 0x4600_0000


def _ret(uc):
    sp = uc.reg_read(UC_M68K_REG_A7)
    uc.reg_write(UC_M68K_REG_PC, struct.unpack(">I", uc.mem_read(sp, 4))[0])
    uc.reg_write(UC_M68K_REG_A7, sp + 4)


def boot(sec3: bytes, area: dict[int, bytes] | None = None, watch=()):
    """Runs the initializer; returns (uc, log). log: ('copy'|'memcpy'|'write', id, offset, ...)."""
    uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, cpu=UC_CPU_M68K_ANY)
    uc.mem_map(0x4000_0000, 0x0800_0000)        # DDR: code, BSS, heap, stack
    uc.mem_write(LOAD, bytes(sec3))
    for a, d in (area or {}).items():
        uc.mem_write(a, d)
    uc.mem_map(0x8000_0000, 0x0010_0000)        # SRAM
    uc.mem_map(0xFC00_0000, 0x0300_0000)        # peripherals (not used by the initializer)
    uc.mem_write(RET, b"\x4e\x75")
    heap = [HEAP]
    log = []
    objs = {OBJS + OBJ_SIZE * i: i for i in watch}

    def which(a):
        base = OBJS + OBJ_SIZE * ((a - OBJS) // OBJ_SIZE)
        return (objs[base], a - base) if base in objs else None

    def code(uc, addr, size, _):
        sp = uc.reg_read(UC_M68K_REG_A7)
        if addr == NEW:
            n = struct.unpack(">I", uc.mem_read(sp + 4, 4))[0]
            uc.reg_write(UC_M68K_REG_D0, heap[0])
            heap[0] += (n + 15) & ~15
            _ret(uc)
        elif addr == DELETE:
            _ret(uc)
        else:
            dst, src = struct.unpack(">II", uc.mem_read(sp + 4, 8))
            w = which(dst)
            if w:
                log.append(("memcpy" if addr == MEMCPY else "copy", w[0], w[1], src))

    def write(uc, access, addr, size, value, _):
        w = which(addr)
        if w and w[1] == 0 and size == 4:
            log.append(("write", w[0], 0, value & 0xFFFFFFFF, uc.reg_read(UC_M68K_REG_PC)))

    for a in (NEW, DELETE, MEMCPY, *COPIES):
        uc.hook_add(UC_HOOK_CODE, code, begin=a, end=a)
    if watch:
        uc.hook_add(UC_HOOK_MEM_WRITE, write, begin=min(objs), end=max(objs) + OBJ_SIZE)
    sp = RET - 0x2000
    uc.mem_write(sp, struct.pack(">I", RET))
    uc.reg_write(UC_M68K_REG_SR, 0x2700)
    uc.reg_write(UC_M68K_REG_A7, sp)
    uc.emu_start(INIT, RET, count=80_000_000)
    if uc.reg_read(UC_M68K_REG_PC) != RET:
        raise RuntimeError(f"initializer did not return (pc {uc.reg_read(UC_M68K_REG_PC):#x})")
    return uc, log


def recipe(sec3: bytes, ids) -> dict[int, tuple[int, int, int, int, int, int]]:
    """{id: (type, value-prototype source, +20 source, +36 source, +52 source, +68 source or 0 = empty)}."""
    _, log = boot(sec3, watch=ids)
    out = {}
    for i in ids:
        typ = [e[3] for e in log if e[0] == "write" and e[1] == i]
        src = {e[2]: e[3] for e in log if e[0] in ("copy", "memcpy") and e[1] == i}
        kinds = {e[2]: e[0] for e in log if e[0] in ("copy", "memcpy") and e[1] == i}
        src.setdefault(68, 0)                   # no style: +68 left empty by the initializer (e.g. IMPULSE)
        kinds.setdefault(68, "copy")
        if len(typ) != 1 or sorted(src) != [4, 20, 36, 52, 68] or kinds[4] != "memcpy" \
                or any(kinds[o] != "copy" for o in (20, 36, 52, 68)):
            raise RuntimeError(f"id {i}: unexpected construction {typ} {kinds}")
        out[i] = (typ[0], src[4], src[20], src[36], src[52], src[68])
    return out
