/* master-filter: analog master filter (Syntakt OS 1.41).
 *
 * The analog FX block (filter, overdrive, VCA) becomes the master filter. While its switch is ON, every
 * audio block, the OS's own control-voltage and mix routines get the live parameter values with:
 *   - tracks 1-12, the delay and reverb returns (RET FLTR, the default) and the external input routed through
 *     the FX block (a track or return taken off the main mix in the routing settings keeps its own routing:
 *     through the FX block it would reach the main again);
 *   - the FX block's filter TYPE, FREQ and RESO set from the master filter's knobs, the filter envelope depth
 *     at 0 and the filter pan centred (FX-track trigs, p-locks and LFOs do not move them); the FX DRIVE stays
 *     the kit's.
 * The FX AMP page (VOL, PAN, envelope and ducking, DEL/REV sends) stays the kit's: FX-track trigs can
 * still duck everything. While a return goes through the FX block the OS itself mutes the FX block's
 * send to that effect (no feedback loop, 0x4008F672). TEST15b: RET KIT leaves the delay and reverb returns
 * where the kit routes them (the FX block's sends work again for a return routed direct); and while the delay's
 * return goes through the FX block, the FX AMP DEL word of the copy is 0 (that send is muted anyway): the OS's
 * loop guard (0x4008F838) would otherwise cut the delay's REV send (delay into reverb) whenever FX AMP DEL > 0.
 *
 * Where: the audio interrupt (0x400A3856) rebuilds a copy of the live values every block
 * (0x40097952: one-pole smoothing of the kit/engine words at 0x800021B0 into 0x80006348), applies the
 * LFOs and modifiers to it, then hands it to the routines that program the analog hardware and the
 * mix. mf_fx_hook replaces the call of the first of them (0x40095DA4, FX filter CVs, at 0x400A4F24): it
 * edits that copy before it (mf_apply) and the resonance CV it wrote after it (mf_post, "Polivoks resonance"
 * below). The copy is rebuilt from scratch the next block (the OS keeps its smoothing state elsewhere,
 * 0x8000E9B0): the kit, the pattern and the live values are never written. Switch OFF: the next block plays the
 * kit's routing and FX settings again; FREQ, RESO, ENV and FPAN glide back to them (at most 256 blocks, 0.17 s).
 *
 * Controls (TEST15): FX track, SYN page 2 (page 0, the OS's unused NONE page, made the SYN tab's second page):
 * A FLTR, B TYPE, C FREQ, D RESO, E CMP, F IN (master-comp's input meter), G RET (TEST15b). FLTR page 2 and AMP
 * page 2 are stock again. TRIM is LVL, on SYN page 1 H (master-comp's BOUM-style page). The FX DRIVE is always the
 * kit's (SYN page 1 A): DRV (KIT or 1..127) lost its knob in TEST15 and its code in TEST15b, where its id became
 * RET; CC 14 / NRPN 1:52 are the OS's. Up to TEST14c: FLTR page 2 (page 12):
 * A DEL (stock), B FLTR, C TYPE, D FREQ, E FPAN (stock), F RESO, G DRV, H FENR; AMP page 2 (page 19): A TRIM, B CMP:
 *   FLTR  OFF / ON   the master filter's switch (looks and turns like AENR); TYPE can be chosen while OFF
 *   TYPE  LP4 / LP2 / BP2 / HP2 / NO1 / NO2 / LPN (the FX filter's own icons) / THRU (text: through the FX
 *         block with the FX filter's own OFF type, FREQ held at 127 and RESO at 0: drive and VCA only)
 *   FREQ  0 .. 127   (the FX block's FREQ scale), shown in Hz: about 6 Hz .. 20 kHz, 1.1 semitones per step,
 *         from cutoffs measured on the device (make_patch.py, MEASURED; units differ slightly)
 *   RESO  0 .. 127   0..63 as the FX filter's own RESO, 63..127 a straight climb past its maximum (mf_post)
 *   RET   FLTR / KIT (TEST15b, id 412, DRV's up to TEST15): FLTR (default) the delay and reverb returns go through
 *         the master filter with everything else (the FX AMP DEL/REV sends are then muted by the OS: a return
 *         through the FX block sent back to its own effect would loop); KIT they stay where the kit routes them
 *         (FX ROUTING on the DELAY/REVERB pages): a return routed direct skips the filter and keeps the FX block's
 *         send to it. FX3's return goes into the FX block whatever RET says (fx3 adds it to the FX bus 0x8000DAD0).
 *   TRIM  (LVL, TEST15) -12.0 .. +11.8 dB (0.1875 dB per step, 64 = 0 dB): the output level of the whole BOUM-style
 *         chain, filter ON or OFF (mf_post_gain, applied by master-comp with its gain: on every path to the main in
 *         CMP MAIN, on the FX block in FX). Up to TEST14c: the FX block's output level while the filter was ON.
 *   CMP   MAIN / FX: what master-comp compresses (mf_p[P_CMP], read by master-comp): MAIN (default) the whole
 *         main mix, FX only what goes through the FX block (the compressor up to TEST13)
 * Knob moves glide (one-pole, ~21 ms, like the OS's own smoothing); switching on jumps straight to the
 * master values (TRIM glides). The ids are the IMPULSE machine's HOLD (442) and SHP (443), the COL knobs of three
 * drum machines (402, 406, 412) and NLEV/NDEC of a fourth (431, 432): no MIDI CC/NRPN, not LFO destinations, only
 * on those machines' SYN pages. vparams + midi-guard make them ours on the FX track; those machines' pages keep
 * their stock knobs.
 * Values live in RAM (global, not saved with the kit: the FX block of the kit has no free word left).
 *
 * MIDI (FX CONTROL CH, see "MIDI" below): FLTR CC 3, TYPE CC 9, FREQ CC 12, RESO CC 13, NRPN 1:48..1:51 in the
 * same order (TEST15: DRV's CC 14 / NRPN 1:52 are gone, the OS handles them as stock). In: FLTR 0-63 OFF, 64-127
 * ON; TYPE 0-15 LP4, 16-31 LP2 ... 112-127 THRU; the others 0-127. Out (knob turns, like the stock knobs): FLTR
 * 0/127, TYPE 0 18 36 54 73 91 109 127, the others 0-127. TRIM (LVL), CMP and RET: no MIDI numbers.
 *
 * Cost: a few instructions per block with the switch OFF, ~280 on plus ~70 for mf_post. No audio processing, no EMAC.
 */

