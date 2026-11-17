/* perf-filter (Syntakt Performance Mods, TEST35): the master filter for PERFORM only. OS 1.41 and 1.42 (-DOS142).
 *
 * The audio half of master-filter, with no page, no parameters and no MIDI: while it is ON, every audio block,
 * tracks 1-12, the delay and reverb returns and the external input go through the analog FX block, whose filter
 * TYPE, FREQ and RESO (Polivoks-style past the stock maximum) come from pf_p; the
 * filter envelope depth is held at 0 and the filter pan centred. The FX DRIVE and the whole FX AMP page stay the
 * kit's, as with master-filter (FX-track trigs still duck, LVL is unity: no gain of its own). Routing settings that
 * take something off the main mix are kept; the kit, the pattern and the live values are never written.
 * Only the jog's PERFORM page sets pf_p (the jog links tj_mfp to it at build time); nothing else on the unit
 * changes, so a MAX set's own pages (FX SYN page 2 and the rest) stay as they are.
 *
 * Where: pf_fx_hook replaces the audio interrupt's call of the FX filter CV routine (jsr at 0x400A4F24 / 1.42
 * 0x400A4F9C, the same site as master-filter: the two can't be in one build). It edits the interrupt's copy of
 * the live values (pf_apply), calls the OS routine with the same two arguments, then rewrites the resonance CV
 * it set (pf_post). pf_p has master-filter's mf_p layout, so the jog drives either one with the same code.
 * Cost: a few instructions a block while OFF; ~300 ON (emulator). No audio processing, no EMAC.
 */
typedef unsigned int u32;
typedef int s32;
typedef unsigned short u16;
typedef short s16;
typedef unsigned char u8;

#define DATA __attribute__((section(".data")))
#ifdef OS142
#define CV_FN     ((void (*)(char *, u16 *))0x40095E1Cu)  /* the OS's FX filter CV routine (CV struct, copy) */
#define HW_CAL    (*(volatile const u8 *)0x43BDD044u)     /* & 31 >= 2: table resonance */
#define FREQ_COMP ((const s16 *)0x40249D38u)              /* per FREQ >> 8, subtracted by the OS */
static const u32 reso_tab[7] = {0x4024A138u, 0x4024A038u, 0x40249F38u, 0x40249E38u,   /* LP4 LP2 BP2 HP2 */
                                0x40249C38u, 0x40249B38u, 0x40249A38u};               /* NO1 NO2 LPN */
#else
#define CV_FN     ((void (*)(char *, u16 *))0x40095DA4u)
#define HW_CAL    (*(volatile const u8 *)0x43BDC044u)
#define FREQ_COMP ((const s16 *)0x40249A18u)
static const u32 reso_tab[7] = {0x40249E18u, 0x40249D18u, 0x40249C18u, 0x40249B18u,
                                0x40249918u, 0x40249818u, 0x40249718u};
#endif
/* route-to-main masks (bit set = off the main mix): 0..11 tracks, 12 delay, 13 reverb, 14 FX block; the kit's
 * word, or the global one when its bit 15 is set (same RAM on both OSes) */
#define TO_MAIN_KIT    (*(volatile const s16 *)0x80003148u)
#define TO_MAIN_GLOBAL (*(volatile const s16 *)0x8000314Cu)

/* byte offsets in the copy of the live values */
#define W(off)    ((off) / 2)
#define ROUT(t)   (142 * (t) + 126)                      /* Pre/Post FX, 0 = through the FX block */
#define OFF_DEL   1782                                   /* Delay FX Routing, 0 = through */
#define OFF_REV   1800                                   /* Reverb FX Routing */
#define OFF_IN    1818                                   /* In FX Routing */
#define OFF_TYPE  1820                                   /* FX filter type 0..7 (<< 8), 7 = OFF */
#define OFF_FREQ  1822
#define OFF_RESO  1824
#define OFF_ENV   1826                                   /* envelope depth, 0x4000 = 0 */
#define OFF_FPAN  1840                                   /* filter pan, 0x4000 = centre */
#define OFF_FXDEL 1858                                   /* FX AMP DEL (the FX block's send to the delay) */

/* master-filter's layout: the knob bytes (TRIM, CMP and RET kept so the offsets are the same; unused here) with the
 * smoothed values 19 bytes under them, where the jog's PERFORM writes its fine cutoff (see tj.c, flt) */
enum { P_TYPE, P_FREQ, P_RESO, P_RET, P_ON, P_TRIM, P_CMP, NP };
enum { T_LP4, T_LP2, T_BP2, T_HP2, T_NO1, T_NO2, T_LPN, T_THRU, NT };
enum { S_FREQ, S_RESO, S_ENV, S_FPAN, NS };
static const u16 s_off[NS] = {OFF_FREQ, OFF_RESO, OFF_ENV, OFF_FPAN};

