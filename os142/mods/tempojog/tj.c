/* tempojog (TEST33a): the JOG page, a CDJ-style jog for beat-matching the Syntakt by hand.
 *
 * Open: hold [TEMPO] (the TEMPO menu opens on the press as stock, then turns into JOG when the OS reports the hold),
 * or push knob A in the TEMPO menu. [NO] / [YES] close it as they close the TEMPO menu. The TEMPO menu itself is
 * stock again (TEST31a's knobs A-D and the two-decimal BPM are gone).
 *
 * JOG is the TEMPO view (TempoView) in a second state: its key handler (vtable slot 2), draw (slot 4), encoder entry
 * and destructors (slots 0 / 1) are ours while tj_view is that view, stock's otherwise.
 *  - A turn: the ring, a pitch bend that follows how fast you spin and eases back when you stop (both modes).
 *  - A push (VINYL): touch the platter: BRAKE to a stop, HOLD; turn while pushed to walk the beat on by hand (forward
 *    only); let go: START back to speed. In CDJ mode a push does nothing, as on a CDJ.
 *  - B mode VINYL / CDJ, C LOAD 1-8 (the jog's weight), D BRAKE 0-3 s, E START 0-3 s, G RANGE 6/10/16/WIDE (the bend
 *    cap), H PHASE (an exact nudge, 1/360 beat a click). LEVEL/DATA, [UP]/[DOWN]: the tempo, as in the TEMPO menu.
 *    [FUNC] held: the settings at a glance.
 *  - The clock: every audio block (1500 a second) the audio interrupt takes the tempo word (BPM x 120) and counts it
 *    down towards the next 96th subtick; tj_rate stands in for that read (internal clock only). At rest it returns
 *    the word itself, so the clock is stock's. MIDI clock out is sent from the same tempo interrupt, so it follows.
 *  - The screen: a platter whose marker turns once a bar (12 o'clock = the one), the mode, the live BPM, the
 *    deviation and a pitch meter. SETTINGS > PERSONALIZE gets a "JOG DISPLAY" line: VINYL (a record with strobe dots
 *    and grooves) or CDJ (a CDJ jog display). RAM only: VINYL after power-on. */
typedef unsigned int u32;
typedef int s32;
typedef unsigned short u16;
typedef short s16;
typedef unsigned char u8;
typedef signed char s8;

#define DATA __attribute__((section(".data")))
#ifdef OS142
#define TEMPO      (*(volatile s32 *)0x402D7360u)
#define PLAYING    (*(volatile u32 *)0x43BD83BCu)
#define UI_ROOT    (*(char *const volatile *)0x444E2334u)
#define TEXT       ((void (*)(void *, const void *, s32, s32, s32, const char *, ...))0x400F8BD0u)
#define FILL       ((void (*)(void *, s32, s32, s32, s32, s32))0x400F7FB6u)
#define FONT(o)    ((const void *)(0x443DB000u + (o)))
#define STOCK_DRAW ((void (*)(void *, void *))0x4006D60Au)
#define STOCK_KEY  ((s32 (*)(void *, const u8 *))0x4006DDDAu)
#define REDRAW     ((void (*)(void *))0x400FFE22u)
#define CLK_SRC    ((s32 (*)(void))0x40118CF8u)
#define EXT_ST     ((s32 (*)(void))0x40119B7Cu)
#define PERS_CTOR  ((void (*)(void *))0x400571F8u)
#define NEW        ((u32 (*)(u32))0x4010394Cu)        /* returns in d0: u32, not a pointer type */
#define ITEM_CTOR  ((void (*)(void *, u32 *, u32 *, u32 *, u32 *, s32, s32))0x400FA84Cu)
#define APPEND     ((void (*)(void *, void *))0x400FA082u)
#define FN_DTOR    ((void (*)(u32 *))0x4016DC10u)
#define TEXT2      ((void (*)(void *, const void *, s32, s32, s32, s32, s32, const char *))0x400F8DDCu)
#define FONT_LIST  ((const void *)0x402AA114u)
#define MGR_NAME   0x40056462u                  /* REMEMBER SUBPAGE's four functor managers (their storage shapes) */
#define MGR_TOG    0x400564B4u
#define MGR_DRAW   0x40056510u
#define MGR_DELTA  0x40056562u
#define ENC_REST   "0x4006DFB8"
#define DTOR0      "0x40187C86"
#define DTOR1      "0x40187D64"
#define STR_CTOR   "0x401BF31E"
#define DIN_CB     ((void (*)(u32))0x40102828u)       /* the stock DIN MIDI byte callback (UART interrupt) */
#define PARSER     ((void (*)(u32, void *))0x401022C6u) /* the stock MIDI byte parser (byte, port state) */
#define USB_ST     ((void *)0x443EB2ECu)              /* the USB port's parser state */
#define COPY_FN    "0x400979CA"                       /* TEST34: the copy builder (the live values, 0x80006348) */
#define STEP       (*(volatile u16 *)0x43BD83C0u)     /* TEST34: the sequencer's pattern step (0 = the pattern's start) */
#define SETTER     ((void (*)(void *, s32))0x4006D3B6u)  /* TEST34: the TEMPO view's own set-tempo (view, BPM x 120) */
#define OBJS       0x41BA0A24u                        /* per-parameter UI objects (84 B, by id): their formatters */
#else
#define TEMPO      (*(volatile s32 *)0x402D7010u)
#define PLAYING    (*(volatile u32 *)0x43BD73BCu)
#define UI_ROOT    (*(char *const volatile *)0x444E1334u)
#define TEXT       ((void (*)(void *, const void *, s32, s32, s32, const char *, ...))0x400F8A0Cu)
#define FILL       ((void (*)(void *, s32, s32, s32, s32, s32))0x400F7DF2u)
#define FONT(o)    ((const void *)(0x443DA000u + (o)))
#define STOCK_DRAW ((void (*)(void *, void *))0x4006D592u)
#define STOCK_KEY  ((s32 (*)(void *, const u8 *))0x4006DD62u)
#define REDRAW     ((void (*)(void *))0x400FFC5Eu)
#define CLK_SRC    ((s32 (*)(void))0x40118B34u)
#define EXT_ST     ((s32 (*)(void))0x401199B8u)
#define PERS_CTOR  ((void (*)(void *))0x40057180u)
#define NEW        ((u32 (*)(u32))0x40103788u)
#define ITEM_CTOR  ((void (*)(void *, u32 *, u32 *, u32 *, u32 *, s32, s32))0x400FA688u)
#define APPEND     ((void (*)(void *, void *))0x400F9EBEu)
#define FN_DTOR    ((void (*)(u32 *))0x4016DA4Cu)
#define TEXT2      ((void (*)(void *, const void *, s32, s32, s32, s32, s32, const char *))0x400F8C18u)
#define FONT_LIST  ((const void *)0x402A9DC4u)
#define MGR_NAME   0x400563EAu
#define MGR_TOG    0x4005643Cu
#define MGR_DRAW   0x40056498u
#define MGR_DELTA  0x400564EAu
#define ENC_REST   "0x4006DF40"
#define DTOR0      "0x40187AC2"
#define DTOR1      "0x40187BA0"
#define STR_CTOR   "0x401BF082"
#define DIN_CB     ((void (*)(u32))0x40102664u)
#define PARSER     ((void (*)(u32, void *))0x40102102u)
#define USB_ST     ((void *)0x443EA2ECu)
#define COPY_FN    "0x40097952"
#define STEP       (*(volatile u16 *)0x43BD73C0u)
#define SETTER     ((void (*)(void *, s32))0x4006D33Eu)
#define OBJS       0x41B9FA24u
#endif
#define PAT_PTR    (*(volatile u32 *)0x800030B8u)
#define MACHINES   ((const volatile u8 *)0x80002F50u) /* TEST34: each track's machine (the OS fills it from the sound) */     /* TEST34: the current pattern (changes on a pattern / song row) */
#define PF __attribute__((section(".text.pf")))   /* TEST34: the drawing of JOG / PERFORM: a chunk of its own */
#define PF2 __attribute__((section(".text.pf2"))) /* TEST34: the pitch, the glide, the keys: another */
#define TL __attribute__((section(".text.tl")))   /* LINK code: its own chunk at +0x15100 */
#define DTCN       (*(volatile u32 *)0xFC07000Cu)     /* DMA timer 0: free running (the OS's own time base) */
#define F_BIG  FONT(0x1E0)                      /* the stock bold label font (9 px) */
#define F_VAL  FONT(0x228)                      /* bold digits (10 px) */
#define F_LBL  FONT(0x230)                      /* MAX's label font (5 px) */
#define F_SML  FONT(0x208)                      /* a narrow 5 px font */

#define Q     65536                             /* platter speed and bend: Q16 */
#define BEAT  10800000                          /* tempo-word units in a beat (96 subticks x 112,500) */
#define BAR   (4 * BEAT)
#define BLK_S 1500                              /* audio blocks a second */

/* engine (audio interrupt) */
s32 tj_bend DATA = 0;                           /* ring: the bend now (Q20: 1/16 of the Q16 speed unit) */
s32 tj_debt DATA = 0;                           /* PHASE / crank: phase still to move (tempo-word units; + ahead) */
s32 tj_sp DATA = Q;                             /* platter speed (Q16): Q = normal, 0 = held */
s32 tj_bstep DATA = Q / 600, tj_sstep DATA = Q / 300;   /* BRAKE / START: speed change a block */
s32 tj_rate DATA = 0;                           /* the rate the clock counted with last block */
u32 tj_pos DATA = 0;                            /* the position in the bar while playing (tempo-word units) */
s32 tj_strobe DATA = 0;                         /* strobe dots: summed speed error */
u32 tj_lease DATA = 0, tj_tick DATA = 0, tj_popt DATA = 0;
u8 tj_touch DATA = 0;
/* settings (RAM) */
u8 tj_mode DATA = 1;                            /* 1 VINYL, 0 CDJ */
u8 tj_load DATA = 3, tj_brake DATA = 4, tj_start DATA = 2, tj_range DATA = 1;
u8 tj_disp DATA = 0;                            /* PERSONALIZE > JOG DISPLAY: 0 VINYL, 1 CDJ */
/* page */
void *tj_view DATA = 0;                         /* the TEMPO view that is the JOG page now */
u8 tj_func DATA = 0, tj_skip DATA = 0, tj_pop DATA = 0;
s32 tj_phs DATA = 0;                            /* PHASE clicks in the pop-up shown now */