typedef unsigned int u32;
typedef int s32;
typedef unsigned short u16;
typedef short s16;
typedef unsigned char u8;

#define DATA __attribute__((section(".data")))

#include "mf_tables.h"          /* FREQ_TXT[128][6]: FREQ in Hz, measured on the device; TRIM_Q12[128], TRIM_TXT[128][6]
                                   (make_patch.py) */

#define UI_ROOT   (*(char *const volatile *)0x444E1334u) /* redraw flag at +96 */
#define OBJ(id)   ((u32 *)(0x41B9FA24u + 84u * (u32)(id)))
#define POD_DISC  ((const u32 *)0x401D68D4u)             /* discrete value prototype (443, 93, 115) */
#define DRAW_TEXT ((void (*)(void *, const void *, s32, s32, s32, s32, const char *, const char *, ...)) \
                   0x400F8C18u)                          /* (ctx, font, x, y, centred, 0, mask, fmt, ...) */
#define FONT      ((const void *)0x402A91C0u)            /* 4x6 */
/* stock graphic of the FX filter TYPE (id 135, FLTR page 1 slot G): draws frame value >> 8 of the 21 x 17 icon
 * strip at 0x444E100C (LP4 LP2 BP HP N 2N LPN OFF) at x, y; it does not use its std::function argument */
#define FX_TYPE_GFX ((void (*)(const void *, s32, void *, s32, s32))0x40070B10u)
#define FN_COPY   ((void (*)(void *, const void *))0x401882BEu)   /* std::function copy constructor */
#define ID_AENR   157                                    /* FX AMP envelope reset: the switch looks like it */

