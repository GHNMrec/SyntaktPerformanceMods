| vparams — parametri "virtuali" per le mod: id logici nascosti che le mod leggono e scrivono
| a modo loro (stato in RAM, parole libere del kit...), al posto dell'OS.
|
| Agganci alle tre funzioni centrali dei parametri di kit (entrata: 4(sp) = oggetto, 8(sp) = id,
| 12(sp) = valore): "e' di kit?" 0x4000D870, lettura 0x4000D94A, scrittura 0x4000DA32.
| Per un id registrato in VP_TABLE: "di kit" = 1, lettura e scrittura saltano alle funzioni della
| mod con lo stesso stack; per gli altri id si riprende il codice originale.
| VP_TABLE: 32 voci da 12 byte {id.w, 0.w, lettura, scrittura}, scritte da ogni mod nel suo posto.
|
| v2 (midi-guard): ids MG_LO..MG_HI (246..269) are the MIDI machine's SRC / CC VALUE / CC SELECT ids,
| MG_X1/MG_X2 (445, 446) the IMPULSE machine's REP/NUM (v3: borrowed by beat-repeat for RPT2 and RPT),
| MG_X3..MG_X9 (443, 402, 406, 412, 442, 431, 432: IMPULSE SHP, three drum machines' COL, IMPULSE HOLD; NLEV and
| NDEC of a fourth: v5/v6/v7: master-filter).
| A registered one belongs to its mod only in the FX context. The context follows what the UI page views
| show: when is-kit (whose 12(sp) is the track) is called from one of the page-view sites in vp_sites,
| vp_ctx asks mg_ensure(0) for the FX track (12) or for the FX3 page (REVERB page 2, page 25, which the
| DELAY/REVERB tabs show whatever the active track: v4), mg_ensure(1) otherwise (the stock descriptors
| and objects become live). In the stock context is-kit, get and set let the OS handle those ids. Other
| callers (MIDI CC/NRPN input, FX routing code with a constant 12) never switch.

        .equ    VP_N,           32

        .text
        .globl  vp_kit, vp_get, vp_set

| d0 = id -> a1 = voce, oppure 0 (Z = 1). Usa d1, a1.
vp_find:
        lea     VP_TABLE,%a1
        moveq   #VP_N-1,%d1
1:      cmp.w   (%a1),%d0
        beq.s   2f
        lea     12(%a1),%a1
        subq.l  #1,%d1
        bge.s   1b
        suba.l  %a1,%a1
2:      move.l  %a1,%d1
        rts

| d0 = id -> Z = 0 for a borrowed id: MIDI machine pages (MG_LO..MG_HI) or MG_X1..MG_X9 (IMPULSE REP,
| NUM: beat-repeat; IMPULSE SHP, HOLD, three drum machines' COL and a fourth's NLEV/NDEC: master-filter). Uses d1.
vp_midi:
        .irp    x, MG_X1, MG_X2, MG_X3, MG_X4, MG_X5, MG_X6, MG_X7, MG_X8, MG_X9
        cmpi.l  #\x,%d0
        beq.s   2f
        .endr
        move.l  %d0,%d1
        subi.l  #MG_LO,%d1
        cmpi.l  #MG_HI-MG_LO,%d1
        bhi.s   1f
2:      moveq   #1,%d1
        rts
1:      moveq   #0,%d1
        rts

| Page views that call is-kit with the active track (return addresses, checked by make_patch.py), each
| with 1 when the calling page view is in a2 there: the ParameterPageView methods that every page view
| shares, the DELAY/REVERB tabs (FxPageView) included: get-value 0x40037E50, set-value 0x40037F9A, the
| generic 8-slot draw 0x4003A244 (fx3 sends page 25 there) and the encoder/trig helper 0x4003B4D2; their
| first argument (the view) is loaded into a2 and never changed before the call. 0: the view is not read
| (the AMP, FILTER, MASTER and LFO views never show page 25; the DELAY/REVERB draw 0x40042CE0 does not
| either, fx3 sends that page to the generic draw). Not listed: MIDI CC/NRPN input 0x4001C1B2/0x4001C2D4,
| FX routing 0x4004C020, 0x4004C054, 0x4004C088, 0x4004C6DA and the FX-track LFO 0x400F30F8 (constant
| track 12).
        .balign 4
vp_sites:
        .long   0x40037ED6, 1, 0x40038034, 1, 0x4003A3C4, 1, 0x4003B522, 1
        .long   0x40041F0A, 0, 0x40042416, 0, 0x400427B2, 0, 0x40043274, 0
        .long   0x40043D5A, 0, 0x400F372A, 0
        .equ    VP_NSITES, 10
        .equ    VP_FX3_PAGE, 25                 | REVERB page 2 (fx3)

| d0 = pointer -> Z = 1 for a 4-aligned DDR address (0x40000000..0x47FFFFFF). Uses d1.
vp_ddr:
        move.l  %d0,%d1
        andi.l  #0xF8000003,%d1
        cmpi.l  #0x40000000,%d1
        rts