/* TEST34 */
u8 tj_mt DATA = 0;                              /* MASTER TEMPO ([YES]): 0 = the pitch follows the jog (default) */
u8 tj_page DATA = 0;                            /* 0 JOG, 1 PERFORM ([RIGHT] / [LEFT]) */
s32 tj_btgt DATA = 0;                           /* the ring's bend target (the bend glides to it) */
s32 tj_ratio DATA = 4096;                       /* the jog's speed against the set tempo, Q12 (the pitch follows it) */
s32 tj_semi DATA = 0;                           /* the pitch offset now, 1/256 semitone */
u32 tj_bars DATA = 0;                           /* bars since the phrase started */
u32 tj_pat DATA = 0;                            /* the pattern the phrase belongs to */
u16 tj_step DATA = 0xFFFF;                      /* the sequencer's step, last block */
u8 tj_phr DATA = 1;                             /* PHR: 8 / 16 / 32 / 64 bars ([FUNC] + H) */
u8 tj_gld DATA = 3;                             /* GLD: CUT / 1 / 2 / 4 / 8 / 16 bars ([FUNC] + G) */
volatile u8 tj_gl DATA = 0;                     /* the glide: 0 none, 1 moving, 2 there (to store), 3 stored */
s32 tj_gl_cur DATA = 0, tj_gl_tgt DATA = 0, tj_gl_step DATA = 0, tj_gl_from DATA = 0;   /* Q8 tempo words */
s32 tj_open_t DATA = 0;                         /* the tempo when JOG opened ([FUNC] + [NO]) */
s8 tj_fpos DATA = 0;                            /* PERFORM's DJ filter: -63 LP closed .. 0 THRU .. +63 HP (drawn) */
/* TEST35 (Syntakt Performance Mods) */
s32 tj_fp DATA = 0;                             /* the DJ filter's fine position: -4032 .. 4032 */
s32 tj_fq DATA = 0, tj_fqt DATA = 0;            /* the cutoff word (FREQ << 8 | FINE) now and its target */
volatile u8 tj_fown DATA = 0;                   /* PERFORM owns the cutoff: its side (1 LP2, 3 HP2), else 0 */
u8 tj_fb DATA = 0;                              /* the FREQ byte PERFORM wrote last */
#define NFFT 256
#define SPX  0x8000DED0u                        /* the OS's digital copy of the main mix: 32 frames L, R (int32) */
typedef struct {
    s16 full[NFFT], dec[NFFT];                  /* the mix at 48 kHz and at 6 kHz (rings, written by tj_tap) */
    s32 re[NFFT], im[NFFT];
    s16 cs[NFFT / 2], sn[NFFT / 2];             /* twiddles, Q14 */
    u16 win[NFFT];                              /* Hann, Q15 */
    u16 lv[2][NFFT / 2];                        /* each FFT's levels, 16 x log2 of the power */
    s16 col[128];                               /* the columns shown */
    s16 ref;                                    /* the loudest, falling slowly */
    u16 turn;
} spec_t;
spec_t *tj_spec DATA = 0;                       /* from the OS's heap at the first PERFORM */
volatile u16 tj_spon DATA = 0;                  /* blocks the tap still runs (PERFORM on screen) */
u16 tj_fw DATA = 0, tj_dw DATA = 0;
u8 tj_dn DATA = 0;
s32 tj_dacc DATA = 0;
u8 *tj_mfp DATA = 0;                            /* master-filter's knob values (mf_p); 0 = not in this build */
static const u8 RANGE[4] = {6, 10, 16, 50};
/* TEST35: LOAD 1-8, the share of the bend target the ring gives back each block (Q16), light .. heavy */
static const u16 EASE[9] = {2000, 2000, 1000, 400, 230, 160, 110, 74, 50};
static const u8 PHRS[4] = {8, 16, 32, 64};
static const u8 GLDS[6] = {0, 1, 2, 4, 8, 16};
static s32 clamp(s32 v, s32 lo, s32 hi) { return v < lo ? lo : v > hi ? hi : v; }

/* ---- LINK (TEST33a): the CDJ bridge's messages on MIDI in ----
 * The bridge (a Teensy on the CDJs' network) sends SysEx F0 7D 4C <cmd> ... F7 (7D: the non-commercial id):
 *   01 BEAT  <deck> <beat 1-4, 0 = no grid>   timed so its F7 lands when the master's beat is heard
 *   02 TEMPO <t2> <t1> <t0>                    the master's tempo playing now (BPM x 120, 21 bits)
 *   03 STATE <deck> <flags>                    bit 0 link up, bit 1 master playing, bit 2 the bridge sends clock
 * The filters sit on the OS's two MIDI inputs (the DIN byte callback, the USB buffer callback): our frames are
 * swallowed, every other byte goes on to the OS exactly as before. Each BEAT is timed by DMA timer 0 and compared
 * with where the Syntakt is at that moment: tj_pos on the internal clock (LOCK steers the rate onto the master),
 * the count of MIDI clocks since Start on an external clock (SYNC: the bridge's clock, the meter only). */
#ifndef NOLINK
struct tl_port { u8 st, n, b[8]; };
struct tl_port tl_pd DATA = {0, 0, {0}}, tl_pu DATA = {0, 0, {0}};
u8 tl_mode DATA = 0;                            /* knob F: 0 MAN (meter only), 1 LOCK */
u8 tl_bar DATA = 1;                             /* LOCK onto the bar (1) or the nearest beat (0) */
s16 tl_off DATA = 0;                            /* offset, 0.1 ms; + = the Syntakt plays later */
s32 tl_mt DATA = 0;                             /* the master's tempo word, 0 = none yet */
u8 tl_dk DATA = 0, tl_fl DATA = 0, tl_bb DATA = 0, tl_ext DATA = 0;
volatile u8 tl_new DATA = 0;                    /* a BEAT for the next audio block to measure */
u32 tl_bt DATA = 0;                             /* DMA timer at that BEAT's last byte */
u32 tl_t0 DATA = 0, tl_blk DATA = 0, tl_seen DATA = 0;
u32 tl_age DATA = 0xFFFF;                       /* audio blocks (internal) / clocks (external) since a BEAT */
s32 tl_err DATA = 0;                            /* the last phase error, tempo-word units; + = the Syntakt late */
s32 tl_rem DATA = 0;                            /* LOCK: phase still to make up (tempo-word units) */
u8 tl_pull DATA = 0;                            /* LOCK: a big error, the wider cap */
s32 tl_f8 DATA = -1;                            /* external clock: clocks since Start (0..95), -1 before the first */
u8 tl_run DATA = 0;
u32 tl_f8t DATA = 0, tl_f8d DATA = 0;
#else
/* NOLINK: the JOG page without LINK. LINK's state is the constant "no bridge" state, so every LINK path below
 * folds away at compile time; no MIDI input is hooked and knob F does nothing. */
#define tl_mode 0
#define tl_bar 1
#define tl_off 0
#define tl_mt 0
#define tl_dk 0
#define tl_bb 0
#define tl_ext 0
#define tl_err 0
#define tl_rem 0
#define tl_pull 0
#define tl_f8 (-1)
#define tl_run 0
#endif

static void want_redraw(void);

#ifdef NOLINK
#define LIVE() 0
#else
#define LIVE() (tl_age < (tl_ext ? 48 : 4500))  /* a BEAT within two beats (external) / three seconds (internal) */
#endif

#ifndef NOLINK
TL static s32 wrap(s32 e, s32 m)                   /* into [-m/2, m/2) */
{
    e %= m;
    if (e >= m / 2)
        e -= m;
    else if (e < -m / 2)
        e += m;
    return e;
}

/* the internal clock: measured in the audio block after the BEAT (pos and rate of the block before) */
TL static void tl_lock(u32 now)
{
    u32 blk = now - tl_t0, dt = tl_bt - tl_t0, f;
    s32 t = tl_mt ? tl_mt : TEMPO, pos, tgt, e;
    if (dt > blk)
        dt = blk;
    f = blk ? (dt << 8) / blk : 0;              /* where in the last block the beat fell, /256 */
    if (PLAYING != 1) {                         /* stopped or paused */
        tl_err = tl_rem = 0;
        return;
    }
    pos = (s32)tj_pos - tj_rate + (s32)(((u32)tj_rate * f) >> 8);   /* tj_pos is already the block's end */
    tgt = (tl_bb ? (tl_bb - 1) * BEAT : 0) - tl_off * t * 3 / 20;   /* 0.1 ms = 0.15 blocks */
    e = tgt - pos;
    e = wrap(e, tl_bar && tl_bb ? BAR : BEAT);
    tl_err = e;
    tl_pull = e > BEAT / 16 || e < -BEAT / 16;
    if (!tl_pull)
        e /= 2;                                 /* in phase: half the error a beat (smooths the BEATs' jitter) */
    tl_rem = tl_mode && !tj_bend && !tj_touch && tj_sp == Q ? e : 0;
}

/* an external clock: measured at once, against the clocks since Start */
TL static void tl_sync(u32 now)
{
    s32 t = tl_mt ? tl_mt : TEMPO, q, tgt, e;
    u32 f = tl_f8d ? ((now - tl_f8t) << 8) / tl_f8d : 0;
    if (!tl_run || tl_f8 < 0) {
        tl_err = 0;
        return;
    }
    if (f > 255)
        f = 255;
    q = tl_f8 * 256 + (s32)f;                    /* 1/256 clock */
    tgt = (tl_bb ? (tl_bb - 1) * 24 * 256 : 0) - tl_off * t / 11719;  /* clocks a ms = BPM x 120 / 300,000 */
    e = wrap(tgt - q, tl_bar && tl_bb ? 96 * 256 : 24 * 256);
    tl_err = e * 1758;                          /* 1/256 clock = 1757.8 tempo-word units */
}

TL static void tl_msg(const u8 *b, s32 n, u32 now)
{
    if (b[2] == 1 && n >= 5) {                  /* BEAT */
        tl_dk = b[3];
        tl_bb = b[4] <= 4 ? b[4] : 0;
        tl_bt = now;
        tl_ext = tl_blk == tl_seen;             /* no audio block on the internal path since the last one */
        tl_seen = tl_blk;
        tl_age = 0;
        if (tl_ext)
            tl_sync(now);
        else
            tl_new = 1;
    } else if (b[2] == 2 && n >= 6) {           /* TEMPO */
        s32 t = (b[3] << 14) | (b[4] << 7) | b[5];
        if (t >= 30 * 120 && t <= 300 * 120)
            tl_mt = t;
    } else if (b[2] == 3 && n >= 5) {           /* STATE */
        tl_dk = b[3];
        tl_fl = b[4];
    }
}

TL static void tl_rt(u32 b, u32 now)               /* real-time bytes: the external clock's position */
{
    if (b == 0xF8) {
        if (tl_run && ++tl_f8 >= 96)
            tl_f8 = 0;
        tl_f8d = now - tl_f8t;
        tl_f8t = now;
        if (tl_ext && tl_age < 0xFFFF)
            tl_age++;
        if (tj_view && tl_ext && !(tl_f8 & 3))
            want_redraw();
    } else if (b == 0xFA) {
        tl_run = 1;
        tl_f8 = -1;
    } else if (b == 0xFB)
        tl_run = 1;
    else if (b == 0xFC)
        tl_run = 0;
}

TL static void fwd(s32 usb, u32 b)
{
    if (usb)
        PARSER(b, USB_ST);
    else
        DIN_CB(b);
}

TL static void flush(struct tl_port *p, s32 usb)
{
    s32 i;
    fwd(usb, 0xF0);
    for (i = 0; i < p->n; i++)
        fwd(usb, p->b[i]);
    p->n = 0;
}