/* route-to-main masks (bit set = off the main mix): 0..11 tracks, 12 delay, 13 reverb, 14 FX block.
 * The kit's word, or the global one when its bit 15 is set ("use global setting"), as the mix
 * (0x4008F1DE) and the CV routine (0x4009083C) read them. */
#define TO_MAIN_KIT    (*(volatile const s16 *)0x80003148u)
#define TO_MAIN_GLOBAL (*(volatile const s16 *)0x8000314Cu)

/* byte offsets in the copy of the live values (= engine block layout: track t at 142 t, words 28 + 2 iid) */
#define W(off)    ((off) / 2)
#define ROUT(t)   (142 * (t) + 126)                      /* id 82  Pre/Post FX, 0 = through the FX block */
#define OFF_DEL   1782                                   /* id 115 Delay FX Routing, 0 = through */
#define OFF_REV   1800                                   /* id 124 Reverb FX Routing */
#define OFF_IN    1818                                   /* id 132 In FX Routing */
#define OFF_TYPE  1820                                   /* id 135 FX filter type 0..7 (<< 8), 7 = OFF */
#define OFF_FREQ  1822                                   /* id 133 */
#define OFF_RESO  1824                                   /* id 134 */
#define OFF_ENV   1826                                   /* id 136 envelope depth, 0x4000 = 0 */
#define OFF_FPAN  1840                                   /* id 143 filter pan, 0x4000 = centre */
#define OFF_FXDEL 1858                                   /* FX AMP DEL: the FX block's send to the delay (0x4008F678,
                                                            used only while the delay's return goes direct) */

/* P_TYPE .. P_ON have MIDI numbers (NP_MIDI, RET excepted); P_TRIM and P_CMP don't. P_CMP's position (6) is the
 * byte master-comp reads (make_patch.py exports mf_p + P_CMP as mf_cmp). P_RET (3) was DRV's up to TEST15. */
enum { P_TYPE, P_FREQ, P_RESO, P_RET, P_ON, NP_MIDI, P_TRIM = NP_MIDI, P_CMP, NP };
enum { T_LP4, T_LP2, T_BP2, T_HP2, T_NO1, T_NO2, T_LPN, T_THRU, NT };   /* = FX filter types, THRU = its OFF */
enum { S_FREQ, S_RESO, S_ENV, S_FPAN, NS };
enum { M_OFF, M_ON };                                    /* mf_mode (TEST17g: no glide back) */
enum { RET_FLTR, RET_KIT };                              /* P_RET */
#define TRIM_ZERO   64                                   /* TRIM knob at 0 dB */
#define POST_UNITY  4096                                 /* mf_post_gain: Q12 */

static const u16 s_off[NS] = {OFF_FREQ, OFF_RESO, OFF_ENV, OFF_FPAN};

u8 mf_p[NP] DATA = {T_LP4, 127, 0, RET_FLTR, 0, TRIM_ZERO, 0};  /* knob values: TYPE 0..7, RET / ON / CMP 0/1,
                                                                    the others 0..127 */
u8 mf_mode DATA = M_OFF;                 /* off, on, gliding back to the kit's values */
u16 mf_back DATA = 0;                    /* unused since TEST17g (kept: symbol list) */
s32 mf_s[NS] DATA = {0};                 /* smoothed FREQ RESO ENV FPAN, value << 16 */
u32 mf_blocks DATA = 0;                  /* blocks with the master filter on (diagnostics) */
/* TRIM (LVL): Q12 gain read by master-comp every block after this function ran (same audio block):
 * TRIM_Q12[TRIM], filter ON or OFF (TEST15; up to TEST14c unity while OFF), gliding (one-pole, 1/32 per block) */
u32 mf_post_gain DATA = POST_UNITY;
s32 mf_post_s DATA = POST_UNITY << 8;    /* the glide, Q12 << 8 */

/* one-pole glide toward t (0..0x7FFF), 1/32 per block (time constant ~21 ms, as the OS's smoothing);
 * snaps when closer than 16 (1/16 of a knob step), so a full-range move ends within ~240 blocks */
static s32 glide(s32 s, s32 t)
{
    s32 d = (t << 16) - s;

    if (d < (16 << 16) && d > -(16 << 16))
        return t << 16;
    return s + (d >> 5);
}

