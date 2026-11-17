/* tripwire (diagnostic, OS 1.41 and 1.42, -DOS142): a stack tripwire for the silent song-transition freeze.
 *
 * the author's freeze (TEST17f, again on TEST32a): no exception screen, the audio stuck on one buzzing buffer. The
 * main CPU stopped without the OS's own exception screen, which is what an overflowing task stack does: the
 * interrupts run on whatever task they interrupt (one A7), the smallest task stack is 2 KB, and the task's own
 * control block sits right under its stack (e.g. the 2 KB task at prio 10: TCB 0x405D2800, stack 0x405D2854).
 *
 *  - every task the OS creates (0x40001640: tcb, entry, prio, stack, size) is registered (up to NT) and its stack
 *    painted with PAINT before the task first runs;
 *  - every audio block, at its start (0x400A3864 / 1.42 0x400A38DC, right after the interrupt saved its registers):
 *      1. GUARD: the interrupted SP is looked up; fewer than GUARD bytes left under it means this very interrupt
 *         will run off the bottom (the stock interrupt alone goes 844 B deep every block; with BOUM, Heat or FX3
 *         busy up to 1,176 B): stop before it does.
 *      2. CANARY: one registered stack a block (round robin) has its bottom CANARY words checked; any word no
 *         longer PAINT means something already wrote there (an overflow): stop.
 *  - and at its end (0x400A54A0 / 1.42 0x400A5518, before it restores the registers and returns):
 *      3. the interrupted stack's bottom CANARY_X words: an overrun by this interrupt (deeper than GUARD covers) is
 *         caught before the interrupt returns and the scheduler trusts the control block under it.
 *  - stop = the OS's own exception screen (V04, illegal instruction), with 12 words that say what we know, drawn
 *    on a safe stack: the bottom EMERG bytes of the largest other task stack (still painted, so never used).
 *
 * Screen words:
 *   w0  0x57AC r ii   r: 1 GUARD (about to overflow), 2 CANARY (overflowed, found by the round), 3 overrun by
 *                     this audio block (found at its end); ii: the task's slot
 *   w1  the interrupted SP (1) / the first damaged address (2, 3)
 *   w2  the task's stack base      w3 its size      w4 its entry point (which task)
 *   w5  bytes left under the interrupted SP (1) / damaged words in the canary (2, 3)
 *   w6  the interrupted PC          w7 the interrupted SR (format word)
 *   w8, w9  the first two code addresses up the interrupted stack (its callers)
 *   w10 the least room ever seen at an audio block << 16 | its slot << 8 | tasks registered
 *   w11 audio blocks counted (low 24 bits) << 8 | creates not registered (table full)
 * Cost: about 330 instructions an audio block with 15 stacks (0.5 % of the CPU); painting at boot about 0.2 ms per 16 KB of stack. */
typedef unsigned int u32;
typedef int s32;

#define DATA __attribute__((section(".data")))
#define NT 16
#define PAINT 0x5AC0FFEEu
#define CANARY 16                               /* words: the round robin */
#define CANARY_X 32                             /* words: the interrupted stack, at the end of each block */
#define GUARD 844                               /* bytes: the stock audio interrupt's own depth, every block */
#define EMERG 4096                              /* bytes of a painted stack bottom the screen is drawn on */
#define CODE_LO 0x40000400u
#ifdef OS142
#define CODE_HI 0x40349000u                     /* the OS image (the mod area's image starts here) */
#else
#define CODE_HI 0x40348000u
#endif
#ifdef OS142
#define AREA_LO 0x444E48C0u                     /* the mod area (the heap's first block) */
#define AREA_HI 0x445048C0u
#else
#define AREA_LO 0x444E38C0u
#define AREA_HI 0x445038C0u
#endif

u32 tw_base[NT] DATA = {0};
u32 tw_end[NT] DATA = {0};
u32 tw_entry[NT] DATA = {0};
u32 tw_n DATA = 0, tw_rot DATA = 0, tw_blk DATA = 0, tw_skip DATA = 0;
u32 tw_least DATA = 0xFFFFu, tw_lix DATA = 0;
u32 tw_cur DATA = NT;                           /* the interrupted stack's slot, from the block's start to its end */

static s32 code(u32 a)
{
    return !(a & 1u) && ((a >= CODE_LO && a < CODE_HI) || (a >= AREA_LO && a < AREA_HI));
}

static s32 painted(u32 base, u32 words)
{
    const volatile u32 *p = (const volatile u32 *)base;
    u32 k;
    for (k = 0; k < words; k++)
        if (p[k] != PAINT)
            return 0;
    return 1;
}

