/* midi-guard (Syntakt OS 1.41): keep the mods' controls off the MIDI machine's pages.
 *
 * fx3 (ids 246-253), master-comp (262-268), beat-repeat (269, 445, 446) and master-filter (443, 402, 406,
 * 412) reuse the logical ids of the MIDI machine's SRC page (CHAN BANK PROG PB AT MW BC SBNK) and CC SELECT
 * page (SEL1-SEL8), of the IMPULSE machine's REP, NUM and SHP, and of three drum machines' COL. The Syntakt shows those pages on tracks set to those machines. Descriptors (names, ranges) and per-parameter
 * objects (encoder type, value prototype, formatter, graphic, style) are global per id, and vparams sent
 * every read/write of those ids to the mods, whatever the track.
 *
 * Two contexts:
 *   0 = FX     the FX track (12) is being edited, or the FX3 page (REVERB page 2) is on screen from any
 *              track: the mods' versions are live, exactly as before;
 *   1 = MIDI   anything else: the stock descriptors and objects are live and vparams lets the OS
 *              handle the ids (stock is-kit, get and set).
 * The context follows what the UI page views show: they all call is-kit (0x4000D870) with the project's
 * active track (view +116 = project + 48) before every read or write of a slot, and vparams calls
 * mg_ensure() from there (page-view call sites only, see vp_sites in vparams.S; vparams v4 also reads the
 * page on screen), so any page of a MIDI track (SRC, CC SELECT, LFO destinations...) sees the stock names. Switching exchanges
 * the words that differ with a shadow copy, so every std::function keeps
 * exactly one owner. The stock objects are built once, the first time the MIDI context is needed, as
 * the static initializer builds them: encoder type, 16-byte value prototype copied from the image,
 * formatter/graphic/style copy-constructed (manager clone) from the OS prototypes. The recipe comes
 * from emulating the stock initializer (make_patch.py). UI code only: no interrupt calls is-kit with
 * these ids, and no formatter, graphic or style of these ids calls is-kit (no swap while one runs).
 */

typedef unsigned int u32;

#define DATA __attribute__((section(".data")))

#include "mg_tables.h"   /* NID, mg_ids[], MG_DESC_STOCK, mg_recipe[][5] (generated) */

#define DESC(id)  ((u32 *)(0x4022D83Cu + 52u * (u32)(id)))     /* parameter descriptor */
#define OBJ(id)   ((u32 *)(0x41BA0A24u + 84u * (u32)(id)))     /* per-parameter object */
#define UI_ROOT   (*(char *const volatile *)0x444E2334u)
#define FN_COPY   ((void (*)(void *, const void *))0x40188482u) /* std::function copy constructor */

u32 mg_ctx DATA = 0;                         /* 0: mods live (FX track), 1: stock live (MIDI tracks) */
u32 mg_swaps DATA = 0;                       /* number of context switches (diagnostics) */
u32 mg_built DATA = 0;                       /* stock shadow objects built */
static u32 dsh[NID][5] DATA = MG_DESC_STOCK; /* shadow descriptor words (stock until the first switch) */
static u32 osh[NID][17] DATA = {{0}};        /* shadow object words (stock once built) */

/* descriptor words that differ: min, max, default, long name, short name */
static const unsigned char DW[5] = {2, 3, 4, 10, 12};
/* object words that differ: type, value prototype (4), formatter (4), graphic (4), style (4).
 * +52 (words 13-16) is the same prototype in both versions and stays put. */
static const unsigned char OW[17] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 17, 18, 19, 20};

static void build(void)
{
    u32 i, k;

    for (i = 0; i < NID; i++) {
        u32 *s = osh[i];
        const u32 *pod = (const u32 *)mg_recipe[i][1];

        s[0] = mg_recipe[i][0];
        for (k = 0; k < 4; k++)
            s[1 + k] = pod[k];
        FN_COPY(s + 5, (const void *)mg_recipe[i][2]);
        FN_COPY(s + 9, (const void *)mg_recipe[i][3]);
        if (mg_recipe[i][4])                 /* 0: no style, the std::function stays empty (zeros) */
            FN_COPY(s + 13, (const void *)mg_recipe[i][4]);
    }
}