static u32 val(s32 s)
{
    return (u32)(s + 0x8000) >> 16;
}

/* TRIM: one-pole glide of mf_post_gain toward target (Q12), 1/32 per block, snapping within 1/256 of a unit */
static void post_glide(u32 target)
{
    s32 t = (s32)target << 8, d = t - mf_post_s;

    if (!d)
        return;                                         /* there already (every block since TEST15: keep it cheap) */
    mf_post_s = d < 256 && d > -256 ? t : mf_post_s + (d >> 5);
    mf_post_gain = (u32)(mf_post_s + 128) >> 8;
}

/* the master filter's work of one block (mf_apply: while it is ON or gliding back) */
static void __attribute__((noinline)) filter_block(u16 *c)
{
    u32 type = mf_p[P_TYPE], on = mf_p[P_ON], k, t;
    s32 m = TO_MAIN_KIT, tg[NS];

    if (m < 0)
        m = TO_MAIN_GLOBAL;
    if (type >= NT)
        type = T_THRU;
    if (m & 0x4000)
        on = 0;                                         /* FX block off the main mix: it would mute all */
    if (!on) {                                          /* TEST17g (the author: OFF dipped the loop): back to the */
        mf_mode = M_OFF;                                /* kit's FREQ RESO ENV FPAN in the same block as its */
        return;                                         /* routing and TYPE (up to TEST17f they glided back, */
    }                                                   /* the kit's TYPE meanwhile at the master's cutoff) */
    tg[S_FREQ] = type == T_THRU ? 0x7F00 : (s32)mf_p[P_FREQ] << 8;  /* THRU: the FX filter's OFF, held */
    tg[S_RESO] = type == T_THRU ? 0 : (s32)mf_p[P_RESO] << 8;          /* fully open with no resonance */
    tg[S_ENV] = 0x4000;
    tg[S_FPAN] = 0x4000;
    for (k = 0; k < NS; k++) {
        s32 x = tg[k];

        mf_s[k] = mf_mode == M_OFF ? x << 16 : glide(mf_s[k], x);
        c[W(s_off[k])] = (u16)val(mf_s[k]);
    }
    for (t = 0; t < 12; t++)
        if (!(m & (1 << t)))
            c[W(ROUT(t))] = 0;
    if (!(m & 0x1000))                                  /* the returns through the master filter too: always since */
        c[W(OFF_DEL)] = 0;                              /* TEST17 (the author: a true end-of-chain filter; RET left the */
    if (!(m & 0x2000))                                  /* page, its id 412 stays registered but unused) */
        c[W(OFF_REV)] = 0;
    if (!c[W(OFF_DEL)])                                 /* delay return in the FX block: the OS mutes the FX block's */
        c[W(OFF_FXDEL)] = 0;                            /* send to the delay; the word would only cut delay -> reverb */
    c[W(OFF_IN)] = 0;
    c[W(OFF_TYPE)] = (u16)(type << 8);                  /* THRU = 7 = the FX filter's OFF */
    mf_mode = M_ON;
    mf_blocks++;
}

/* c: the audio interrupt's copy of the live values, just before the FX filter CV routine reads it */
void mf_apply(u16 *c)
{
    u32 was = mf_mode, g;

    if (mf_p[P_ON] || mf_mode != M_OFF)                 /* OFF and settled: nothing else to do */
        filter_block(c);
    g = mf_mode == M_ON ? TRIM_Q12[mf_p[P_TRIM] & 127] : POST_UNITY;  /* TEST17g: LVL is the filter-ON trim */
    if (was != mf_mode) {                               /* (author): it switches with the routing, */
        mf_post_s = (s32)g << 8;                        /* knob moves glide */
        mf_post_gain = g;
    } else
        post_glide(g);
}