struct pf_t {
    s32 s[NS];                                           /* smoothed FREQ RESO ENV FPAN, value << 16 */
    u8 pad[3];
    u8 p[NP];                                            /* the knobs: pf_p = pf.p = pf.s + 19 */
} pf DATA = {{0}, {0}, {T_THRU, 127, 0, 0, 0, 64, 0}};    /* OFF at power-on, as master-filter */
#define pf_p (pf.p)
#define pf_s (pf.s)
u8 pf_on DATA = 0;                                       /* the filter is in the signal path (the last block) */
u32 pf_blocks DATA = 0, pf_posts DATA = 0;               /* diagnostics */

/* one-pole glide toward t (0..0x7FFF), 1/32 a block (~21 ms, as the OS's smoothing), snapping within 1/16 step */
static s32 glide(s32 s, s32 t)
{
    s32 d = (t << 16) - s;
    if (d < (16 << 16) && d > -(16 << 16))
        return t << 16;
    return s + (d >> 5);
}

void pf_apply(u16 *c)
{
    u32 type = pf_p[P_TYPE], on = pf_p[P_ON], k, t;
    s32 m = TO_MAIN_KIT, tg[NS];

    if (!on && !pf_on)
        return;                                         /* OFF and settled: nothing to do */
    if (m < 0)
        m = TO_MAIN_GLOBAL;
    if (type >= NT)
        type = T_THRU;
    if (m & 0x4000)
        on = 0;                                         /* FX block off the main mix: it would mute all */
    if (!on) {
        pf_on = 0;                                      /* the kit's routing and FX settings in this very block */
        return;
    }
    tg[S_FREQ] = type == T_THRU ? 0x7F00 : (s32)pf_p[P_FREQ] << 8;
    tg[S_RESO] = type == T_THRU ? 0 : (s32)pf_p[P_RESO] << 8;
    tg[S_ENV] = 0x4000;
    tg[S_FPAN] = 0x4000;
    for (k = 0; k < NS; k++) {
        s32 x = tg[k];
        pf_s[k] = !pf_on ? x << 16 : glide(pf_s[k], x);
        c[W(s_off[k])] = (u16)((u32)(pf_s[k] + 0x8000) >> 16);
    }
    for (t = 0; t < 12; t++)
        if (!(m & (1 << t)))
            c[W(ROUT(t))] = 0;
    if (!(m & 0x1000))                                  /* the returns through the filter too */
        c[W(OFF_DEL)] = 0;
    if (!(m & 0x2000))
        c[W(OFF_REV)] = 0;
    if (!c[W(OFF_DEL)])                                 /* delay return in the FX block: that send is muted */
        c[W(OFF_FXDEL)] = 0;                            /* anyway; the word would only cut delay -> reverb */
    c[W(OFF_IN)] = 0;
    c[W(OFF_TYPE)] = (u16)(type << 8);                  /* THRU = 7 = the FX filter's OFF */
    pf_on = 1;
    pf_blocks++;
}

/* Polivoks resonance (master-filter's): the table up to RESO 63 (interpolated), then a straight line past the
 * stock maximum by a quarter of the type's table range, minus the OS's cutoff compensation */
#define CV_RESO 78
#define KNEE    63
static s32 reso_cv(u32 type, s32 r)
{
    const s16 *t = (const s16 *)reso_tab[type];
    s32 i = r >> 8, f = r & 0xFF, top;
    if (i < KNEE)
        return t[i] + (((t[i + 1] - t[i]) * f) >> 8);
    top = t[127] + ((t[127] - t[0]) >> 2);
    return t[KNEE] + (((top - t[KNEE]) * (r - (KNEE << 8))) >> 14);
}

void pf_post(char *cv, const u16 *c)
{
    u32 type = c[W(OFF_TYPE)] >> 8, fi = c[W(OFF_FREQ)] >> 8;
    s32 r = (s16)c[W(OFF_RESO)], v;
    if (!pf_on || type >= T_THRU || (HW_CAL & 31) <= 1)
        return;
    r = r < 0 ? 0 : r > 0x7F00 ? 0x7F00 : r;
    if (fi > 127)
        fi = 127;
    v = reso_cv(type, r) - FREQ_COMP[fi];
    *(s16 *)(cv + CV_RESO) = (s16)(v < -32768 ? -32768 : v > 32767 ? 32767 : v);
    pf_posts++;
}

/* the audio interrupt's jsr: (CV struct, copy), as the OS routine; d0-d1/a0-a1 scratch, the rest kept (C ABI) */
void pf_fx_hook(char *cv, u16 *c)
{
    pf_apply(c);
    CV_FN(cv, c);
    pf_post(cv, c);
}
