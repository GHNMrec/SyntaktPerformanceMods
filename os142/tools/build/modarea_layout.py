"""Indirizzi dell'area mod, condivisi da mods/modarea e da tutte le mod che la usano (OS 1.41).

Dalla v0.8.2 l'area mod e' un blocco dell'heap dell'OS (allocatore buddy 0x401036D0, pool di 16 MB nel BSS
a 0x444E48C0..0x454E48C0): il primo blocco da 64 KB, prenotato da modarea alla prima allocazione, quindi
sempre lo stesso e mai assegnato ad altri. Fino alla v0.8.1 stava a 0x46000000, sopra il BSS: RAM che l'OS
usa a runtime (caricamento dei campioni, issue #4).
"""

from __future__ import annotations

HEAP_BLOCK = 0x444E_48C0        # primo blocco dell'heap (indice 0)
HEAP_BLOCK_SIZE = 0x2_0000      # richiesta all'allocatore: 128 KB (ordine 13; TEST20a, era 64 KB)
RAM = HEAP_BLOCK + 0x10         # i primi 12 byte li scrive l'inizializzazione dell'heap
SIZE = HEAP_BLOCK + HEAP_BLOCK_SIZE - RAM
IMG = 0x4034_9000               # flusso compresso accodato alla sezione 3

# Run-time buffers inside the area (offset from RAM, end, owner): not part of the image (the loader zeroes
# them), written by their mod while the OS runs. No other code or data may be linked there. TEST14 put
# master-comp v2 at +0xD800..+0xF940, on top of fx3's line: fx3 runs from power-on (VOL 100) and zeroed
# the end of mc_cv_wrap within two audio blocks; the next call hit 0x0000 (ori.b, illegal on ColdFire).
# TEST16 linked seqpages at +0x5800, on FM4's tables: FM4's init (0x444E9BB6, run by the OS's CC/NRPN table
# builder 0x400A5EC4 at boot) writes three 71-word position tables from the end of its blob (0x444EA0BC) to
# +0x5B40, which overwrote all six page hooks; opening KEYBOARD SETUP ran 0x00000035 at 0x444EA14C (V04).
RUNTIME = [
    (0x57EC, 0x5B40, "fm4: sound save/load and p-lock position tables, written by its init at boot (TEST16b)"),
    (0xD800, 0xDD80, "arp: run-time state ar_st (TEST16)"),
    (0xDD80, 0xDF30, "arpstore: arp step pattern, RAM copies ap_* (TEST16d)"),
    (0xDF30, 0xDF3C, "arp: arp step pattern positions ar_pidx (TEST16d)"),
    (0xDF3C, 0xDFD8, "patpage: knob step state of the OS routine 0x400F6A96, knobs A-F (TEST16d)"),
    (0xDFD8, 0xDFFC, "arpchord: chord notes 2..4 of the step just built, per track, ac_ofs (TEST17d)"),
    (0xDFFC, 0xF000, "fx3: feedback word (+0xDFFC) and delay line + copy (+0xE000, 2 x 1024 x s16)"),
]


# arpstore's arp step pattern in RAM (offset from RAM): zero at boot = the defaults (TEST16d)
AP = {"ap_len16": 0xDD80, "ap_flags": 0xDD8C, "ap_off": 0xDD98, "ap_ofs": 0xDDB0, "ap_rat": 0xDE70}
AP_END = 0xDF30
AR_PIDX = 0xDF30                 # arp: the pattern position per track (12 B)
AC_OFS = 0xDFD8                  # arpchord: 12 x 3 signed offsets (36 B), read by arp's ar_trig (TEST17d)
PP_ACC = 0xDF3C                  # patpage: the OS step routine's state (acc + 32 + 20 k, k = 0..5: 152 B)


def owner(who: str) -> str:
    """The mod that owns a RUNTIME region (the text before ':')."""
    return who.split(":")[0].strip()


def runtime_clash(start: int, end: int, absent=()) -> str | None:
    """Owner of the first run-time buffer that [start, end) (absolute RAM addresses) overlaps, else None.
    absent: mods not in the build; their regions are free (TEST19a: grid links code on fx3's delay line, and
    grid conflicts with fx3)."""
    for lo, hi, who in RUNTIME:
        if owner(who) in absent:
            continue
        if start < RAM + hi and RAM + lo < end:
            return who
    return None