/* ---- Polivoks resonance. The OS's FX filter CV routine 0x40095DA4 sets the resonance CV (CV struct +78,
 * higher = more resonance) from a 128-word table per filter type, indexed by RESO >> 8, minus a cutoff
 * compensation indexed by FREQ >> 8 (0x40249A18: 0 up to the mids, up to 399 at the top), on units whose
 * calibration block says so ((0x43BDC044 & 31) >= 2, 0x40095ED2; the others get 0x7E6F - RESO and are left
 * alone). Those tables flatten out at the top: RESO 64..127 covers 16 % of their range (LP2: -31 .. 930 of
 * -5000 .. 930), so the top half of the knob barely changes the sound. With the master filter on, mf_post
 * (after the OS routine, same arguments) writes that CV again from the same tables:
 *   RESO 0 .. 63    the table (interpolated between its steps: the knob glide stays smooth)
 *   RESO 63 .. 127  a straight line from table[63] to table[127] + PUSH, PUSH = the type's table range >> 2
 *                   (LP2 +1482, LP4 +568): the stock maximum is passed around RESO 90, the rest of the knob
 *                   pushes the feedback past it into self-oscillation, as a Polivoks filter screams
 * minus the OS's cutoff compensation. Nothing else in the CV struct changes. THRU, switch OFF and the glide
 * back keep the OS's value. MF_PUSH_SHIFT 1 (make_patch.py MF_PUSH=hot) doubles PUSH. */
#define CV_RESO    78                                    /* byte offset of the FX filter resonance CV */
#define HW_CAL     (*(volatile const u8 *)0x43BDC044u)   /* & 31 >= 2: table resonance */
#define FREQ_COMP  ((const s16 *)0x40249A18u)            /* per FREQ >> 8, subtracted (0x40095F74) */
#define KNEE       63                                    /* (127 - KNEE) << 8 = 1 << 14 */
#ifndef MF_PUSH_SHIFT
#define MF_PUSH_SHIFT 2
#endif
static const u32 reso_tab[T_THRU] = {0x40249E18u, 0x40249D18u, 0x40249C18u, 0x40249B18u,    /* LP4 LP2 BP2 HP2 */
                                     0x40249918u, 0x40249818u, 0x40249718u};             /* NO1 NO2 LPN */

u32 mf_posts DATA = 0;                  /* blocks with the resonance CV rewritten (diagnostics) */

/* r: RESO word of the copy, 0 .. 0x7F00 */
s32 mf_reso_cv(u32 type, s32 r)
{
    const s16 *t = (const s16 *)reso_tab[type];
    s32 i = r >> 8, f = r & 0xFF, top;

    if (i < KNEE)
        return t[i] + (((t[i + 1] - t[i]) * f) >> 8);
    top = t[127] + ((t[127] - t[0]) >> MF_PUSH_SHIFT);
    return t[KNEE] + (((top - t[KNEE]) * (r - (KNEE << 8))) >> 14);
}

/* cv: the CV struct (0x80003160), c: the copy mf_apply edited, both as the OS routine just used them */
void mf_post(char *cv, const u16 *c)
{
    u32 type = c[W(OFF_TYPE)] >> 8, fi = c[W(OFF_FREQ)] >> 8;
    s32 r = (s16)c[W(OFF_RESO)], v;

    if (mf_mode != M_ON || type >= T_THRU || (HW_CAL & 31) <= 1)
        return;
    if (r < 0)
        r = 0;
    if (r > 0x7F00)
        r = 0x7F00;
    if (fi > 127)
        fi = 127;
    v = mf_reso_cv(type, r) - FREQ_COMP[fi];
    *(s16 *)(cv + CV_RESO) = (s16)(v < -32768 ? -32768 : v > 32767 ? 32767 : v);
    mf_posts++;
}

/* ---- parameters (vparams: the OS's kit get/set stack layout) */

static u32 slot(s32 id)
{
    return id == ID_TYPE ? P_TYPE : id == ID_FREQ ? P_FREQ : id == ID_RESO ? P_RESO : id == ID_ON ? P_ON :
           id == ID_TRIM ? P_TRIM : id == ID_CMP ? P_CMP : P_RET;
}

s32 mf_get(void *obj, s32 id)
{
    (void)obj;
    return (s32)mf_p[slot(id)] << 8;
}

static void redraw(void)
{
    char *ui = UI_ROOT;

    if (ui)
        ui[96] = 1;                                     /* redraw now, as the OS setters do */
}