TL static void tl_in(struct tl_port *p, s32 usb, u32 b)
{
    u32 now = DTCN;
    if (b >= 0xF8) {                            /* real time: anywhere, even inside a SysEx */
        tl_rt(b, now);
        fwd(usb, b);
        return;
    }
    if (p->st == 1) {                           /* collecting what may be ours */
        if (b == 0xF7) {
            p->st = 0;
            if (p->n >= 3) {
                tl_msg(p->b, p->n, now);
                p->n = 0;
                return;
            }
            flush(p, usb);
            fwd(usb, b);
            return;
        }
        if (!(b & 0x80)) {
            p->b[p->n++] = (u8)b;
            if ((p->n == 1 && b != 0x7D) || (p->n == 2 && b != 0x4C) || p->n >= 8) {
                flush(p, usb);                  /* not ours: the OS gets all of it, from F0 on */
                p->st = 2;
            }
            return;
        }
        flush(p, usb);                          /* a status byte cut it short */
        p->st = 0;
    } else if (p->st == 2) {                    /* someone else's SysEx: straight through */
        if (!(b & 0x80)) {
            fwd(usb, b);
            return;
        }
        p->st = 0;
        if (b == 0xF7) {
            fwd(usb, b);
            return;
        }
    }
    if (b == 0xF0) {
        p->st = 1;
        p->n = 0;
        return;
    }
    fwd(usb, b);
}

/* the OS's MIDI input callbacks, registered at boot in place of its own */
TL void tl_din(u32 b) { tl_in(&tl_pd, 0, b & 0xFF); }

TL void tl_usb(const u8 *buf, s32 len)
{
    s32 i;
    for (i = 0; i < len; i++)
        tl_in(&tl_pu, 1, buf[i]);
}
#endif

static void want_redraw(void)
{
    char *ui = UI_ROOT;
    if (ui)
        ui[96] = 1;
}

/* every audio block, in place of "move.l TEMPO,d0" (internal clock): the rate the clock counts with */
s32 tj_rate_c(void)
{
    u32 now = DTCN, st = PLAYING;
    s32 t, r, k, m, s, rj;
#ifndef NOLINK
    if (tl_new) {                               /* a BEAT since the last block: where were we? */
        tl_new = 0;
        tl_lock(now);
    }
    tl_t0 = now;
    tl_blk++;
    if (tl_age < 0xFFFF)
        tl_age++;
#else
    (void)now;
#endif
    t = tl_mode && tl_mt ? tl_mt : TEMPO;       /* LOCK: the master's tempo (the saved tempo is untouched) */
    if (tj_gl) {                                /* TEST34: a tempo memory / reset gliding in */
        if (tl_mode && tl_mt)
            tj_gl = 0;                          /* LOCK: the master rules */
        else {
            if (tj_gl == 1) {                   /* equal steps, clamped at the target: no overshoot */
                s32 c = tj_gl_cur, g = tj_gl_tgt, d = tj_gl_step;
                c = c < g ? (g - c > d ? c + d : g) : (c - g > d ? c - d : g);
                tj_gl_cur = c;
                if (c == g)
                    tj_gl = 2;                  /* there: the UI stores it with the TEMPO view's own setter */
            }
            if (tj_gl == 3 && TEMPO == tj_gl_tgt >> 8)
                tj_gl = 0;                      /* stored: the tempo setting takes over in this very block */
            else
                t = tj_gl_cur >> 8;
        }
    }
    r = t;
    if (tj_bend || tj_btgt || tj_debt || tj_sp != Q || tj_touch) {
        if (tj_touch)
            tj_sp = tj_sp > tj_bstep ? tj_sp - tj_bstep : 0;
        else if (tj_sp < Q)
            tj_sp = tj_sp + tj_sstep < Q ? tj_sp + tj_sstep : Q;
        if (tj_bend != tj_btgt) {               /* TEST34: the bend glides to its target (about 40 ms) */
            k = (tj_btgt - tj_bend) >> 6;
            tj_bend += k ? k : tj_btgt > tj_bend ? 1 : -1;
        }
        k = tj_sp + (tj_touch ? 0 : tj_bend >> 4);
        if (k < 0)
            k = 0;
        if (k != Q)
            r = t + ((t * ((k - Q) >> 1)) >> 15);   /* t <= 36,000, |k - Q| <= Q: fits */
        if (tj_btgt) {                          /* TEST35: the target eases back by LOAD, the jog's weight: */
            s32 a = tj_btgt < 0 ? -tj_btgt : tj_btgt;   /* a share a block (EASE), never less than 4 units, */
            s = (a * EASE[tj_load]) >> 16;      /* so there is no slow tail: from a 2 % bend about 0.28 s */
            if (s < 4)                          /* (LOAD 1) .. 2.3 s (LOAD 8), 0.6 s at LOAD 3 */
                s = 4;
            tj_btgt = s >= a ? 0 : tj_btgt > 0 ? tj_btgt - s : tj_btgt + s;
        }
        if (tj_debt) {                          /* PHASE at up to 4 %; the hand walk (platter held) as before */
            s32 cap = tj_touch || tj_sp < Q ? t : t / 25;
            if (cap < 1)
                cap = 1;
            m = tj_debt > 0 ? (tj_debt < cap ? tj_debt : cap) : (-tj_debt < r && -tj_debt < cap ? tj_debt :
                                                                  -(r < cap ? r : cap));
            r += m;
            tj_debt -= m;
        }
    }
    rj = r;                                     /* the jog's own speed: what the pitch follows */
#ifndef NOLINK
    if (tl_rem) {                               /* LOCK: make up the phase, half of it a beat, capped */
        s32 cap = t * (tl_pull ? 16 : 3) / 100;
        if (PLAYING != 1 || !tl_mode || tj_bend || tj_touch || tj_sp != Q || !LIVE())
            tl_rem = 0;
        else {
            m = clamp((tl_rem >> 10) * 2 * t / (BEAT >> 10), -cap, cap);
            if (!m)
                m = tl_rem > 0 ? 1 : -1;
            if ((tl_rem > 0 && m > tl_rem) || (tl_rem < 0 && m < tl_rem))
                m = tl_rem;
            r += m;
            tl_rem -= m;
        }
    }
#endif
    tj_rate = r;
    tj_ratio = rj == t || !t ? 4096 : (rj << 12) / t;
    if (st == 1) {                              /* TEST34: playing (2 = paused: everything holds) */
        u32 pat = PAT_PTR, stp = STEP;
        if (pat != tj_pat) {                    /* a new pattern / song row: the one, and the phrase from bar 1 */
            tj_pat = pat;
            tj_pos = 0;
            tj_bars = 0;
        } else if (stp < tj_step && tj_step != 0xFFFF) {   /* the pattern starts again: that's the one */
            if (tj_pos >= BEAT / 2)
                tj_bars++;                      /* a pattern shorter than whole bars: its part bar counts */
            tj_pos = 0;
        }
        tj_step = (u16)stp;
        tj_pos += r;
        if (tj_pos >= BAR) {
            tj_pos -= BAR;
            tj_bars++;
        }
        if (tj_lease)
            tj_strobe += r - t;
    } else if (!st) {
        tj_pos = 0;
        tj_bars = 0;
        tj_step = 0xFFFF;
        tj_pat = PAT_PTR;
    }
    if (tj_popt && !--tj_popt)
        want_redraw();
    if (tj_lease) {                             /* ~30 redraws a second while JOG is up and something moves */
        tj_lease--;
        if (++tj_tick >= (tj_page ? 100u : 50u)) {   /* TEST35: PERFORM 15 a second (its spectrum) */
            tj_tick = 0;
            if (st == 1 || r != t || tj_sp != Q || LIVE() || tj_gl || tj_page)
                want_redraw();
        }
    }
    return r;
}

/* ---- TEST34: the pitch follows the jog (MASTER TEMPO off) ----
 * Right after the audio interrupt builds its copy of the live values (0x40097952 -> 0x80006348, 142 B a track,
 * parameter slot i at +28 + 2i; the machine from the engine's table 0x80002F50), every audio track's TUNE (slot 18, every machine that has a
 * TUNE: 1/256 semitone a step, +-64 semitones) gets the jog's offset: 12 x log2(speed) semitones. The voice CPU
 * and the analog CV routines read that copy, so tracks 1-8 and 9-12 follow it. A VINYL brake fades every audio
 * track's AMP VOL (slot 48) over the last quarter of the speed, back on START. The OS rebuilds the copy every block
 * from the kit, so nothing is ever left behind: MASTER TEMPO on (or the jog at rest) = stock. */
static const u16 LOG2[17] = {0, 269, 522, 762, 989, 1205, 1411, 1608, 1797, 1978, 2152, 2319, 2480, 2636, 2786,
                             2931, 3072};       /* 3072 x log2(1 + i/16): 12 semitones an octave, Q8 */
#define TUNE_LO 0xFFD7FFFFu                     /* machines 0-31 with TUNE in slot 18 (not 19, 21) */
#define TUNE_HI 0x000007F0u                     /* machines 32-42: 36-42 */
#define AUD_HI  0x000017F0u                     /* audio machines (AMP VOL, slot 48): + 44 (CY ALLOY, no TUNE) */

PF2 static s32 semis(s32 x)                      /* x: speed, Q12 (4096 = 1); semitones, Q8; floor -24 */
{
    s32 e = 0, i, f;
    if (x <= 1024)
        return -24 * 256;
    while (x >= 8192) {
        x >>= 1;
        e++;
    }
    while (x < 4096) {
        x <<= 1;
        e--;
    }
    i = (x - 4096) >> 8;
    f = (x - 4096) & 255;
    return e * 3072 + LOG2[i] + (((LOG2[i + 1] - LOG2[i]) * f) >> 8);
}

PF2 void tj_pitch(u8 *c)
{
    s32 semi = 0, fade = 4096, i, x = tj_ratio;
    if (!tj_mt && x != 4096) {
        semi = semis(x);
        if (tj_mode && (tj_touch || tj_sp < Q) && x < 1024)
            fade = x * 4;                       /* the brake's last quarter: the held notes fade out */
    }
    tj_semi = semi;
    if (!semi && fade == 4096)
        return;
    for (i = 0; i < 12; i++, c += 142) {
        u32 mc = MACHINES[i];
        s32 w;
        if (mc > 44)
            continue;
        if (semi && (mc < 32 ? TUNE_LO >> mc : TUNE_HI >> (mc - 32)) & 1) {
            w = *(s16 *)(c + 64) + semi;
            *(u16 *)(c + 64) = (u16)(w < 0 ? 0 : w > 0x7FFF ? 0x7FFF : w);
        }
        if (fade < 4096 && (mc < 32 || (AUD_HI >> (mc - 32)) & 1))
            *(u16 *)(c + 124) = (u16)((*(u16 *)(c + 124) * fade) >> 12);
    }
}

/* ---- knobs ---- */
static void pop(s32 n)
{
    if (tj_pop != n)
        tj_phs = 0;
    tj_pop = (u8)n;
    tj_popt = 2250;                             /* 1.5 s */
}

static s32 step(s32 d, s32 held) { return d * (held ? 5 : 1); }

/* TEST35: detents: knob n moves its setting one step every k detents (a turn back, or another knob, starts over) */
static s8 tj_acc DATA = 0;
static u8 tj_acck DATA = 0;
static s32 det(s32 n, s32 d, s32 k)
{
    s32 a = tj_acck == n ? tj_acc : 0, q;
    if ((a > 0 && d < 0) || (a < 0 && d > 0))
        a = 0;
    a = clamp(a + d, -64, 64);
    q = a / k;
    tj_acc = (s8)(a - q * k);
    tj_acck = (u8)n;
    return q;
}
void tj_perf_knob(s32 n, s32 d);