static void swap(void)
{
    u32 i, k, t;

    for (i = 0; i < NID; i++) {
        u32 *d = DESC(mg_ids[i]), *o = OBJ(mg_ids[i]);

        for (k = 0; k < 5; k++) {
            t = d[DW[k]];
            d[DW[k]] = dsh[i][k];
            dsh[i][k] = t;
        }
        for (k = 0; k < 17; k++) {
            t = o[OW[k]];
            o[OW[k]] = osh[i][k];
            osh[i][k] = t;
        }
    }
}

void mg_ensure(u32 want)
{
    char *ui;

    if (want == mg_ctx)
        return;
    if (want && !mg_built) {
        build();
        mg_built = 1;
    }
    swap();
    mg_ctx = want;
    mg_swaps++;
    ui = UI_ROOT;
    if (ui)
        ui[96] = 1;                          /* redraw the page with the right names */
}

#ifdef MG_FM4
/* ---- SY FM4 scope (mods/fm4, Syntakt MAX Modular Builder RC2's port of Rxuting's SY FM4).
 *
 * FM4's page 2 (SY TONE's second SYN page: a SourcePageView at position 1, its slots from FM4's slot-id
 * function) uses the ids 254-261, which everywhere else are the MIDI machine's CC VALUE knobs VAL1-VAL8
 * (page 28). Their descriptors and objects stay the stock ones. While FM4's page 2 is on screen they are
 * exchanged with FM4's (mg_fm4_ensure(1)): RC2's descriptor rows (fm4_rows, from mods/fm4) and objects copied
 * from FM4's SY TONE donors exactly as FM4's own page-2 setup (0x444E999C) would copy them over the VAL objects
 * (mods/fm4 presets FM4's flag so it never does). Any other page view puts the stock ones back (0). Decided:
 *   - at the generic page draw 0x4003A244 (mg_draw_hook), before any slot is read: FM4 for a SourcePageView
 *     whose slot A is one of the ids (its slot-id function, as the draw then asks), stock otherwise;
 *   - at every page-view is-kit call (vparams vp_ctx): FM4 for one of the ids from a SourcePageView (view in
 *     a2), stock from any other view (the MIDI machine's pages) and from the views whose is-kit call does not
 *     pass the view (AMP, FILTER, LFO, MASTER: none shows FM4's page); a SourcePageView asking about another
 *     id leaves the choice to the next draw (no switching back and forth within FM4's page).
 * So FM4's rows are live only while FM4's page 2 is the page on screen.
 * The OS's CC/NRPN tables are built at boot from the stock rows (stock: CC 70-77 -> VAL1-VAL8 on MIDI tracks,
 * no NRPN; FM4's own keys never registered, as in RC2). While FM4's rows are live the OS's CC and NRPN lookups
 * (0x400A6796, 0x400A6816) report no parameter for those ids (mg_cc_filter, mg_nrpn_filter): such a message
 * for a MIDI track is ignored then, rather than written to FM4's keys. Swaps from UI code only (as above). */
#define SRCVIEW_VT 0x401CA37Cu                                  /* SourcePageView: the machines' SYN pages */
#define FM4_LO     254u
#define NF         8

u32 mg_fm4 DATA = 0;                         /* 0: stock rows/objects live for 254-261, 1: FM4's */
u32 mg_fm4_built DATA = 0;                   /* FM4's objects built (shadow) */
u32 mg_fm4_swaps DATA = 0;                   /* switches (diagnostics) */
u32 mg_fm4_drops DATA = 0;                   /* MIDI lookups suppressed while FM4's rows were live */
static u32 fsh_d[NF][13] DATA = FM4_ROWS;    /* the rows not live: FM4's while stock is live, and back */
static u32 fsh_o[NF][21] DATA = {{0}};       /* the objects not live (words 0-20: type, prototype, 4 functions) */
static const unsigned short fm4_donor[NF] = FM4_DONORS;

static void fm4_build(void)
{
    u32 i, k;

    for (i = 0; i < NF; i++) {
        const u32 *src = OBJ(fm4_donor[i]);
        u32 *s = fsh_o[i];

        for (k = 0; k < 5; k++)
            s[k] = src[k];                   /* encoder type, value prototype */
        for (k = 5; k < 21; k += 4)
            FN_COPY(s + k, src + k);         /* formatter, graphic, +52, style */
    }
}