/* ---- MIDI. The OS maps incoming CC/NRPN numbers to parameters with tables it builds once at boot from the
 * descriptors (0x400A5E4C); our borrowed ids have no numbers there, and the FX channel's CC 3, 9, 12, 13 and
 * NRPN 1:48..1:51 map to nothing. mf_cc_lookup / mf_nrpn_lookup (mf_hook.S) wrap the table lookups of the CC
 * handler 0x4001C12C and the NRPN handler 0x4001C262: for the FX track (12) and those numbers mf_midi_in sets the
 * knob and the handler ends as after a parameter change; every other message goes on to the OS's lookup
 * unchanged. Knob turns on SYN page 2 send the same numbers the way the OS sends a stock knob (0x4001316C):
 * only with ENCODER DEST = INT+EXT, on the channel the OS picks (0x40013298: AUTO CHANNEL, or with OUTPUT CH =
 * TRK CH the active track's channel, the FX CONTROL CH on the FX track; OFF sends nothing), CC or NRPN as
 * PARAM OUTPUT says, through the OS's senders. Incoming messages are not sent back out. */

#define FX_TRACK   12
#define NRPN_MSB   1
static const u8 midi_cc[NP_MIDI] = {9, 12, 13, 0, 3};      /* P_TYPE P_FREQ P_RESO P_RET P_ON (RET, TRIM, CMP:
                                                              none; DRV's old CC 14 / NRPN 1:52 are the OS's) */
static const u8 midi_nrpn[NP_MIDI] = {49, 50, 51, 0, 48};  /* LSBs, MSB 1 */
static const u8 type_out[NT] = {0, 18, 36, 54, 73, 91, 109, 127};   /* round(type * 127 / 7): v >> 4 = type */

#define PROJECT    ((u32 (*)(void))0x4016E804u)            /* project object (in d0: declared as an integer,
                                                              GCC would read a pointer result from a0) */
#define ENC_DEST   ((s32 (*)(void *))0x4002151Eu)          /* ENCODER DEST: 0 INT, 1 INT+EXT */
#define PARAM_OUT  ((s32 (*)(void *))0x4002149Au)          /* PARAM OUTPUT: 0 NRPN, 1 CC */
#define OUT_CHAN   ((s32 (*)(void))0x40013298u)            /* channel for parameter changes, -1 = OFF */
#define SEND_CC    ((s32 (*)(s32, s32, s32))0x401066B4u)   /* (channel, CC, value): 0 if not sent */
#define SEND_NRPN  ((s32 (*)(s32, s32, s32, s32))0x401066FCu)   /* (channel, NRPN, 14-bit value, 1) */
#define UI_SETV    0x400380E4u          /* ParameterPageView set-value 0x40037F9A, after its jsr 0x4000DA32 */
#define UI_SETL    0x40037F92u          /* page-view value setter 0x40037F6C, after its jsr 0x4000DA32 */

u32 mf_midi_ins DATA = 0;               /* messages taken (diagnostics) */
u32 mf_midi_outs DATA = 0;              /* messages sent */

u32 mf_midi_in(u32 track, u32 num, u32 v, u32 nrpn)
{
    u32 n;

    if (track != FX_TRACK)
        return 0;
    for (n = 0; n < NP_MIDI; n++)
        if (n != P_RET && num == (nrpn ? (NRPN_MSB << 7) + (u32)midi_nrpn[n] : (u32)midi_cc[n]))
            break;                                      /* RET: no MIDI number */
    if (n == NP_MIDI)
        return 0;
    if (v > 127)
        v = 127;
    mf_p[n] = (u8)(n == P_ON ? v >= 64 : n == P_TYPE ? v >> 4 : v);
    mf_midi_ins++;
    redraw();
    return 1;
}