s32 tj_enc_c(void *view, const u8 *ev)
{
    s32 n = *(const s32 *)(ev + 12), d = *(const s32 *)(ev + 16), held = ev[20], one = d > 0 ? 1 : d < 0 ? -1 : 0;
    if (view != tj_view)
        return 0;
    if (n == 9 || n < 1 || n > 8) {             /* LEVEL/DATA: the tempo, stock's (a glide gives way to it) */
        tj_gl = 0;
        return 0;
    }
    if (tj_func) {                              /* TEST34: [FUNC] held: G = the glide, H = the phrase */
        if (n == 7)
            tj_gld = (u8)clamp(tj_gld + one, 0, 5);
        else if (n == 8)
            tj_phr = (u8)clamp(tj_phr + one, 0, 3);
        tj_lease = 3000;
        REDRAW(view);
        return 1;
    }
    if (tj_page && (n == 2 || n == 3)) {        /* TEST34: PERFORM: B the DJ filter, C its RESO */
        tj_perf_knob(n, d);
    } else if (n == 1) {
        if (tj_mode && (tj_touch || held)) {    /* VINYL, platter held: walk the beat on (1/8 beat a click) */
            tj_debt = clamp(tj_debt + d * (BEAT / 8), 0, BEAT);
        } else {                                /* the ring: a click a step, whatever the turn's speed (TEST34) */
            s32 cap = RANGE[tj_range] * (Q / 100) * 16;
            tj_btgt = clamp(tj_btgt + one * 2620, -cap, cap);   /* 0.25 % a click; LOAD = how long it coasts */
        }
    } else if (n == 2) {                        /* TEST35: B LOAD (3 detents a step) */
        tj_load = (u8)clamp(tj_load + det(n, d, 3), 1, 8);
        pop(3);
    } else if (n == 3) {                        /* C START (2 detents a step; pressed: 0.5 s) */
        tj_start = (u8)clamp(tj_start + step(det(n, d, 2), held), 0, 30);
        tj_sstep = tj_start ? Q / (150 * tj_start) : Q;
        pop(5);
    } else if (n == 4) {                        /* D BRAKE (2 detents a step; pressed: 0.5 s) */
        tj_brake = (u8)clamp(tj_brake + step(det(n, d, 2), held), 0, 30);
        tj_bstep = tj_brake ? Q / (150 * tj_brake) : Q;
        pop(4);
    } else if (n == 5) {                        /* E RANGE (3 detents a step) */
        tj_range = (u8)clamp(tj_range + det(n, d, 3), 0, 3);
        pop(7);
    } else if (n == 6) {                        /* F PHASE: 1/360 beat a step (2 detents), pressed 10 */
        s32 c = det(n, d, 2) * (held ? 10 : 1);
        tj_debt = clamp(tj_debt + c * (BEAT / 360), -BEAT / 4, BEAT / 4);
        pop(8);
        tj_phs += c;
#ifndef NOLINK
    } else if (n == 7) {                        /* LINK (shelved): G MAN / LOCK; pressed: BAR / BEAT */
        if (held) {
            if (d)
                tl_bar = d > 0;
        } else if (d) {
            tl_mode = d > 0;
            if (!tl_mode)
                tl_rem = 0;
        }
        pop(6);
    } else if (n == 8 && tl_mode) {             /* LOCK: H trims the offset (0.1 ms, pressed 1 ms) */
        tl_off = (s16)clamp(tl_off + d * (held ? 10 : 1), -500, 500);
        pop(9);
#endif
    } else
        return 1;                               /* G, H: nothing */
    tj_lease = 3000;
    REDRAW(view);
    return 1;
}

/* ---- keys ---- */
s32 tj_keys(void *view, u32 code, s32 down);
void tj_glide(void *view, s32 g);
void tj_perf_enter(void);
static void open_jog(void *view)
{
    tj_view = view;
    tj_page = 0;
    tj_open_t = TEMPO;
    tj_touch = tj_func = tj_pop = 0;
    tj_popt = 0;
    tj_lease = 3000;
    REDRAW(view);
}

s32 tj_key_c(void *view, const u8 *ev)
{
    u32 code = *(const volatile u32 *)(ev + 12) & 0xFF, f = *(const volatile u32 *)(ev + 16);
    if (view != tj_view) {
        if (code == 8 && (f & 0xB) == 0x9) {    /* [TEMPO] held (no FUNC) */
            open_jog(view);
            return 1;
        }
        if (code == 40 && (f & 1)) {            /* knob A pushed in the TEMPO menu */
            open_jog(view);
            tj_skip = 1;                        /* its release is not a touch */
            return 1;
        }
        return STOCK_KEY(view, ev);
    }
    if (code == 8)
        return 1;                               /* the hold's repeats and release */
    if (code == 40) {
        if (tj_skip) {
            if (!(f & 1))
                tj_skip = 0;
            return 1;
        }
        tj_touch = (f & 1) && tj_mode;
        tj_lease = 3000;
        REDRAW(view);
        return 1;
    }
    if (code == 1) {                            /* [FUNC]: the settings while held (and stock's PREP on release) */
        tj_func = f & 1;
        REDRAW(view);
        return STOCK_KEY(view, ev);
    }
    if (tj_keys(view, code, (f & 1) && !(f & 8)))   /* TEST34: MT, the tools, PERFORM */
        return 1;
    if (code > 40 && code <= 47)
        return 1;
    if (code == 14 || code == 15)
        tj_gl = 0;                              /* [UP] / [DOWN] change the tempo: a glide gives way */
    return STOCK_KEY(view, ev);
}

/* the TEMPO view is gone: JOG ends, a held platter lets go */
void tj_gone(void *view)
{
    if (view == tj_view) {
        if (tj_gl == 1 || tj_gl == 2) {         /* TEST34: leaving mid-glide: the target at once */
            tj_gl_cur = tj_gl_tgt;
            tj_gl = 3;
            SETTER(view, tj_gl_tgt >> 8);
        }
        tj_view = 0;
        tj_touch = tj_func = 0;
        tj_lease = 0;
    }
}

/* ---- drawing (y up, 0 = bottom row) ---- */
static const s16 SIN[65] = {
    0, 1606, 3196, 4756, 6270, 7723, 9102, 10394, 11585, 12665, 13623, 14449, 15137, 15679, 16069, 16305,
    16384, 16305, 16069, 15679, 15137, 14449, 13623, 12665, 11585, 10394, 9102, 7723, 6270, 4756, 3196, 1606,
    0, -1606, -3196, -4756, -6270, -7723, -9102, -10394, -11585, -12665, -13623, -14449, -15137, -15679, -16069, -16305,
    -16384, -16305, -16069, -15679, -15137, -14449, -13623, -12665, -11585, -10394, -9102, -7723, -6270, -4756, -3196,
    -1606, 0};

static s32 sn(u32 a)                             /* sin of a / 65536 turns, Q14 */
{
    s32 i = (a >> 10) & 63, f = a & 1023;
    return SIN[i] + (((SIN[i + 1] - SIN[i]) * f) >> 10);
}

#define CX 30
#define CY 35
static void *cv DATA = 0;
static void px(s32 x, s32 y) { FILL(cv, x, y, x, y, 1); }

static void pt(s32 r4, u32 a, s32 *x, s32 *y)  /* r in 1/16 px, a in 1/65536 turns from 12 o'clock, clockwise */
{
    *x = CX + ((r4 * sn(a) + (1 << 17)) >> 18);
    *y = CY + ((r4 * sn(a + 16384) + (1 << 17)) >> 18);
}

static void line(s32 x0, s32 y0, s32 x1, s32 y1)
{
    s32 dx = x1 > x0 ? x1 - x0 : x0 - x1, dy = y1 > y0 ? y0 - y1 : y1 - y0;
    s32 sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, e = dx + dy, e2;
    for (;;) {
        px(x0, y0);
        if (x0 == x1 && y0 == y1)
            break;
        e2 = 2 * e;
        if (e2 >= dy) {
            e += dy;
            x0 += sx;
        }
        if (e2 <= dx) {
            e += dx;
            y0 += sy;
        }
    }
}

static void ray(u32 a, s32 r0, s32 r1)
{
    s32 x0, y0, x1, y1;
    pt(r0 * 16, a, &x0, &y0);
    pt(r1 * 16, a, &x1, &y1);
    line(x0, y0, x1, y1);
}

static void circle(s32 r)                       /* midpoint circle */
{
    s32 x = r, y = 0, e = 1 - r;
    while (x >= y) {
        px(CX + x, CY + y); px(CX - x, CY + y); px(CX + x, CY - y); px(CX - x, CY - y);
        px(CX + y, CY + x); px(CX - y, CY + x); px(CX + y, CY - x); px(CX - y, CY - x);
        y++;
        if (e < 0)
            e += 2 * y + 1;
        else {
            x--;
            e += 2 * (y - x) + 1;
        }
    }
}

static void disc(s32 r)                         /* filled */
{
    s32 y, x;
    for (y = -r; y <= r; y++) {
        for (x = r; x * x + y * y > r * r + (r >> 1); x--)
            ;
        FILL(cv, CX - x, CY + y, CX + x, CY + y, 1);
    }
}

/* a dashed circle turning with the record: per dashes a turn, on/256 of each lit */
static void dashes(s32 r, u32 phase, s32 per, s32 on)
{
    s32 i, n = r * 10, x, y, lx = -99, ly = -99;
    for (i = 0; i < n; i++) {
        u32 a = (u32)(i * 65536 / n);
        if ((((a - phase) & 0xFFFF) * per >> 8 & 255) >= (u32)on)
            continue;
        pt(r * 16, a, &x, &y);
        if (x != lx || y != ly)
            px(x, y);
        lx = x;
        ly = y;
    }
}

static void platter(u32 bar, s32 touch)
{
    s32 i, x, y;
    for (i = 0; i < 4; i++)                     /* beat ticks, the one longer */
        ray((u32)i << 14, 27, i ? 28 : 29);
    if (!tj_disp) {                             /* VINYL: a record */
        u32 st = (u32)(tj_strobe >> 7);
        circle(26);
        for (i = 0; i < 20; i++) {              /* strobe dots: still at the set tempo, drifting when off it */
            pt(376, (u32)(i * 65536 / 20) + st, &x, &y);
            px(x, y);
        }
        dashes(19, bar, 6, 141);
        dashes(15, bar + 4000, 5, 154);
        if (touch) {                            /* touched: the label lights */
            disc(9);
            pt(0, 0, &x, &y);
            FILL(cv, x, y, x, y, 0);
        } else {
            circle(9);
            ray(bar, 3, 9);
            px(CX, CY);
        }
        ray(bar, 10, 21);                       /* the marker: once a bar, 12 o'clock = the one */
    } else {                                    /* CDJ: the jog display */
        circle(26);                             /* TEST35: the rings turn with the platter, as the record's */
        dashes(24, bar, 12, 154);               /* grooves do: an outer dashed ring and the ticks */
        for (i = 0; i < 32; i += 2)
            ray(((u32)i << 11) + bar, 20, 21);
        for (i = 17; i <= 22; i++) {            /* the operation marker */
            s32 k, n = i;
            for (k = -n / 2; k <= n / 2; k++) {
                pt(i * 16, bar + (u32)(k * 4000 / n), &x, &y);
                px(x, y);
            }
        }
        ray(bar, 11, 17);
        circle(10);
        if (touch)
            disc(8);
    }
}

static char *num(char *q, u32 v)                /* decimal */
{
    char t[12];
    s32 n = 0;
    do {
        t[n++] = (char)('0' + v % 10);
        v /= 10;
    } while (v);
    while (n)
        *q++ = t[--n];
    *q = 0;
    return q;
}