void mg_fm4_ensure(u32 want)
{
    u32 i, k, t;
    char *ui;

    if (want == mg_fm4)
        return;
    if (want && !mg_fm4_built) {
        fm4_build();
        mg_fm4_built = 1;
    }
    if (want)
        mg_fm4 = 1;                          /* the MIDI lookups stop before the first FM4 word goes live */
    for (i = 0; i < NF; i++) {
        u32 *d = DESC(FM4_LO + i), *o = OBJ(FM4_LO + i);

        for (k = 0; k < 13; k++) {
            t = d[k];
            d[k] = fsh_d[i][k];
            fsh_d[i][k] = t;
        }
        for (k = 0; k < 21; k++) {
            t = o[k];
            o[k] = fsh_o[i][k];
            fsh_o[i][k] = t;
        }
    }
    mg_fm4 = want;                           /* ... and resume after the last stock word is back */
    mg_fm4_swaps++;
    ui = UI_ROOT;
    if (ui)
        ui[96] = 1;
}

static u32 is_view(const u32 *v)                /* a 4-aligned DDR pointer to a SourcePageView */
{
    u32 a = (u32)v;

    return (a & 0xF8000003u) == 0x40000000u && v[0] == SRCVIEW_VT;
}

/* the view the generic page draw is about to draw */
void mg_fm4_draw(const u32 *view)
{
    u32 want = 0;

    if (is_view(view)) {
        u32 (*slot_id)(const u32 *, u32) = (u32 (*)(const u32 *, u32))((const u32 *)SRCVIEW_VT)[188 / 4];

        want = slot_id(view, 0) - FM4_LO < NF;
    }
    mg_fm4_ensure(want);
}

/* is-kit from a page view (vparams): view = the view where the site has it in a2, else 0 */
void mg_fm4_view(const u32 *view, u32 id)
{
    if (!is_view(view))
        mg_fm4_ensure(0);
    else if (id - FM4_LO < NF)
        mg_fm4_ensure(1);
}

__asm__(
"        .text\n"
"        .globl  mg_draw_hook\n"
"mg_draw_hook:\n"                               /* replaces "lea -80(%sp),%sp; movem.l" at 0x4003A244 */
"        lea     -16(%sp),%sp\n"
"        movem.l %d0-%d1/%a0-%a1,(%sp)\n"
"        move.l  20(%sp),-(%sp)\n"              /* the view */
"        jsr     mg_fm4_draw\n"
"        addq.l  #4,%sp\n"
"        movem.l (%sp),%d0-%d1/%a0-%a1\n"
"        lea     16(%sp),%sp\n"
"        lea     -80(%sp),%sp\n"                /* the replaced prologue */
"        movem.l %d2-%d7/%a2-%a6,(%sp)\n"
"        jmp     0x4003A24C\n"
"\n"
"        .globl  mg_cc_filter\n"
"mg_cc_filter:\n"                               /* replaces the first 6 bytes of the OS's CC lookup 0x400A6796 */
"        move.l  12(%sp),-(%sp)\n"              /* (track, machine, number) again */
"        move.l  12(%sp),-(%sp)\n"
"        move.l  12(%sp),-(%sp)\n"
"        bsr.s   1f\n"
"        lea     12(%sp),%sp\n"
"        bra.s   mg_lookup_filter\n"
"1:      move.l  %a2,-(%sp)\n"                  /* the replaced instructions */
"        move.l  %d2,-(%sp)\n"
"        moveq   #127,%d2\n"
"        jmp     0x400A679C\n"
"\n"
"        .globl  mg_nrpn_filter\n"
"mg_nrpn_filter:\n"                             /* replaces the first 8 bytes of the OS's NRPN lookup 0x400A6816 */
"        move.l  12(%sp),-(%sp)\n"
"        move.l  12(%sp),-(%sp)\n"
"        move.l  12(%sp),-(%sp)\n"
"        bsr.s   2f\n"
"        lea     12(%sp),%sp\n"
"        bra.s   mg_lookup_filter\n"
"2:      move.l  %a2,-(%sp)\n"
"        move.l  %d2,-(%sp)\n"
"        move.l  12(%sp),%d1\n"
"        jmp     0x400A681E\n"
"\n"
"mg_lookup_filter:\n"                           /* d0 = the OS lookup's id; d1 is scratch there too */
"        tst.l   mg_fm4\n"
"        beq.s   9f\n"
"        move.l  %d0,%d1\n"
"        subi.l  #254,%d1\n"
"        cmpi.l  #7,%d1\n"
"        bhi.s   9f\n"
"        moveq   #0,%d0\n"                      /* FM4's rows live: no MIDI parameter for 254-261 */
"        addq.l  #1,mg_fm4_drops\n"
"9:      rts\n"
);
#endif