static void midi_out(u32 n)
{
    char *cfg = (char *)(PROJECT() + 48);               /* +48: MIDI settings and the active track */
    s32 ch, mode, v = n == P_ON ? (mf_p[n] ? 127 : 0) : n == P_TYPE ? type_out[mf_p[n] & 7] : mf_p[n], sent;

    if (!ENC_DEST(cfg))
        return;                                         /* INT: the knobs send nothing */
    ch = OUT_CHAN();
    mode = PARAM_OUT(cfg);
    if (mode == 0)
        sent = SEND_NRPN(ch, (NRPN_MSB << 7) + midi_nrpn[n], v << 7, 1);
    else if (mode == 1)
        sent = SEND_CC(ch, midi_cc[n], v);
    else
        return;
    if (sent & 0xFF)
        mf_midi_outs++;
}

s32 mf_set(void *obj, s32 id, s32 value)
{
    u32 from = (u32)__builtin_return_address(0);
    u32 n = slot(id), old = mf_p[n];
    s32 max = n == P_TYPE ? NT - 1 : n == P_ON || n == P_CMP || n == P_RET ? 1 : 127;

    (void)obj;
    value = (value + 0x80) >> 8;
    mf_p[n] = (u8)(value < 0 ? 0 : value > max ? max : value);
    redraw();
    if (mf_p[n] != old && n < NP_MIDI && n != P_RET && (from == UI_SETV || from == UI_SETL))
        midi_out(n);                                    /* a knob turn on the page, as the stock knobs (RET: no
                                                           MIDI number) */
    return 0;
}

/* ---- TYPE text and graphic (std::function invokers, as in beat-repeat) */

static const char type_txt[NT][5] = {"LP4", "LP2", "BP2", "HP2", "NO1", "NO2", "LPN", "THRU"};

static u32 pos_of(s32 value, u32 max)
{
    value = (value + 0x80) >> 8;
    return value < 0 ? 0 : (u32)value > max ? max : (u32)value;
}

static void copy(char *dst, const char *s)
{
    while ((*dst++ = *s++))
        ;
}

void mf_type_fmt(const void *fn, s32 value, char *buf)
{
    (void)fn;
    copy(buf, type_txt[pos_of(value, NT - 1)]);
}

/* the FX block's own filter icons for its modes (as on the FX track's FLTR page), text for THRU */
void mf_type_gfx(const void *fn, s32 value, void *ctx, s32 x, s32 y)
{
    u32 v = pos_of(value, NT - 1);

    if (v == T_THRU)                                    /* centred on the 21 x 17 icon area */
        DRAW_TEXT(ctx, FONT, x + 10, y + 5, 1, 0, "XXXX", "%s", type_txt[v]);
    else
        FX_TYPE_GFX(fn, (s32)v << 8, ctx, x, y);
}

void mf_freq_fmt(const void *fn, s32 value, char *buf)
{
    (void)fn;
    copy(buf, FREQ_TXT[pos_of(value, 127)]);
}

/* RET: FLTR (the returns through the master filter) / KIT (where the kit routes them) */
void mf_ret_fmt(const void *fn, s32 value, char *buf)
{
    (void)fn;
    copy(buf, pos_of(value, 1) ? "KIT" : "FLTR");
}

void mf_trim_fmt(const void *fn, s32 value, char *buf)
{
    (void)fn;
    copy(buf, TRIM_TXT[pos_of(value, 127)]);
}

void mf_cmp_fmt(const void *fn, s32 value, char *buf)
{
    (void)fn;
    copy(buf, pos_of(value, 1) ? "FX" : "MAIN");
}

int mf_mgr(void *dst, const void *src, int op)
{
    (void)dst;
    (void)src;
    (void)op;
    return 0;
}

const void *const mf_type_proto[4] __attribute__((aligned(4))) = {0, 0, (const void *)mf_mgr, (const void *)mf_type_fmt};
const void *const mf_tgfx_proto[4] __attribute__((aligned(4))) = {0, 0, (const void *)mf_mgr, (const void *)mf_type_gfx};
const void *const mf_freq_proto[4] __attribute__((aligned(4))) = {0, 0, (const void *)mf_mgr, (const void *)mf_freq_fmt};
const void *const mf_ret_proto[4] __attribute__((aligned(4))) = {0, 0, (const void *)mf_mgr, (const void *)mf_ret_fmt};
const void *const mf_trim_proto[4] __attribute__((aligned(4))) = {0, 0, (const void *)mf_mgr, (const void *)mf_trim_fmt};
const void *const mf_cmp_proto[4] __attribute__((aligned(4))) = {0, 0, (const void *)mf_mgr, (const void *)mf_cmp_fmt};