static char *fix(char *q, s32 v, s32 dec, s32 sign)  /* v / 10^dec with dec decimals */
{
    u32 a = v < 0 ? (u32)-v : (u32)v, p = dec == 2 ? 100 : 10;
    char t[4];
    if (sign)
        *q++ = v > 0 ? '+' : v < 0 ? '-' : ' ';
    else if (v < 0)
        *q++ = '-';
    q = num(q, a / p);
    *q++ = '.';
    num(t, a % p + p);                          /* leading zero */
    *q++ = t[1];
    if (dec == 2)
        *q++ = t[2];
    *q = 0;
    return q;
}

static void meter(s32 dev, s32 y)               /* dev: 1/100 % */
{
    s32 x0 = 68, x1 = 124, m = 96, e, k = RANGE[tj_range] * 100;
    FILL(cv, x0, y, x1, y, 1);
    FILL(cv, m, y - 2, m, y + 2, 1);
    FILL(cv, x0, y - 1, x0, y + 1, 1);
    FILL(cv, x1, y - 1, x1, y + 1, 1);
    e = m + clamp(dev, -k, k) * (x1 - m) / k;
    if (e != m)
        FILL(cv, e < m ? e : m, y + 1, e < m ? m : e, y + 2, 1);
}

static void setting(s32 n, char *b)             /* the value of knob n's setting */
{
    if (n == 3)
        num(b, tj_load);
    else if (n == 4 || n == 5) {
        b = fix(b, n == 4 ? tj_brake : tj_start, 1, 0);
        *b++ = 'S';
        *b = 0;
    } else if (n == 7) {
        if (tj_range == 3) {
            b[0] = 'W'; b[1] = 'I'; b[2] = 'D'; b[3] = 'E'; b[4] = 0;
        } else {
            b = num(b, RANGE[tj_range]);
            *b++ = '%';
            *b = 0;
        }
    } else if (n == 6) {
        const char *w = tl_mode ? (tl_bar ? "LOCK BAR" : "LOCK BEAT") : "MAN";
        while ((*b++ = *w++))
            ;
    } else if (n == 9) {                        /* the offset, ms */
        b = fix(b, tl_off, 1, 1);
        b[0] = 'M'; b[1] = 'S'; b[2] = 0;
    } else if (n == 10) {                       /* TEST34: MASTER TEMPO */
        b[0] = 'O'; b[1] = tj_mt ? 'N' : 'F'; b[2] = tj_mt ? 0 : 'F'; b[3] = 0;
    } else if (n == 11) {                       /* TEST34: the tempo a glide stored */
        fix(b, TEMPO * 5 / 6, 2, 0);
    } else {                                    /* PHASE: the clicks of this gesture, in ms (tenths) */
        s32 t = TEMPO;
        b = fix(b, t ? tj_phs * 200000 / t : 0, 1, 1);
        b[0] = 'M'; b[1] = 'S'; b[2] = 0;
    }
}

static const char LETTER[13] = "???BDCGEFH??";   /* TEST35: the knob of each setting */
static const char *const NAMES[12] = {0, 0, 0, "LOAD", "BRAKE", "START", "LINK", "RANGE", "PHASE", "OFFSET",
                                      "MASTER TEMPO", "TEMPO SET"};

#ifndef NOLINK
/* LINK: the phase meter across the top of the right panel, as a CDJ's: one bar in four cells, the master above
 * (the beat it last sent), the Syntakt below (where it is in its bar); a cell lit = that beat */
TL static void cells(s32 y, s32 lit)
{
    s32 i, x;
    for (i = 0; i < 4; i++) {
        x = 66 + i * 15;
        if (i + 1 == lit)
            FILL(cv, x, y, x + 13, y + 2, 1);
        else {
            FILL(cv, x, y, x + 13, y, 1);
            FILL(cv, x, y + 2, x + 13, y + 2, 1);
            FILL(cv, x, y, x, y + 2, 1);
            FILL(cv, x + 13, y, x + 13, y + 2, 1);
        }
    }
}

TL static void phase_text(char *b, s32 t)       /* the error: IN PHASE, or signed ms: +3.1MS late, -2.0MS early */
{
    s32 ms = t ? tl_err * 20 / (t * 3) : 0;     /* 0.1 ms (a 0.1 ms = 0.15 blocks of t) */
    const char *w = "IN PHASE";
    if (ms < 5 && ms > -5) {
        while ((*b++ = *w++))
            ;
        return;
    }
    b = fix(b, ms, 1, 1);
    b[0] = 'M'; b[1] = 'S'; b[2] = 0;
}

TL static void link_top(s32 syn)                   /* the meter and the line under it; syn: the Syntakt's beat 1-4, 0 */
{
    char b[24], *q = b;
    const char *w;
    s32 live = LIVE();
    cells(60, live ? tl_bb : 0);
    cells(56, syn);
    w = tl_ext ? "SYNC " : tl_mode ? (tl_bar ? "LOCK " : "LOCK1 ") : "MAN ";
    while (*w)
        *q++ = *w++;
    if (!live) {
        w = "NO LINK";
        while ((*q++ = *w++))
            ;
    } else {
        *q++ = 'M';
        q = num(q, tl_dk);
        if (tl_mt) {
            *q++ = ' ';
            fix(q, tl_mt * 5 / 6, 2, 0);
        } else
            *q = 0;
    }
    TEXT(cv, F_SML, 96, 48, 2, "%s", b);
}
#endif

void tj_tags(void *c);
void tj_perform(void *c, s32 dev);
void tj_commit(void *view);

PF void tj_draw(void *view, void *c)
{
    s32 t = tl_mode && tl_mt ? tl_mt : TEMPO, r = tj_rate, dev, src, link, dy;
    char b[24];
    if (view != tj_view) {
        STOCK_DRAW(view, c);
        return;
    }
    cv = c;
    tj_lease = 3000;
    tj_commit(view);                            /* TEST34: a glide that arrived: stored by the TEMPO view itself */
    if (tj_gl)
        t = tj_gl_cur >> 8;
    FILL(c, 0, 0, 127, 63, 0);
    if (tj_page) {                              /* TEST35: PERFORM is the whole screen */
        tj_perform(c, 0);
        return;
    }
    platter((u32)tj_pos / 675 * 1024 / 1000, tj_touch);
    tj_tags(c);                                 /* the phrase counter (in place of "(A)") and the MT tag */
    link = LIVE() || tl_mode;
    dy = link ? 3 : 0;                          /* the LINK lines push the rest down a little */
    src = CLK_SRC();
    if (src == 1 || (src && EXT_ST() == 3)) {   /* the Syntakt follows an external clock: nothing to jog */
#ifndef NOLINK
        if (LIVE() && tl_ext) {                 /* SYNC: the bridge's clock; the meter shows how close */
            link_top(tl_run && tl_f8 >= 0 ? tl_f8 / 24 + 1 : 0);
            TEXT(c, F_BIG, 96, 36, 2, "%s", "SYNC");
            TEXT(c, F_LBL, 96, 28, 2, "%s", "EXT CLOCK");
            phase_text(b, tl_mt);
            TEXT(c, F_BIG, 96, 12, 2, "%s", b);
            return;
        }
#endif
        TEXT(c, F_BIG, 96, 46, 2, "%s", "EXT");
        TEXT(c, F_BIG, 96, 34, 2, "%s", "CLOCK");
        TEXT(c, F_LBL, 96, 20, 2, "%s", "THE JOG RESTS:");
        TEXT(c, F_LBL, 96, 12, 2, "%s", "THE SYNTAKT");
        TEXT(c, F_LBL, 96, 4, 2, "%s", "IS SLAVED");
        return;
    }
    dev = t ? (r - t) * 10000 / t : 0;          /* 1/100 % */
    if (tj_func) {                              /* the settings, the memories and the tools at a glance */
        static const char *const L[6] = {"LOAD", "STRT", "BRK", "RNG", "PHR", "GLD"};
        static const u8 SET[4] = {3, 5, 4, 7};  /* TEST35: in knob order B C D E */
        static const char *const R[6] = {"T1 130", "T2 140", "T3 150", "T4 160", "NO RST", "YES P1"};
        s32 i, y;
        for (i = 0; i < 6; i++) {
            y = 50 - 9 * i;
            if (i < 4)
                setting(SET[i], b);
            else {
                s32 v = i == 4 ? PHRS[tj_phr] : GLDS[tj_gld];
                char *q = num(b, (u32)v);
                if (i == 5) {
                    if (!v) {
                        b[0] = 'C'; b[1] = 'U'; b[2] = 'T'; b[3] = 0;
                    } else {
                        q[0] = 'B'; q[1] = 0;
                    }
                }
            }
            TEXT(c, F_SML, 63, y, 0, "%s", L[i]);
            TEXT(c, F_SML, 97, y, 4, "%s", b);
            TEXT(c, F_SML, 101, y, 0, "%s", R[i]);
        }
        return;
    }
#ifndef NOLINK
    if (link) {
        link_top(PLAYING == 1 ? (s32)(tj_pos / BEAT) + 1 : 0);
        TEXT(c, F_LBL, 96, 41, 2, "%s", tj_mode ? "VINYL" : "CDJ");
    } else
#endif
    {
        TEXT(c, F_BIG, 96, 54, 2, "%s", tj_mode ? "VINYL" : "CDJ");
    }
    if (tj_popt && tj_pop) {                    /* a setting just turned */
        setting(tj_pop, b);
        TEXT(c, F_LBL, 96, 37 - dy, 2, "%s", NAMES[tj_pop]);
        TEXT(c, tj_pop == 6 || tj_pop == 10 ? F_BIG : F_VAL, 96, 24 - dy, 2, "%s", b);
        if (tj_pop == 10)
            TEXT(c, F_LBL, 96, 16 - dy, 2, "%s", "(YES)");
        else if (tj_pop != 11) {
            b[0] = '('; b[1] = LETTER[tj_pop]; b[2] = ')'; b[3] = 0;
            TEXT(c, F_LBL, 96, 16 - dy, 2, "%s", b);
        }
    } else {
        char *q;
        fix(b, r * 5 / 6, 2, 0);                /* the live BPM: rate / 120, two decimals */
        TEXT(c, F_VAL, 96, 33 - dy, 2, "%s", b);
        if (tj_gl) {                            /* TEST34: where the glide goes */
            b[0] = 'T'; b[1] = 'O'; b[2] = ' ';
            fix(b + 3, tj_gl_tgt * 5 / 6 >> 8, 2, 0);
            TEXT(c, F_LBL, 96, 26 - dy, 2, "%s", b);
        } else if (!tj_mt && tj_semi) {         /* TEST34: the pitch follows: semitones */
            q = fix(b, tj_semi * 100 / 256, 2, 1);
            q[0] = ' '; q[1] = 'S'; q[2] = 'T'; q[3] = 0;
            TEXT(c, F_LBL, 96, 26 - dy, 2, "%s", b);
        } else
            TEXT(c, F_LBL, 96, 26 - dy, 2, "%s", "(LEV)");
        if (tj_touch)
            TEXT(c, F_BIG, 96, 12 - dy / 3, 2, "%s", tj_sp ? "BRAKE" : "HOLD");
        else if (tj_sp < Q)
            TEXT(c, F_BIG, 96, 12 - dy / 3, 2, "%s", "START");
        else if (tj_gl)
            TEXT(c, F_BIG, 96, 12 - dy / 3, 2, "%s", "GLIDE");
        else if (PLAYING == 2)
            TEXT(c, F_BIG, 96, 12 - dy / 3, 2, "%s", "PAUSE");
#ifndef NOLINK
        else if (link && LIVE() && PLAYING == 1) {   /* how far off the master's beat */
            phase_text(b, t);
            TEXT(c, F_BIG, 96, 11, 2, "%s", b);
        }
#endif
        else {
            q = fix(b, dev, 2, 1);
            q[0] = '%';
            q[1] = 0;
            TEXT(c, F_BIG, 96, 12 - dy / 3, 2, "%s", b);
        }
    }
    if (tj_gl) {                                /* TEST34: the glide's progress in place of the pitch meter */
        s32 span = tj_gl_tgt - tj_gl_from, k = span ? (tj_gl_cur - tj_gl_from) / (span / 56 ? span / 56 : 1) : 56;
        FILL(c, 68, 6, 124, 6, 1);
        FILL(c, 68, 5, 68, 7, 1);
        FILL(c, 124, 5, 124, 7, 1);
        k = clamp(k, 0, 56);
        if (k)
            FILL(c, 68, 7, 68 + k, 8, 1);
    } else
        meter(dev, 6);
}

