| master-filter: the audio hook and the page stub (Syntakt OS 1.41). See mf.c.
|
| mf_fx_hook replaces "jsr 0x40095E1C" at 0x400A4F9C in the audio interrupt (args: CV struct
| 0x80003160, copy of the live values 0x80006348). It edits the copy (mf_apply), calls the original
| routine with the same two arguments, then rewrites the resonance CV it set (mf_post) and returns to the
| interrupt. C: d0-d1/a0-a1 scratch, everything else preserved (as the OS routine), no EMAC. Each call gets
| its own copy of the arguments: the interrupt's are only read.

        .text

        .globl  mf_fx_hook
mf_fx_hook:                             | (sp) interrupt return, 4 CV struct, 8 copy
        move.l  8(%sp),-(%sp)           | the copy
        jsr     mf_apply
        addq.l  #4,%sp
        move.l  8(%sp),-(%sp)           | the copy
        move.l  8(%sp),-(%sp)           | the CV struct
        jsr     0x40095E1C              | the OS's FX filter CV routine: (CV struct, copy)
        addq.l  #8,%sp
        move.l  8(%sp),-(%sp)
        move.l  8(%sp),-(%sp)
        jsr     mf_post                 | (CV struct, copy): Polivoks resonance
        addq.l  #8,%sp
        rts
        .globl  mf_fx_hook_end
mf_fx_hook_end:

| TEST15: page 0 (the OS's NONE page, the FX SYN tab's second page): A FLTR, B TYPE, C FREQ, D RESO, E CMP,
| F IN (master-comp's meter), G RET (TEST15b), H empty; pages 12 (FX FLTR 2) and 19 (FX AMP 2) stay stock. Then
| the objects (mf_boot). Replaces "clr.l 0x41BA0730" (page 19 slot H) in the page table initializer at 0x40194D84,
| the last write of page 19's slots; page 0's slots (0x41BA03D0..0x41BA03EC) were cleared before it by the same
| initializer (0x401944dc..0x40194506).
        .globl  mf_page_stub
mf_page_stub:
        lea     -16(%sp),%sp
        movem.l %d0-%d1/%a0-%a1,(%sp)
        clr.l   0x41BA0730              | the replaced instruction: page 19 (FX AMP 2) H empty, stock
        move.l  #ID_ON,%d0              | TEST15: page 0 = SYN page 2: A FLTR
        move.l  %d0,0x41BA03D0
        move.l  #ID_TYPE,%d0            | B
        move.l  %d0,0x41BA03D4
        move.l  #ID_FREQ,%d0            | C
        move.l  %d0,0x41BA03D8
        move.l  #ID_RESO,%d0            | D
        move.l  %d0,0x41BA03DC
        move.l  #ID_CMP,%d0             | E
        move.l  %d0,0x41BA03E0
        move.l  #ID_IN,%d0              | F: master-comp's IN meter
        move.l  %d0,0x41BA03E4
        clr.l   0x41BA03E8              | G empty (TEST17; RET FLTR/KIT TEST15b..16: the returns always go through)
        jsr     mf_boot
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea     16(%sp),%sp
        rts

| MIDI in (see mf.c, MIDI): the table lookups of the OS's CC and NRPN handlers. Each is entered as the
| lookup it replaces: (sp) return into the handler, 4 track, 8 machine, 12 CC or NRPN number. The handler
| keeps the 7-bit value in d4 (CC: its value argument; NRPN: the 14-bit value >> 7) until after the lookup.
| Not ours (mf_midi_in = 0): jump to the OS's lookup with the stack and the callee-saved registers as the
| handler built them (the C call only uses d0-d1/a0-a1, as the lookup does). Ours: drop the return address
| and the three arguments and leave through the handler's own exit, as after a parameter change.
        .globl  mf_cc_lookup
mf_cc_lookup:                           | replaces "jsr 0x400A6796" at 0x4001C17A (CC handler 0x4001C12C)
        clr.l   -(%sp)                  | CC
        move.l  %d4,-(%sp)              | value
        move.l  20(%sp),-(%sp)          | number
        move.l  16(%sp),-(%sp)          | track
        jsr     mf_midi_in
        lea     16(%sp),%sp
        tst.l   %d0
        bne.s   1f
        jmp     0x400A6796              | the OS's CC lookup, returns to 0x4001C180
1:      lea     16(%sp),%sp
        jmp     0x4001C256              | handler exit (d0 = 1), as after its kit-parameter set

        .globl  mf_nrpn_lookup
mf_nrpn_lookup:                         | replaces "jsr 0x400A6816" at 0x4001C2B4 (NRPN handler 0x4001C262)
        moveq   #1,%d0
        move.l  %d0,-(%sp)              | NRPN
        move.l  %d4,-(%sp)              | value >> 7
        move.l  20(%sp),-(%sp)          | number (MSB << 7 | LSB)
        move.l  16(%sp),-(%sp)          | track
        jsr     mf_midi_in
        lea     16(%sp),%sp
        tst.l   %d0
        bne.s   1f
        jmp     0x400A6816              | the OS's NRPN lookup, returns to 0x4001C2BA
1:      lea     16(%sp),%sp
        moveq   #0,%d0                  | as after its kit-parameter set (clr.b %d0 at 0x4001C2F8)
        jmp     0x4001C418              | handler exit