static void put_fn(u32 *dst, const void *const *proto)    /* our std::function, no captured data */
{
    dst[0] = 0;
    dst[1] = 0;
    dst[2] = (u32)proto[2];
    dst[3] = (u32)proto[3];
}

/* a two-position switch drawn and turned like AENR, with our text (CMP, RET) */
static void aenr_switch(s32 id, const void *const *text)
{
    u32 *o = OBJ(id), *a = OBJ(ID_AENR), i;

    for (i = 0; i < 5; i++)
        o[i] = a[i];                                    /* AENR's encoder step and value prototype */
    put_fn(o + 5, text);
    FN_COPY(o + 9, a + 9);                              /* switch graphic */
    FN_COPY(o + 17, a + 17);                            /* style */
}

/* at boot, from mf_page_stub (after the OS built every object): TYPE as an 8-position discrete knob drawn
 * with the FX filter icons; FREQ and RESO keep the stock 0..127 knob of the COL ids, FREQ with its text in Hz;
 * TRIM keeps NLEV's 0..127 knob with its text in dB; FLTR, CMP and RET become copies of AENR's object (header,
 * switch graphic and style through the OS's std::function copy constructor; FLTR keeps AENR's OFF / ON text, CMP
 * shows MAIN / FX, RET FLTR / KIT). The replaced std::functions stay allocated (never destroyed, as in master-comp
 * and beat-repeat); midi-guard rebuilds the stock ones for those machines' pages. */
void mf_boot(void)
{
    u32 *o = OBJ(ID_ON), *a = OBJ(ID_AENR), i;

    for (i = 0; i < 5; i++)
        o[i] = a[i];                                    /* encoder step, value prototype (discrete) */
    FN_COPY(o + 5, a + 5);                              /* OFF / ON */
    FN_COPY(o + 9, a + 9);                              /* switch graphic */
    FN_COPY(o + 17, a + 17);                            /* style */
    o = OBJ(ID_TYPE);

    o[0] = 0;
    for (i = 0; i < 4; i++)
        o[1 + i] = POD_DISC[i];
    put_fn(o + 5, mf_type_proto);
    put_fn(o + 9, mf_tgfx_proto);
    for (i = 17; i < 21; i++)
        o[i] = 0;                                       /* no style (as LFO MODE) */
    put_fn(OBJ(ID_FREQ) + 5, mf_freq_proto);            /* FREQ text in Hz */
    put_fn(OBJ(ID_TRIM) + 5, mf_trim_proto);            /* TRIM in dB */
    aenr_switch(ID_CMP, mf_cmp_proto);                  /* MAIN / FX */
    /* TEST26: no RET object (id 412 is master-comp / gbus's MODE) */
}

const char mf_n_fltr_s[] = "FLTR";
const char mf_n_fltr_l[] = "Master Filter On/Off";
const char mf_n_type_s[] = "TYPE";
const char mf_n_type_l[] = "Master Filter Type";
const char mf_n_freq_s[] = "FREQ";
const char mf_n_freq_l[] = "Master Filter Freq";
const char mf_n_reso_s[] = "RESO";
const char mf_n_reso_l[] = "Master Filter Reso";
const char mf_n_ret_s[] = "RET";
const char mf_n_ret_l[] = "Delay/Reverb Returns";
const char mf_n_trim_s[] = "LVL";
const char mf_n_trim_l[] = "Output Level";

/* TEST15: the FX track's SYN tab cycles page 32 (SYN, BOUM-style dynamics) and page 0 (the OS's unused NONE page,
 * here the master filter); page 0's names, through the page initializer's own string copy */
const u32 mf_syn_pages[2] __attribute__((aligned(4))) = {32, 0};
const char mf_page0_s[] = "SYN2";
const char mf_page0_l[] = "Master Filter";
const char mf_n_cmp_s[] = "CMP";
const char mf_n_cmp_l[] = "Comp Target";