/* ---- TEST34: the tools (their own chunk) ---- */
/* a glide to g (BPM x 120) over GLD bars at the mean tempo; CUT = at once. Equal steps a block, clamped at the
 * target in the audio interrupt; once there, tj_commit stores it through the TEMPO view's own setter (pattern or
 * project tempo, as the stock menu does) and the setting takes over in the same block. */
PF2 void tj_glide(void *view, s32 g)
{
    s32 from, n, d, bars = GLDS[tj_gld];
    if ((tl_mode && tl_mt) || g < 3600 || g > 36000)
        return;
    from = tj_gl ? tj_gl_cur : TEMPO << 8;
    if (!bars) {
        tj_gl = 0;
        SETTER(view, g);
        return;
    }
    if (from == g << 8)
        return;
    n = bars * 4 * (BEAT / ((((from >> 8) + g) >> 1)));   /* blocks: a beat = BEAT / tempo word blocks */
    d = (g << 8) - from;
    if (d < 0)
        d = -d;
    tj_gl_step = (d + n / 2) / n ? (d + n / 2) / n : 1;   /* rounded: GLD bars to within a step */
    tj_gl_from = from;
    tj_gl_cur = from;
    tj_gl_tgt = g << 8;
    tj_gl = 1;
}

PF2 void tj_commit(void *view)
{
    if (tj_gl == 2) {
        tj_gl = 3;
        SETTER(view, tj_gl_tgt >> 8);
        pop(11);
    }
}

/* PERFORM's DJ filter on the master filter's knob values (master-filter's mf_p, or perf-filter's pf_p: the same
 * layout, TYPE FREQ RESO RET ON TRIM CMP, with the smoothed FREQ 19 bytes under it), so no new DSP: the analog FX
 * block's filter. Centre = THRU; left LP2 closing; right HP2 opening. TEST35: B moves a fine position (64 steps a
 * detent at a slow turn, 128 fast; 4032 a side) and the cutoff is a 16-bit word: while PERFORM owns the filter, the
 * audio interrupt (tj_tap, before the filter's own hook in the same block) glides its word to the target (~21 ms)
 * and writes it into the filter's smoothed FREQ (the OS's cutoff CVs take all 16 bits; the filter's own glide
 * toward the knob byte then moves it by under 1/64 of a step): an analog knob's sweep, no steps. The byte follows
 * (rounded); anyone else changing it (the FX page, MIDI) takes the filter back. Crossing to a side starts at its
 * open end at once. */
#define MF_TYPE 0
#define MF_FREQ 1
#define MF_RESO 2
#define MF_ON 4
#define FSIDE 4032                              /* tj_fp's range a side */
PF2 static void flt(void)
{
    u8 *p = tj_mfp;
    s32 f = tj_fp, side = f < 0 ? 1 : f > 0 ? 3 : 7;
    if (!p)
        return;
    tj_fpos = (s8)(f / 64);
    tj_fown = 0;                                /* (the interrupt waits while this changes it) */
    if (side == 7) {
        p[MF_TYPE] = 7;
        p[MF_ON] = 1;
        return;
    }
    tj_fqt = side == 1 ? 0x7F00 + f * (119 * 256) / FSIDE : f * (110 * 256) / FSIDE;
    if (side != p[MF_TYPE] || !p[MF_ON]) {      /* from THRU, OFF or the other side: the open end at once */
        tj_fq = side == 1 ? 0x7F00 : 0;
        *(s32 *)(p - 19) = tj_fq << 16;
        p[MF_FREQ] = (u8)(tj_fq >> 8);
        p[MF_TYPE] = (u8)side;
        p[MF_ON] = 1;
    }
    tj_fb = p[MF_FREQ];
    tj_fown = (u8)side;                         /* the audio interrupt takes it from here */
}

PF2 void tj_perf_enter(void)                     /* B starts where the master filter is */
{
    u8 *p = tj_mfp;
    s32 w;
    tj_fp = 0;
    tj_fpos = 0;
    tj_fown = 0;
    if (!p || !p[MF_ON])
        return;
    w = *(s32 *)(p - 19) >> 16;                 /* where the filter is now (its smoothed FREQ) */
    tj_fq = w;
    if (p[MF_TYPE] == 1)
        tj_fp = -clamp((0x7F00 - w) * FSIDE / (119 * 256), 1, FSIDE);
    else if (p[MF_TYPE] == 3)
        tj_fp = clamp(w * FSIDE / (110 * 256), 1, FSIDE);
    tj_fpos = (s8)(tj_fp / 64);
}

PF2 void tj_perf_knob(s32 n, s32 d)
{
    u8 *p = tj_mfp;
    if (!p)
        return;
    if (n == 2) {                               /* slow: 64 a detent (63 detents a side), fast: 128 */
        s32 e = d * (d > 2 || d < -2 ? 128 : 64);
        if (tj_fp && ((tj_fp < 0) != (tj_fp + e < 0)) && tj_fp + e)
            e = -tj_fp;                         /* a sweep stops at THRU before it crosses to the other side */
        tj_fp = clamp(tj_fp + e, -FSIDE, FSIDE);
        flt();
    } else                                      /* C: RESO, a step a detent (the filter glides it) */
        p[MF_RESO] = (u8)clamp(p[MF_RESO] + clamp(d, -2, 2), 0, 127);
}

/* TEST35, the audio interrupt (from tj_copy, before the filter's own hook in the same block): the cutoff glides
 * to PERFORM's target, then PERFORM's spectrum tap (only while PERFORM is on screen) */
PF2 void tj_tap(void)
{
    u8 *p = tj_mfp;
    spec_t *s = tj_spec;
    if (tj_fown && p) {
        if (!p[MF_ON] || p[MF_TYPE] != tj_fown || p[MF_FREQ] != tj_fb)
            tj_fown = 0;                        /* switched off, or changed from elsewhere: theirs again */
        else {
            s32 d = tj_fqt - tj_fq;
            tj_fq = d < 8 && d > -8 ? tj_fqt : tj_fq + (d >> 5);
            *(s32 *)(p - 19) = tj_fq << 16;
            tj_fb = (u8)((tj_fq + 128) >> 8 > 127 ? 127 : (tj_fq + 128) >> 8);
            p[MF_FREQ] = tj_fb;
        }
    }
    if (!s || !tj_spon)
        return;
    tj_spon--;
    {
        const volatile s32 *m = (const volatile s32 *)SPX;
        u32 w = tj_fw, dw = tj_dw, n = tj_dn, i;
        s32 a = tj_dacc, v;
        for (i = 0; i < 32; i++, m += 2) {
            v = (m[0] >> 14) + (m[1] >> 14);   /* L + R: each at full scale 2^28 (the bus is x8 before the DACs) */
            v = v > 32767 ? 32767 : v < -32768 ? -32768 : v;
            s->full[w] = (s16)v;
            w = (w + 1) & (NFFT - 1);
            a += v;
            if (++n == 8) {                     /* 6 kHz for the lows: the mean of 8 */
                s->dec[dw] = (s16)(a >> 3);
                dw = (dw + 1) & (NFFT - 1);
                a = 0;
                n = 0;
            }
        }
        tj_fw = (u16)w;
        tj_dw = (u16)dw;
        tj_dn = (u8)n;
        tj_dacc = a;
    }
}

PF2 s32 tj_keys(void *view, u32 code, s32 down)
{
    if (code == 12) {                           /* [YES]: MASTER TEMPO; [FUNC] + [YES]: the phrase from bar 1 */
        if (down) {
            if (tj_func)
                tj_bars = 0;
            else {
                tj_mt ^= 1;
                pop(10);
            }
        }
    } else if (code == 13 && tj_func) {         /* [FUNC] + [NO]: back to the tempo JOG opened with */
        if (down)
            tj_glide(view, tj_open_t);
    } else if (code == 16 || code == 17) {      /* [LEFT] JOG, [RIGHT] PERFORM */
        if (down && tj_page != (code == 17)) {
            tj_page = code == 17;
            tj_popt = 0;
            if (tj_page)
                tj_perf_enter();
        }
    } else if (code >= 24 && code <= 27 && tj_func) {   /* [FUNC] + [TRIG 1-4]: 130 140 150 160 */
        if (down)
            tj_glide(view, (130 + 10 * (s32)(code - 24)) * 120);
    } else if (code == 41 && tj_page) {         /* B pushed: the filter snaps to THRU; [FUNC]: the filter off */
        if (down && tj_mfp) {
            tj_fp = 0;
            tj_fpos = 0;
            tj_fown = 0;
            if (tj_func)
                tj_mfp[MF_ON] = 0;
            else if (tj_mfp[MF_ON])
                flt();
        }
    } else
        return 0;
    tj_lease = 3000;
    REDRAW(view);
    return 1;
}

/* the phrase counter under the platter (the last 4 bars inverted, blinking a bar), the MT tag in the corner */
PF void tj_tags(void *c)
{
    char b[12], *q;
    u32 len = PHRS[tj_phr], bar = tj_bars % len + 1;
    q = num(b, bar);
    *q++ = '/';
    num(q, len);
    TEXT(c, F_SML, CX, 1, 2, "%s", b);
    if (len - bar < 4 && PLAYING == 1) {        /* the last 4 bars: brackets, blinking with the beat */
        if (tj_pos < 2 * BEAT || PLAYING != 1) {
            FILL(c, CX - 15, 0, CX - 15, 7, 1);
            FILL(c, CX - 15, 0, CX - 13, 0, 1);
            FILL(c, CX - 15, 7, CX - 13, 7, 1);
            FILL(c, CX + 15, 0, CX + 15, 7, 1);
            FILL(c, CX + 13, 0, CX + 15, 0, 1);
            FILL(c, CX + 13, 7, CX + 15, 7, 1);
        }
    }
    if (tj_mt) {                                /* MASTER TEMPO on: a framed MT in the corner */
        FILL(c, 0, 55, 13, 55, 1);
        FILL(c, 0, 63, 13, 63, 1);
        FILL(c, 0, 55, 0, 63, 1);
        FILL(c, 13, 55, 13, 63, 1);
        TEXT(c, F_SML, 7, 57, 2, "%s", "MT");
    }
}

/* TEST35: per column (20 Hz .. 20 kHz, log, 128 px + the edge): bit 15 = the 48 kHz FFT (else the 6 kHz one),
 * the rest = its bin x 16 (make_tables in the notes) */