| Context for a page-view call of is-kit: the mods' (0) on the FX track or when the calling view shows the
| FX3 page (page index = view.pages[view.pos]: vector begin +124, end +128, position +144, as the OS's
| own id-under-slot 0x40037D9E reads it), stock (1) otherwise.
| (sp) vp_kit, 4(sp) OS return, 16(sp) track. Returns d0 = 1 for a page-view call, 0 for any other caller
| (context left alone). Uses d0, d1, a0, a1.
vp_ctx:
        move.l  4(%sp),%d0
        lea     vp_sites,%a0
        moveq   #VP_NSITES-1,%d1
1:      cmp.l   (%a0)+,%d0
        beq.s   2f
        addq.l  #4,%a0
        subq.l  #1,%d1
        bge.s   1b
        moveq   #0,%d0                          | not a page view: leave the context alone
        rts
2:
        .ifdef  MG_FM4_VIEW                     | SY FM4 scope (midi-guard): every page-view is-kit
        move.l  %a0,-(%sp)
        move.l  16(%sp),-(%sp)                  | the id (vp_ctx's 12(sp); a0 pushed above)
        moveq   #0,%d0
        tst.l   (%a0)
        beq.s   3f                              | view not passed here: 0
        move.l  %a2,%d0                         | the page view
3:      move.l  %d0,-(%sp)
        jsr     MG_FM4_VIEW                     | (view or 0, id); C: d0, d1, a0, a1 clobbered
        addq.l  #8,%sp
        movea.l (%sp)+,%a0
        .endif
        moveq   #12,%d1
        cmp.l   16(%sp),%d1
        beq.s   5f                              | FX track: the mods' context
        tst.l   (%a0)
        beq.s   4f                              | view not read here: stock context
        move.l  %a2,%d0                         | the page view (checked before reading it)
        bsr.s   vp_ddr
        bne.s   4f
        movea.l %a2,%a1
        move.l  124(%a1),%d0                    | page vector begin
        bsr.s   vp_ddr
        bne.s   4f
        movea.l %d0,%a0
        move.l  128(%a1),%d0                    | end
        sub.l   %a0,%d0
        cmpi.l  #4*64,%d0
        bhi.s   4f                              | not a page vector (or end < begin)
        lsr.l   #2,%d0                          | number of pages
        move.l  144(%a1),%d1                    | position of the page on screen
        cmp.l   %d0,%d1
        bcc.s   4f                              | out of range (unsigned)
        moveq   #VP_FX3_PAGE,%d0
        cmp.l   (%a0,%d1.l*4),%d0
        beq.s   5f                              | FX3 page, any track: the mods' context
4:      moveq   #1,%d0                          | anything else: stock context
        bra.s   6f
5:      moveq   #0,%d0
6:      cmp.l   MG_CTX,%d0
        beq.s   7f
        move.l  %d0,-(%sp)
        jsr     MG_ENSURE                       | C: d0, d1, a0, a1 clobbered
        addq.l  #4,%sp
7:      moveq   #1,%d0
        rts

vp_kit:                                         | 0x4000D870: "parametro di kit?" (4 oggetto, 8 id, 12 traccia)
        bsr.w   vp_ctx
        movea.l %d0,%a0                         | 1: called by a page view (context set for it)
        move.l  8(%sp),%d0
        beq.s   9f                              | id 0: mai registrato (voci vuote)
        bsr.w   vp_find                         | (d1, a1)
        beq.s   9f
        bsr.w   vp_midi                         | (d1)
        beq.s   1f
        tst.l   MG_CTX
        bne.s   9f                              | stock context: the OS answers
        move.l  %a0,%d1
        bne.s   1f                              | page view in the mods' context (FX track or FX3 page)
        moveq   #12,%d1
        cmp.l   12(%sp),%d1
        bne.s   9f                              | other callers: a borrowed id is the mod's for the FX track only
1:      moveq   #1,%d0
        rts
9:      move.l  %d2,-(%sp)                      | istruzioni originali sostituite
        moveq   #124,%d2
        move.l  8(%sp),%d1
        jmp     0x4000D878

vp_get:                                         | 0x4000D94A: lettura
        move.l  8(%sp),%d0
        beq.s   9f
        bsr.w   vp_find
        beq.s   9f
        bsr.w   vp_midi
        beq.s   1f
        tst.l   MG_CTX
        bne.s   9f                              | stock context: the OS reads it
1:      movea.l 4(%a1),%a0
        jmp     (%a0)
9:      move.l  %d2,-(%sp)
        move.l  8(%sp),%d1
        jmp     0x4000D950

vp_set:                                         | 0x4000DA32: scrittura
        move.l  8(%sp),%d0
        beq.s   9f
        bsr.w   vp_find
        beq.s   9f
        bsr.w   vp_midi
        beq.s   1f
        tst.l   MG_CTX
        bne.s   9f                              | stock context: the OS writes it
1:      movea.l 8(%a1),%a0
        jmp     (%a0)
9:      move.l  %d3,-(%sp)
        move.l  %d2,-(%sp)
        move.l  12(%sp),%d1
        jmp     0x4000DA3A