static void __attribute__((noinline, noreturn)) fire(u32 why, u32 i, const u32 *fp, u32 a, u32 b)
{
    u32 j, s, best = NT, big = 0, *w, n = 0, v, sp = (u32)fp + 12;
    __asm__ volatile("move.w #0x2700,%%sr" : : : "memory");
    for (j = 0; j < tw_n; j++) {                /* the largest other stack whose bottom is still unused */
        s = tw_end[j] - tw_base[j];
        if (j != i && s >= EMERG + 1024 && s > big && painted(tw_base[j], EMERG / 4)) {
            best = j;
            big = s;
        }
    }
    if (best == NT)                             /* none intact: the largest other one anyway */
        for (j = 0; j < tw_n; j++) {
            s = tw_end[j] - tw_base[j];
            if (j != i && s > big) {
                best = j;
                big = s;
            }
        }
    w = best < NT ? (u32 *)(tw_base[best] + EMERG) : (u32 *)((u32)fp & ~3u);
    w[0] = 0x57AC0000u | (why & 0xFu) << 12 | (i & 0xFFu);
    w[1] = a;
    w[2] = tw_base[i];
    w[3] = tw_end[i] - tw_base[i];
    w[4] = tw_entry[i];
    w[5] = b;
    w[6] = fp[2];
    w[7] = fp[1];
    w[8] = w[9] = 0;
    for (j = sp; j + 4 <= tw_end[i] && j < sp + 160 && n < 2; j += 4) {
        v = *(const u32 *)j;
        if (code(v) && v != fp[2])
            w[8 + n++] = v;
    }
    w[10] = (tw_least & 0xFFFFu) << 16 | (tw_lix & 0xFFu) << 8 | (tw_n & 0xFFu);
    w[11] = (tw_blk & 0xFFFFFFu) << 8 | (tw_skip & 0xFFu);
    __asm__ volatile("movea.l %0,%%sp\n\tillegal" : : "a"(w) : "memory");
    for (;;)
        ;
}

/* f: [the caller's return address, tcb, entry, prio, stack, size] of the OS's task create */
void tw_create(const u32 *f)
{
    u32 base = f[4], end = base + (f[5] & ~3u), lim = end, sp = (u32)f, sr, i;
    volatile u32 *p;
    if (sp >= base && sp < end)                 /* never paint under our own feet */
        lim = (sp - 64u) & ~3u;
    for (p = (volatile u32 *)base; (u32)p < lim; p++)
        *p = PAINT;
    __asm__ volatile("move.w %%sr,%0\n\tmove.w #0x2700,%%sr" : "=d"(sr) : : "memory");
    for (i = 0; i < tw_n && tw_base[i] != base; i++)
        ;
    if (i < NT) {
        tw_base[i] = base;
        tw_end[i] = end;
        tw_entry[i] = f[2];
        if (i == tw_n)
            tw_n++;
    } else
        tw_skip++;
    __asm__ volatile("move.w %0,%%sr" : : "d"(sr) : "memory");
}

/* fp: the audio interrupt's frame pointer (link a6: 0(fp) old a6, 4(fp) format/SR, 8(fp) PC) */
void tw_isr(const u32 *fp)
{
    u32 sp = (u32)fp + 12, n = tw_n, i, k, bad, first;
    const volatile u32 *b;
    tw_blk++;
    tw_cur = NT;
    if (!n)
        return;
    for (i = 0; i < n; i++)
        if (sp > tw_base[i] && sp <= tw_end[i]) {
            tw_cur = i;
            k = sp - tw_base[i];
            if (k < tw_least) {
                tw_least = k;
                tw_lix = i;
            }
            if (k < GUARD)
                fire(1, i, fp, sp, k);
            break;
        }
    i = tw_rot;
    tw_rot = i + 1 < n ? i + 1 : 0;
    b = (const volatile u32 *)tw_base[i];
    for (k = bad = 0, first = 0; k < CANARY; k++)
        if (b[k] != PAINT) {
            if (!bad)
                first = (u32)&b[k];
            bad++;
        }
    if (bad)
        fire(2, i, fp, first, bad);
}

/* the end of the audio block: did this interrupt overrun the stack it interrupted? */
void tw_exit(const u32 *fp)
{
    u32 i = tw_cur, k, bad, first;
    const volatile u32 *b;
    if (i >= NT)
        return;
    b = (const volatile u32 *)tw_base[i];
    for (k = bad = 0, first = 0; k < CANARY_X; k++)
        if (b[k] != PAINT) {
            if (!bad)
                first = (u32)&b[k];
            bad++;
        }
    if (bad)
        fire(3, i, fp, first, bad);
}

__asm__(".text\n"
        "    .globl tw_mk, tw_blk_hook, tw_end_hook\n"
        "tw_mk:\n"                              /* 0x40001640: was move.l 12(sp),d0 ; moveq #-4,d1 */
        "    move.l  %sp,-(%sp)\n"                /* f = [ret, tcb, entry, prio, stack, size] */
        "    jsr     tw_create\n"
        "    addq.l  #4,%sp\n"
        "    move.l  12(%sp),%d0\n"
        "    moveq   #-4,%d1\n"
        "    jmp     0x40001646\n"
        "tw_blk_hook:\n"                        /* audio interrupt: was and.l d0,0xFC04C010 (d0 = 0x7FFFFFFF) */
        "    and.l   %d0,0xFC04C010\n"
        "    move.l  %a6,-(%sp)\n"
        "    jsr     tw_isr\n"
        "    addq.l  #4,%sp\n"
        "    rts\n"
        "tw_end_hook:\n"                        /* the end of the audio interrupt: was movem.l -164(a6),d0-a5 */
        "    move.l  %a6,-(%sp)\n"
        "    jsr     tw_exit\n"
        "    addq.l  #4,%sp\n"
        "    movem.l -164(%a6),%d0-%a5\n"
        "    rts\n");