static const u16 COLB[129] = {0x000e, 0x000e, 0x000f, 0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0018, 0x0019, 0x001a, 0x001c, 0x001d, 0x001f, 0x0021, 0x0022, 0x0024, 0x0026, 0x0029, 0x002b, 0x002d, 0x0030, 0x0032, 0x0035, 0x0038, 0x003b, 0x003f, 0x0042, 0x0046, 0x004a, 0x004e, 0x0052, 0x0057, 0x005c, 0x0061, 0x0066, 0x006c, 0x0072, 0x0078, 0x007f, 0x0086, 0x008e, 0x0095, 0x009e, 0x00a7, 0x00b0, 0x00ba, 0x00c4, 0x00cf, 0x00db, 0x00e7, 0x00f4, 0x0102, 0x0110, 0x011f, 0x012f, 0x0140, 0x0152, 0x0165, 0x0179, 0x018e, 0x01a4, 0x01bc, 0x01d4, 0x01ef, 0x020a, 0x0227, 0x0246, 0x0267, 0x0289, 0x02ae, 0x02d4, 0x02fc, 0x0327, 0x806b, 0x8070, 0x8077, 0x807d, 0x8084, 0x808c, 0x8094, 0x809c, 0x80a5, 0x80ae, 0x80b8, 0x80c2, 0x80cd, 0x80d8, 0x80e4, 0x80f1, 0x80fe, 0x810d, 0x811c, 0x812b, 0x813c, 0x814e, 0x8160, 0x8174, 0x8189, 0x819f, 0x81b6, 0x81cf, 0x81e8, 0x8204, 0x8221, 0x823f, 0x825f, 0x8281, 0x82a5, 0x82cb, 0x82f3, 0x831d, 0x834a, 0x8379, 0x83aa, 0x83df, 0x8416, 0x8451, 0x848e, 0x84cf, 0x8514, 0x855d, 0x85aa, 0x85fb, 0x8650, 0x86ab, 0x870a};
/* TEST35: the 2-pole low-pass curve drawn on PERFORM, px from the 0 dB row (1.23 dB a px), 8 RESO rows (q 0.7 ..
 * 9.7), x - cutoff from -64 to +64 px in steps of 2 (12.7 px an octave); the high-pass is its mirror */
static const s8 CURVE[8][65] = {
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -2, -3, -3, -4, -6, -7, -8, -10, -11, -12, -14, -15, -17, -19, -20, -22, -23, -25, -26, -28, -29, -31, -32, -34, -35, -37, -39, -40, -42, -43, -44, -44, -44, -44},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, -2, -3, -5, -7, -8, -10, -12, -13, -15, -17, -18, -20, -21, -23, -25, -26, -28, -29, -31, -32, -34, -35, -37, -38, -40, -42, -43, -44, -44, -44, -44},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 3, 1, -1, -3, -5, -7, -9, -11, -13, -15, -16, -18, -20, -21, -23, -24, -26, -28, -29, -31, -32, -34, -35, -37, -38, -40, -42, -43, -44, -44, -44, -44},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 6, 7, 8, 6, 3, 0, -3, -5, -7, -9, -11, -13, -15, -16, -18, -20, -21, -23, -24, -26, -28, -29, -31, -32, -34, -35, -37, -38, -40, -42, -43, -44, -44, -44, -44},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 10, 7, 3, 0, -3, -5, -7, -9, -11, -13, -15, -16, -18, -20, -21, -23, -24, -26, -28, -29, -31, -32, -34, -35, -37, -38, -40, -42, -43, -44, -44, -44, -44},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 3, 4, 5, 7, 10, 12, 8, 4, 0, -2, -5, -7, -9, -11, -13, -15, -16, -18, -20, -21, -23, -24, -26, -28, -29, -31, -32, -34, -35, -37, -38, -40, -42, -43, -44, -44, -44, -44},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 3, 4, 5, 7, 10, 12, 9, 4, 0, -2, -5, -7, -9, -11, -13, -15, -16, -18, -20, -21, -23, -24, -26, -28, -29, -31, -32, -34, -35, -37, -38, -40, -42, -43, -44, -44, -44, -44},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 3, 4, 5, 7, 11, 12, 9, 4, 0, -2, -5, -7, -9, -11, -13, -15, -16, -18, -20, -21, -23, -24, -26, -28, -29, -31, -32, -34, -35, -37, -38, -40, -42, -43, -44, -44, -44, -44},
};

/* ---- TEST35: PERFORM's screen, full width: the filter's curve over the mix's spectrum (20 Hz .. 20 kHz, log),
 * as an Ableton Auto Filter. The curve is drawn from the 2-pole shape at the cutoff (master-filter's measured
 * FREQ -> Hz map) and RESO: an illustration. The spectrum is the real mix after the filter: the OS's digital copy
 * of the main mix (for Overbridge main, the FX block's output in it), taken by tj_tap only while PERFORM is on
 * screen, two 256-point FFTs in the drawing (6 kHz for the lows, 48 kHz for the highs, one a redraw), levels that
 * rise at once and fall slowly, on a fixed scale (so closing the filter shows the level going) tilted +3 dB an
 * octave. Nothing runs on other pages. */
#define GY0  8                                  /* the graph: rows 8 .. 52, 0 dB at row 40 */
#define GY1  52
#define Y0DB 40
#define LG_PX(u) ((u) / 9)                      /* 1/16 log2 of the power (0.19 dB) -> px (1.7 dB): 50 dB */
#define SP_TOP 400                              /* the level 2 px under 0 dB: a full-scale sine's bin less 3 dB
                                                   (the main mix copy taken as full scale at 2^28: see tj_tap) */

PF2 __attribute__((noinline)) static s32 lg(u32 v)                            /* 16 x log2(v), 0 for 0 */
{
    s32 e = 31;
    if (!v)
        return 0;
    if (!(v >> 16)) { v <<= 16; e -= 16; }      /* the top bit in 5 steps */
    if (!(v >> 24)) { v <<= 8; e -= 8; }
    if (!(v >> 28)) { v <<= 4; e -= 4; }
    if (!(v >> 30)) { v <<= 2; e -= 2; }
    if (!(v >> 31)) { v <<= 1; e -= 1; }
    return e * 16 + (s32)((v >> 27) & 15);
}

PF2 __attribute__((noinline)) static void fft(spec_t *s)   /* 128-point complex, in place, a halving a stage */
{
    s32 *re = s->re, *im = s->im, tr, ti, c, sn;
    u32 i, j, k, m, h;
    for (i = 0, j = 0; i < NFFT / 2; i++) {
        if (i < j) {
            tr = re[i]; re[i] = re[j]; re[j] = tr;
            ti = im[i]; im[i] = im[j]; im[j] = ti;
        }
        m = NFFT >> 2;
        while (m && (j & m)) {
            j ^= m;
            m >>= 1;
        }
        j |= m;
    }
    for (h = 1; h < NFFT / 2; h <<= 1)
        for (k = 0; k < h; k++) {
            c = s->cs[k * (NFFT / 2) / h];      /* e^(-i pi k / h) */
            sn = s->sn[k * (NFFT / 2) / h];
            for (i = k; i < NFFT / 2; i += 2 * h) {
                j = i + h;
                tr = (re[j] * c + im[j] * sn) >> 14;
                ti = (im[j] * c - re[j] * sn) >> 14;
                re[j] = (re[i] - tr) >> 1;
                im[j] = (im[i] - ti) >> 1;
                re[i] = (re[i] + tr) >> 1;
                im[i] = (im[i] + ti) >> 1;
            }
        }
}

/* one 256-point real FFT (a 128-point complex one, even samples real, odd imaginary, then split): its levels */
PF2 __attribute__((noinline)) static void spectrum(spec_t *s, u32 hi)
{
    const s16 *src = hi ? s->full : s->dec;
    u32 w0 = hi ? tj_fw : tj_dw, i;
    s32 a, b, c, d, er, ei, or, oi, xr, xi;
    for (i = 0; i < NFFT / 2; i++) {
        s->re[i] = (src[(w0 + 2 * i) & (NFFT - 1)] * (s32)s->win[2 * i]) >> 15;
        s->im[i] = (src[(w0 + 2 * i + 1) & (NFFT - 1)] * (s32)s->win[2 * i + 1]) >> 15;
    }
    fft(s);
    for (i = 0; i < NFFT / 2; i++) {
        u32 n = (NFFT / 2 - i) & (NFFT / 2 - 1);
        a = s->re[i]; b = s->im[i]; c = s->re[n]; d = s->im[n];
        er = (a + c) >> 1; ei = (b - d) >> 1;   /* the even samples' spectrum */
        or = (b + d) >> 1; oi = (c - a) >> 1;   /* the odd ones' */
        xr = er + ((or * s->cs[i] + oi * s->sn[i]) >> 14);
        xi = ei + ((oi * s->cs[i] - or * s->sn[i]) >> 14);
        s->lv[hi][i] = (u16)lg((u32)(xr * xr) + (u32)(xi * xi));
    }
}

static spec_t *spec_new(void)                   /* once, at the first PERFORM: ~5 KB from the OS's heap */
{
    spec_t *s = (spec_t *)NEW(sizeof(spec_t));
    u32 i;
    if (!s)
        return 0;
    for (i = 0; i < NFFT; i++) {
        s->full[i] = s->dec[i] = 0;
        s->win[i] = (u16)(16384 - sn((u32)i * (65536 / NFFT) + 16384));   /* Hann, Q15 */
    }
    for (i = 0; i < NFFT / 2; i++) {
        s->cs[i] = (s16)sn((u32)i * (65536 / NFFT) + 16384);
        s->sn[i] = (s16)sn((u32)i * (65536 / NFFT));
        s->lv[0][i] = s->lv[1][i] = 0;
    }
    for (i = 0; i < 128; i++)
        s->col[i] = 0;
    s->ref = 0;
    s->turn = 0;
    return s;
}

PF2 __attribute__((noinline)) static s32 level(const spec_t *s, u32 x)         /* column x: the bins it spans (max), or between two (interpolated) */
{
    u32 a = COLB[x], b = COLB[x + 1], hi = a >> 15, i, e;
    s32 v;
    const u16 *lv = s->lv[hi];
    a &= 0x7FFF;
    b = (b >> 15) == hi ? b & 0x7FFF : a + 16;
    if (b >= a + 16) {
        e = b >> 4;
        if (e > NFFT / 2)
            e = NFFT / 2;
        for (v = 0, i = a >> 4; i < e; i++)
            if (lv[i] > v)
                v = lv[i];
        return v;
    }
    i = a >> 4;
    if (i >= NFFT / 2 - 1)
        return lv[NFFT / 2 - 1];
    return lv[i] + (((lv[i + 1] - lv[i]) * (s32)(a & 15)) >> 4);
}

static s32 hz_log(s32 w)                        /* FREQ word (Q8) -> log2(Hz), Q16: 5.9 Hz x 2^(0.0926 FREQ) */
{
    return 167819 + w * 24277 / 1024;
}

PF __attribute__((noinline)) static void hz_text(char *b, s32 l)             /* log2(Hz) Q16 -> 820HZ / 3.2K / 12K */
{
    s32 e = l >> 16, f = l & 0xFFFF, h;
    h = 65536 + (s32)(((u32)f * (u32)(43025 + ((f * 22512) >> 16))) >> 16);   /* 2^(f/65536), Q16, 0.3 % */
    h = e >= 16 ? h << (e - 16) : h >> (16 - e);
    if (h < 1000) {
        b = num(b, (u32)h);
        b[0] = 'H'; b[1] = 'Z'; b[2] = 0;
    } else if (h < 10000) {
        b = num(b, (u32)h / 1000);
        b[0] = '.';
        b = num(b + 1, (u32)h % 1000 / 100);
        b[0] = 'K'; b[1] = 0;
    } else {
        b = num(b, (u32)(h + 500) / 1000);
        b[0] = 'K'; b[1] = 0;
    }
}

static s32 curve(s32 x, s32 xc, s32 hp, s32 reso)   /* px from the 0 dB row; xc in 1/16 px */
{
    s32 d = x * 16 - xc, q, f, r0, r1, i, k, a, b;
    if (hp)
        d = -d;
    if (d <= -1024)
        return 0;
    if (d >= 1024)
        return -44;
    q = reso * 7;
    r0 = q / 127;
    f = q % 127;
    r1 = r0 < 7 ? r0 + 1 : 7;
    i = (d + 1024) >> 5;
    k = (d + 1024) & 31;
    a = CURVE[r0][i] + (((CURVE[r0][i + 1] - CURVE[r0][i]) * k) >> 5);
    b = CURVE[r1][i] + (((CURVE[r1][i + 1] - CURVE[r1][i]) * k) >> 5);
    return a + (b - a) * f / 127;
}

PF __attribute__((noinline)) static void fbar(s32 x0, s32 x1, s32 y, s32 f)  /* the DJ filter: centre notch, filled toward the side in use */
{
    s32 m = (x0 + x1) / 2, e = m + f * (x1 - m) / 63;
    FILL(cv, x0, y, x1, y, 1);
    FILL(cv, m, y - 2, m, y + 2, 1);
    FILL(cv, x0, y - 1, x0, y + 1, 1);
    FILL(cv, x1, y - 1, x1, y + 1, 1);
    if (e != m)
        FILL(cv, e < m ? e : m, y + 1, e < m ? m : e, y + 2, 1);
}

void tj_perform(void *c, s32 dev)
{
    char b[16], *q;
    u8 *p = tj_mfp;
    spec_t *s = tj_spec;
    s32 x, y, py = 0, on = p && p[MF_ON], type = p ? p[MF_TYPE] : 7, xc = 0, w, pk = 0, lv, top;
    (void)dev;
    cv = c;
    if (!s)
        s = tj_spec = spec_new();
    tj_spon = 300;                              /* the tap runs 0.2 s past the last redraw (then PERFORM is gone) */
    if (!p)
        TEXT(c, F_LBL, 64, 57, 2, "%s", "NO MASTER FILTER");
    else if (!on || type == 7) {
        TEXT(c, F_LBL, 0, 57, 0, "%s", "PERFORM");
        TEXT(c, F_LBL, 127, 57, 4, "%s", on ? "THRU" : "FILTER OFF");
    } else {
        w = *(s32 *)(p - 19) >> 16;
        TEXT(c, F_LBL, 0, 57, 0, "%s", type == 1 ? "LP2" : type == 3 ? "HP2" : "FLT");
        hz_text(b, hz_log(w));
        TEXT(c, F_LBL, 64, 57, 2, "%s", b);
        q = b;
        *q++ = 'R'; *q++ = 'E'; *q++ = 'S'; *q++ = ' ';
        num(q, p[MF_RESO]);
        TEXT(c, F_LBL, 127, 57, 4, "%s", b);
        xc = (hz_log(w) - 283247) * (127 * 16) / 653127;
    }
    for (y = GY0; y <= GY1; y += 3) {          /* 100 Hz, 1 kHz, 10 kHz: dotted */
        px(30, y);
        px(72, y);
        px(114, y);
    }
    for (x = 0; x < 128; x += 4)                /* 0 dB, dotted */
        px(x, Y0DB);
    if (s) {                                    /* the spectrum: one FFT a redraw, lows and highs in turn */
        s->turn ^= 1;
        spectrum(s, s->turn);
        for (x = 0; x < 128; x++) {
            lv = level(s, (u32)x);
            s->col[x] = (s16)(lv > s->col[x] ? lv : s->col[x] - 8);   /* falls ~20 dB a second */
            if (s->col[x] > pk)
                pk = s->col[x];
        }
        s->ref = (s16)pk;
        for (x = 0; x < 128; x += 2) {          /* every other column (lighter than the curve), on an absolute */
            lv = s->col[x] > s->col[x + 1] ? s->col[x] : s->col[x + 1];   /* scale, tilted +3 dB an octave */
            lv += (x - 72) * 5 / 4;             /* around 1 kHz (as analyzers show a mix: flatter, highs visible) */
            top = GY0 + LG_PX(lv - SP_TOP + 270);
            if (top >= GY0)
                FILL(c, x, GY0, x, top > GY1 ? GY1 : top, 1);
        }
    }
    if (on && type != 7 && p) {                 /* the curve, 2 px thick */
        for (x = 0; x < 128; x++) {
            y = Y0DB + curve(x, xc, type == 3, p[MF_RESO]);
            if (y < GY0 - 1)
                y = GY0 - 1;
            if (!x)
                py = y;
            FILL(c, x, py < y ? py : y, x, (py < y ? y : py) + 1, 1);   /* 2 px thick, joined */
            py = y;
        }
    } else if (on)                              /* THRU: flat */
        FILL(c, 0, Y0DB, 127, Y0DB + 1, 1);
    TEXT(c, F_SML, 0, 0, 0, "%s", "LP");
    TEXT(c, F_SML, 127, 0, 4, "%s", "HP");
    fbar(14, 113, 3, on ? tj_fpos : 0);
}

/* ---- SETTINGS > PERSONALIZE: "JOG DISPLAY  VINYL / CDJ" ---- */
const char tj_str_name[] = "JOG DISPLAY";

void tj_inv_tog(u32 *fn)                         /* [YES]: functor storage holds the menu view */
{
    u8 *v = (u8 *)*(u32 *)fn[0];
    tj_disp ^= 1;
    tj_mode = !tj_disp;                         /* TEST35: the look decides the behaviour (CDJ: a push does nothing) */
    tj_touch = 0;
    REDRAW(v + 56);
}

void tj_inv_delta(u32 *fn, u32 unused, s32 d)    /* [LEFT] / [RIGHT] */
{
    u8 *v = (u8 *)*(u32 *)fn[0];
    (void)unused;
    tj_disp = (u8)clamp(tj_disp + d, 0, 1);
    tj_mode = !tj_disp;
    tj_touch = 0;
    REDRAW(v + 56);
}

void tj_inv_draw(u32 *fn, u32 unused, void *c, s32 x, s32 y)   /* the value, as LED INTENSITY draws its own */
{
    (void)fn;
    (void)unused;
    TEXT2(c, FONT_LIST, x + 19, y + 2, 2, 0, 0, tj_disp ? "CDJ" : "VINYL");
}

extern void tj_inv_name(void);

/* replaces the boot's call of the PERSONALIZE menu's constructor: build it, then add our line as its last item */
void tj_pers(void *view)
{
    u32 f[4][4], *s, it;
    s32 i;
    PERS_CTOR(view);
    f[0][0] = NEW(1); f[0][2] = MGR_NAME; f[0][3] = (u32)tj_inv_name;
    s = (u32 *)NEW(4); *s = (u32)view;
    f[1][0] = (u32)s; f[1][2] = MGR_TOG; f[1][3] = (u32)tj_inv_tog;
    f[2][0] = NEW(1); f[2][2] = MGR_DRAW; f[2][3] = (u32)tj_inv_draw;
    s = (u32 *)NEW(4); *s = (u32)view;
    f[3][0] = (u32)s; f[3][2] = MGR_DELTA; f[3][3] = (u32)tj_inv_delta;
    for (i = 0; i < 4; i++)
        f[i][1] = 0;
    it = NEW(0x54);
    ITEM_CTOR((void *)it, f[0], f[1], f[2], f[3], -1, 8);
    APPEND(view, (void *)it);
    for (i = 0; i < 4; i++)
        FN_DTOR(f[i]);
}

__asm__(".section .text.pf2,\"ax\"\n"
        "    .globl tj_copy\n"
        "tj_copy:\n"                           /* TEST34: the audio interrupt's call of the copy builder (arg pushed) */
        "    move.l  4(%sp),-(%sp)\n"
        "    jsr     " COPY_FN "\n"
        "    addq.l  #4,%sp\n"
        "    move.l  %d0,-(%sp)\n"
        "    jsr     tj_pitch\n"
        "    jsr     tj_tap\n"                 /* TEST35: the DJ filter's glide, PERFORM's spectrum */
        "    move.l  (%sp)+,%d0\n"
        "    rts\n");

__asm__(".text\n"
        "    .globl tj_rate_isr, tj_enc, tj_key, tj_draw_v, tj_dtor0, tj_dtor1, tj_inv_name, tj_pers_v\n"
        "tj_rate_isr:\n"                        /* jsr from the audio interrupt: d0 = the rate; all else kept */
        "    lea     -12(%sp),%sp\n"
        "    movem.l %d1/%a0-%a1,(%sp)\n"
        "    jsr     tj_rate_c\n"
        "    movem.l (%sp),%d1/%a0-%a1\n"
        "    lea     12(%sp),%sp\n"
        "    rts\n"
        "tj_enc:\n"                             /* the TEMPO view's encoder handler entry (view, ev) */
        "    move.l  8(%sp),-(%sp)\n"
        "    move.l  8(%sp),-(%sp)\n"
        "    jsr     tj_enc_c\n"
        "    addq.l  #8,%sp\n"
        "    tst.l   %d0\n"
        "    beq.s   1f\n"
        "    moveq   #1,%d0\n"
        "    rts\n"
        "1:  lea     -16(%sp),%sp\n"            /* stock's first two instructions, then on */
        "    movem.l %d2-%d4/%a2,(%sp)\n"
        "    jmp     " ENC_REST "\n"
        "tj_key:\n"
        "    jmp     tj_key_c\n"
        "tj_draw_v:\n"
        "    jmp     tj_draw\n"
        "tj_dtor0:\n"                           /* the TEMPO view's destructors: JOG ends first */
        "    move.l  4(%sp),-(%sp)\n"
        "    jsr     tj_gone\n"
        "    addq.l  #4,%sp\n"
        "    jmp     " DTOR0 "\n"
        "tj_dtor1:\n"
        "    move.l  4(%sp),-(%sp)\n"
        "    jsr     tj_gone\n"
        "    addq.l  #4,%sp\n"
        "    jmp     " DTOR1 "\n"
        "tj_inv_name:\n"                        /* std::string by value (result in a0), as the menu's own names */
        "    link.w  %fp,#-4\n"
        "    move.l  %d2,-(%sp)\n"
        "    pea     -1(%fp)\n"
        "    pea     tj_str_name\n"
        "    move.l  %a0,%d2\n"
        "    move.l  %a0,-(%sp)\n"
        "    jsr     " STR_CTOR "\n"
        "    lea     12(%sp),%sp\n"
        "    move.l  %d2,%d0\n"
        "    move.l  -8(%fp),%d2\n"
        "    unlk    %fp\n"
        "    rts\n"
        "tj_pers_v:\n"
        "    jmp     tj_pers\n");
