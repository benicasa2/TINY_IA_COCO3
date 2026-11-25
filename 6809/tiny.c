/* Tiny 2.1 for the CoCo 3. Inference adapted from upstream dos/TINY.C.
 * See LICENSE for the original copyright and MIT terms. */
#include <cmoc.h>
#include <coco.h>

#define VOCAB 97
#define CTX 128
#define D 96
#define L 4
#define H 4
#define HD 24
#define HID 256
#define MAXQ 72
#define WINDOW ((unsigned char *)0x6000)
#define MMU (*(unsigned char *)0xffa3)
#define NORMAL_PAGE 0x3b

/* The BASIC loader keeps these mailboxes clear of its stack and of LOADM. */
#define START_MODE (*(unsigned char *)0x1ef2)
#define BATCH_END (*(unsigned char *)0x1ef3)
#define BATCH_IN ((char *)0x1f00)
#define BATCH_OUT ((char *)0x1f50)
#define CACHE_PAGE 128
#define CACHE_ROWS 40
#define CACHE_BYTES (2 * (D + 5))

typedef struct {
    unsigned char page;
    unsigned rows, cols, per_page, offset, first_rows;
} Table;
#include "model.h"

/* These work areas have disjoint lifetimes within each token. */
#ifdef TINY_FUJINET
static float bx[D], bh[D], bt[D];
#else
static float bx[D], bh[D], bt[D], ba[D];
#endif
static float layer_act[L], last_conf;
static int creativity = 5;
static union {
    float hidden[HID];
    float logits[VOCAB];
} output_work;
#ifndef TINY_FUJINET
static float bs[CTX];
#endif
#define gain bt
#define bq bh
#define bm (output_work.hidden)
#ifdef TINY_FUJINET
/* Attention output is dead before the feed-forward output is written. */
#define ba (output_work.hidden)
/* The upper half is free during attention and token sampling. */
#define bs (output_work.hidden + CTX)
#endif
#define score (output_work.logits)

static const unsigned char *row(const Table *t, unsigned r)
{
    unsigned n = t->cols + 5;
    if (r < t->first_rows) {
        MMU = t->page;
        return WINDOW + t->offset + r * n;
    }
    r -= t->first_rows;
    MMU = (unsigned char)(t->page + 1 + r / t->per_page);
    return WINDOW + (r % t->per_page) * n;
}

static const unsigned char *cache(unsigned layer, unsigned p)
{
    MMU = (unsigned char)(CACHE_PAGE + layer * 4 + p / CACHE_ROWS);
    return WINDOW + (p % CACHE_ROWS) * CACHE_BYTES;
}

/* Same product and accumulation order as DOS. The CoCo uses the BASIC
 * ROM's five-byte floating-point representation for these operations. */
static void matvec(const Table *t, const float *x, float *y)
{
    unsigned r, c, n = t->cols;
    for (r = 0; r < t->rows; ++r) {
        const unsigned char *data = row(t, r);
        const signed char *w = (const signed char *)(data + 5);
        float s = 0.0f;
        for (c = 0; c < n; ++c)
            s += w[c] * x[c];
        y[r] = s * *(const float *)data;
    }
    MMU = NORMAL_PAGE;
}

static void norm(const float *x, unsigned which, float *y)
{
    int i;
    float s = 0.0f;
    MMU = 64;
    memcpy(gain, WINDOW + which * sizeof gain, sizeof gain);
    MMU = NORMAL_PAGE;
    for (i = 0; i < D; i++)
        s += x[i] * x[i];
    s = 1.0f / sqrtf(s / D + 1e-5f);
    for (i = 0; i < D; i++)
        y[i] = x[i] * s * gain[i];
}

/* e to the power x, quietly 0 for very negative x (no underflow messages) */
static float safe_exp(float x)
{
    if (x < -60.0f)
        return 0.0f;
    return expf(x);
}

/* keep a list of D numbers as bytes, returning the scale */
static float store(signed char *dst, const float *src)
{
    int i;
    float big = 0.0f, v, k;
    for (i = 0; i < D; i++) {
        v = src[i] < 0 ? -src[i] : src[i];
        if (v > big) big = v;
    }
    if (big < 1e-20f)
        big = 1e-20f;
    k = 127.0f / big;
    for (i = 0; i < D; i++) {
        v = src[i] * k;
        dst[i] = (signed char)(v < 0 ? v - 0.5f : v + 0.5f);
    }
    return big / 127.0f;
}

static int checkpoint(void);

static int step(int tok, int p, int need_score)
{
    int i, j, l, h;
    const signed char *kp, *vp;
    const unsigned char *data;
    float s, big, sum, scale;
    unsigned head;

    data = row(&emb, tok);
    scale = *(const float *)data;
    kp = (const signed char *)(data + 5);
    for (i = 0; i < D; ++i) bx[i] = kp[i] * scale;
    data = row(&pos, p);
    scale = *(const float *)data;
    kp = (const signed char *)(data + 5);
    for (i = 0; i < D; ++i) bx[i] += kp[i] * scale;
    MMU = NORMAL_PAGE;

    for (l = 0; l < L; ++l) {
        if (checkpoint()) return 0;
        norm(bx, l*2, bh);
        matvec(wk[l], bh, bt);
        data = cache(l, p);
        *(float *)data = store((signed char *)(data + 5), bt);
        MMU = NORMAL_PAGE;
        matvec(wv[l], bh, bt);
        data = cache(l, p) + 5 + D;
        *(float *)data = store((signed char *)(data + 5), bt);
        MMU = NORMAL_PAGE;
        /* bq shares bh, so preserve the input until all rows are complete. */
        memcpy(bt, bh, sizeof bh);
        matvec(wq[l], bt, bq);
        for (h = 0; h < H; ++h) {
            head = h * HD;
            big = -1.0e30f;
            for (j = 0; j <= p; ++j) {
                data = cache(l, j);
                kp = (const signed char *)(data + 5 + head);
                s = 0.0f;
                for (i = 0; i < HD; ++i) s += bq[head+i] * kp[i];
                s = s * *(const float *)data / 4.898979663848876953125f;
                bs[j] = s;
                if (s > big) big = s;
            }
            sum = 0.0f;
            for (j = 0; j <= p; ++j) {
                bs[j] = safe_exp(bs[j] - big);
                sum += bs[j];
            }
            for (i = 0; i < HD; ++i) ba[head+i] = 0.0f;
            for (j = 0; j <= p; ++j) {
                if (bs[j] == 0.0f) continue;
                data = cache(l, j) + 5 + D;
                vp = (const signed char *)(data + 5 + head);
                s = bs[j] * *(const float *)data / sum;
                for (i = 0; i < HD; ++i) ba[head+i] += s * vp[i];
            }
        }
        MMU = NORMAL_PAGE;
        matvec(wo[l], ba, bt);
        for (i = 0; i < D; ++i) bx[i] += bt[i];

        norm(bx, l*2+1, bh);
        matvec(f1[l], bh, bm);
        s = 0.0f;
        for (i = 0; i < HID; ++i) {
            if (bm[i] < 0.0f) bm[i] = 0.0f;
            else s += bm[i];
        }
        layer_act[l] = s / HID;
        matvec(f2[l], bm, bt);
        for (i = 0; i < D; ++i) bx[i] += bt[i];
    }
    /* Question tokens only need to populate the key/value cache. */
    if (need_score) {
        norm(bx, 2*L, bh);
        matvec(&emb, bh, score);
    }
    return 1;
}
/* Turbo C 2.0 rand() in the shipped DOS executable. Keep its 32-bit
 * recurrence and upper-15-bit output when applying the DOS sampler. */
static unsigned long random_state = 1;
static int tiny_rand(void)
{
    random_state = random_state * 0x015a4e35UL + 1;
    return (int)((random_state >> 16) & 0x7fff);
}

static int chosen(int tok)
{
    int i;
    float sum = 0.0f;
    for (i = 0; i < VOCAB; i++)
        sum += safe_exp(score[i] - score[tok]);
    last_conf = 1.0f / sum;
    return tok;
}

/* Pick the next letter. With creativity 0 it is always the best one.
   Otherwise choose at random among the letters that fit nearly as well,
   so the same question gets differently worded answers. */
static int pick(void)
{
    int i, best = 0;
    float t, sum = 0.0f, r;

    for (i = 1; i < VOCAB; i++)
        if (score[i] > score[best]) best = i;
    if (creativity <= 0)
        return chosen(best);
    t = creativity / 5.0f;
    for (i = 0; i < VOCAB; i++) {
        bs[i] = safe_exp((score[i] - score[best]) / t);
        if (bs[i] < 0.15f) bs[i] = 0.0f;      /* never pick unlikely letters */
        sum += bs[i];
    }
    r = sum * (float)(tiny_rand() % 10000) / 10000.0f;
    for (i = 0; i < VOCAB; i++) {
        r -= bs[i];
        if (r < 0.0f && bs[i] > 0.0f) return chosen(i);
    }
    return chosen(best);
}

static int clean(const char *line, char *q)
{
    int i, n = 0, lower = 0, upper = 0;
    for (i = 0; line[i] && n < MAXQ; i++)
        if (line[i] >= 32 && line[i] <= 126)
            q[n++] = line[i];
    while (n > 0 && q[n - 1] == ' ')
        n--;
    q[n] = 0;
    for (i = 0; i < n; i++) {
        if (q[i] >= 'a' && q[i] <= 'z') lower++;
        if (q[i] >= 'A' && q[i] <= 'Z') upper++;
    }
    if (upper > 0 && lower == 0)
        for (i = 0; i < n; i++)
            if (q[i] >= 'A' && q[i] <= 'Z') q[i] += 'a' - 'A';
    return n;
}

static int is_word(const char *q, const char *w)
{
    int i;
    for (i = 0; q[i] && w[i]; i++)
        if ((q[i] | 32) != w[i]) return 0;
    return q[i] == 0 && w[i] == 0;
}

/* WIDTH 80 uses GIME RAM block $36 on the CoCo 3 Disk BASIC display.
 * Draw directly so scrolling the chat leaves the monitor and status intact. */
#define VIDEO_PAGE 0x36
#define CHAT_TOP 3
#define CHAT_END 20
#define CHAT_WIDTH 55
#define CELL(fg,bg) ((fg)*8+(bg))

static unsigned char cx, cy, plain, quiet, voice = 1, batch, out_len;

static unsigned char *screen_at(unsigned x, unsigned y)
{
    return WINDOW + (y * 80 + x) * 2;
}

static void fill(unsigned char *dst, unsigned n, unsigned char c, unsigned char attr)
{
    while (n--) {
        *dst++ = c;
        *dst++ = attr;
    }
}

static void text_at(unsigned x, unsigned y, const char *s, unsigned char attr)
{
    unsigned char *dst = screen_at(x, y);
    while (*s) {
        *dst++ = *s++;
        *dst++ = attr;
    }
}

static void ui_frame(void)
{
    unsigned y;
    MMU = VIDEO_PAGE;
    fill(WINDOW, 80*24, ' ', CELL(7,0));
    fill(screen_at(0,0), 80, ' ', CELL(7,4));
    fill(screen_at(0,23), 80, ' ', CELL(7,4));
    text_at(2,0,"TINY 2.1  |  NEURAL QUESTION ANSWERING",CELL(7,4));
    text_at(64,0,"COCO 3 / 2 MB",CELL(7,4));
    text_at(1,1,"CHAT",CELL(6,0));
    text_at(58,1,"NEURAL MONITOR",CELL(6,0));
    text_at(58,3,"LAYERS",CELL(7,0));
    text_at(58,10,"CONFIDENCE",CELL(7,0));
    text_at(58,13,"LAST LETTERS",CELL(7,0));
    text_at(58,17,"POSITION",CELL(7,0));
    text_at(1,23,"F1 Help  F2 Sound  Shift-F1 Voice  Shift-F2 Creativity  DEMO  BREAK Cancel",CELL(7,4));
    for (y=1; y<23; ++y)
        fill(screen_at(56,y),1,'|',CELL(6,0));
    MMU = NORMAL_PAGE;
    cx = 0;
    cy = CHAT_TOP;
}

static void ui_put(int c)
{
    unsigned y;
    if (batch) {
        if (c >= 32 && out_len < CTX)
            BATCH_OUT[out_len++] = (char)c;
        BATCH_OUT[out_len] = 0;
        return;
    }
    if (plain) {
        putchar(c);
        return;
    }
    MMU = VIDEO_PAGE;
    if (c == '\n' || cx == CHAT_WIDTH) {
        cx = 0;
        ++cy;
        if (cy > CHAT_END) {
            for (y = CHAT_TOP; y < CHAT_END; ++y)
                memcpy(screen_at(1,y), screen_at(1,y+1), CHAT_WIDTH*2);
            fill(screen_at(1,CHAT_END),CHAT_WIDTH,' ',CELL(7,0));
            cy = CHAT_END;
        }
    }
    if (c >= 32)
        fill(screen_at(1+cx++,cy),1,(unsigned char)c,CELL(7,0));
    MMU = NORMAL_PAGE;
}

static void ui_text(const char *s)
{
    while (*s) ui_put(*s++);
}

static void ui_input(const char *line)
{
    MMU = VIDEO_PAGE;
    fill(screen_at(0,21), 80, ' ', CELL(7,0));
    text_at(1,21,"> ",CELL(6,0));
    text_at(3,21,line,CELL(7,0));
    MMU = NORMAL_PAGE;
}

static void meter(unsigned y, int n, unsigned char attr)
{
    unsigned char *dst = screen_at(59,y);
    if (n > 18) n = 18;
    fill(dst, n, '=', attr);
    fill(dst + n*2, 18-n, '.', CELL(7,0));
}

static void monitor(unsigned p, int token, unsigned letters)
{
    unsigned h, value;
    unsigned char digits[4];
    if (plain) return;
    MMU = VIDEO_PAGE;
    for (h = 0; h < L; ++h)
        meter(5+h, (int)(layer_act[h] * 8.0f), CELL(6,0));
    if (token > 1) {
        unsigned char attr = last_conf > 0.75f ? CELL(2,0) :
                             last_conf > 0.4f ? CELL(3,0) : CELL(1,0);
        meter(11, (int)(last_conf * 18.0f), attr);
        if (letters > 18)
            memcpy(screen_at(59,14), screen_at(60,14), 34);
        fill(screen_at(59+(letters > 18 ? 17u : letters-1),14),1,
             (unsigned char)(token+30),attr);
    } else if (p == 1) {
        fill(screen_at(59,11),18,' ',CELL(7,0));
        fill(screen_at(59,14),18,' ',CELL(7,0));
    }
    value = p;
    digits[3] = 0;
    for (h=3; h>0; --h) {
        digits[h-1] = (unsigned char)('0'+value%10);
        value /= 10;
    }
    text_at(59,18,(char *)digits,CELL(6,0));
    MMU = NORMAL_PAGE;
}

static void say(int c)
{
    if (plain || quiet || !voice || c <= 32) return;
    c |= 32;
    if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u')
        sound((unsigned char)(70+(c&15)*3),3);
    else
        sound((unsigned char)(35+(c&31)*5),1);
}

static unsigned ticks(void)
{
    unsigned value;
    asm {
        pshs cc
        orcc #$50
        ldd $112
        std value
        puls cc
    }
    return value;
}

#define KEY_HELP 128
#define KEY_SOUND 129
#define KEY_VOICE 130
#define KEY_CREATIVITY 131
#define KEY_RECALL 94

/* ROM POLCAT updates the matrix shadow at $0152..$0159. A held
 * function key produces one action even when POLCAT has no new ASCII. */
static unsigned char key(void)
{
    static unsigned char held;
    unsigned char c = inkey(), fn = 0;
    if (!(*(unsigned char *)0x157 & 0x40)) fn = KEY_HELP;
    if (!(*(unsigned char *)0x158 & 0x40)) fn = KEY_SOUND;
    if (fn && !(*(unsigned char *)0x159 & 0x40)) fn += 2;
    if (fn) {
        c = held ? 0 : fn;
        held = 1;
    } else held = 0;
    return c;
}

static unsigned char delay_key(unsigned duration)
{
    unsigned start = ticks();
    unsigned char c;
    do {
        c = key();
        if (c) return c;
    } while (ticks() - start < duration);
    return 0;
}

static void rain(void)
{
    signed char y[40];
    unsigned char f, x;
    int p;
    MMU = VIDEO_PAGE;
    fill(WINDOW, 80*24, ' ', CELL(2,0));
    for (x = 0; x < 40; ++x) y[x] = (signed char)-(int)(rand() % 24);
    for (f = 0; f < 46; ++f) {
        for (x = 0; x < 40; ++x) {
            p = y[x];
            if (p >= 0 && p < 24)
                fill(screen_at(x*2,p),1,(unsigned char)(33+rand()%90),CELL(2,0));
            if (p >= -1 && p < 23)
                fill(screen_at(x*2,p+1),1,(unsigned char)(33+rand()%90),CELL(7,0));
            if (p >= 7 && p < 31)
                fill(screen_at(x*2,p-7),1,' ',CELL(2,0));
            y[x] = (signed char)(y[x] + 1 + (x & 1));
            if (y[x] > 31) y[x] = (signed char)-(int)(rand()%10);
        }
        MMU = NORMAL_PAGE;
        if (delay_key(2)) return;
        MMU = VIDEO_PAGE;
    }
    MMU = NORMAL_PAGE;
}

static char last_q[MAXQ+1];

static void show_help(void)
{
    ui_text("F1 Help   F2 Sound   Shift-F1 Voice   Shift-F2 Creativity\n");
    ui_text("Up Last question   BREAK Cancel   DEMO Auto chat\n");
    ui_text("HELP CLS QUIT /0-/9 /P /FULL /QUIET /VOICE\n");
}

static void set_creativity(int value)
{
    creativity = value;
    ui_text("Creativity ");
    ui_put('0'+value);
    ui_put('\n');
}

static int read_line(char *line)
{
    unsigned n = 0;
    unsigned char c;
    if (plain) ui_text("\n> ");
    line[0] = 0;
    if (!plain) ui_input(line);
    while (1) {
        c = key();
        if (c == 0) continue;
        if (c == 3 || c == 27) return 0;
        if (c == 13) break;
        if (c == KEY_HELP) show_help();
        else if (c == KEY_SOUND) {
            quiet = !quiet;
            ui_text(quiet ? "Sound off\n" : "Sound on\n");
        } else if (c == KEY_VOICE) {
            voice = !voice;
            ui_text(voice ? "Voice on\n" : "Voice off\n");
        } else if (c == KEY_CREATIVITY) {
            set_creativity((creativity+1)%10);
        } else if (c == KEY_RECALL && !plain) {
            strcpy(line,last_q);
            n = strlen(line);
        } else if ((c == 8 || c == 127) && n) {
            line[--n] = 0;
            if (plain) putchar(8);
        } else if (c >= 32 && c < 127 && n < MAXQ) {
            line[n++] = c;
            line[n] = 0;
            if (plain) putchar(c);
        }
        if (!plain) ui_input(line);
    }
    if (plain) putchar('\n');
    else {
        ui_input("");
        ui_text("> ");
        ui_text(line);
        ui_put('\n');
    }
    return 1;
}

static unsigned char demo_running, phase, activity;

static void thinking_status(void)
{
    if (plain) return;
    MMU = VIDEO_PAGE;
    fill(screen_at(0,22), 80, ' ', CELL(7,0));
    if (phase) {
        text_at(1,22,phase == 1 ? "READING QUESTION" : "GENERATING ANSWER",CELL(6,0));
        fill(screen_at(20,22),1,"|/-\\"[activity++ & 3],CELL(6,0));
        text_at(24,22,"BREAK cancels",CELL(7,0));
    }
    MMU = NORMAL_PAGE;
}

static int checkpoint(void)
{
    unsigned char c;
    if (batch) return 0;
    thinking_status();
    c = key();
    return c && (demo_running || c == 3 || c == 27);
}

static int think(const char *q, int demo)
{
    unsigned p = 0, letters = 0;
    int tok;
    demo_running = (unsigned char)demo;
    phase = 1;
    for (; q[p];) {
        if (!step(q[p] - 30, p, 0)) goto cancel;
        monitor(++p, 0, 0);
    }
    if (!step(1, p++, 1)) goto cancel;
    phase = 2;
    for (; p < CTX; ++p) {
        tok = pick();
        if (tok <= 1) break;
        ui_put(tok + 30);
        monitor(p, tok, ++letters);
        say(tok+30);
        if (!step(tok, p, 1)) goto cancel;
    }
    if (!letters && !batch) ui_text("[no answer]");
    ui_put('\n');
    phase = 0;
    thinking_status();
    return 1;
cancel:
    ui_text("\n[stopped]\n");
    phase = 0;
    thinking_status();
    return 0;
}

static void run_demo(void)
{
    static const char *questions[] = {
        "what is the capital of estonia", "is a whale a fish", "what is 7 times 8",
        "which countries border estonia", "spell computer", "what is the symbol for gold",
        "how do you say thank you in spanish", "what is a group of lions called",
        "what comes after 199", "what time is it", "tell me a joke",
        "name the continents", 0
    };
    char line[MAXQ+1];
    unsigned char i, n;
    const char *q;
    for (i = 0; (q = questions[i]) != 0; ++i) {
        for (n = 0; q[n]; ++n) {
            line[n] = q[n];
            line[n+1] = 0;
            if (!plain) ui_input(line);
            if (delay_key(4)) goto done;
        }
        if (!plain) ui_input("");
        ui_text("> ");
        ui_text(q);
        ui_text("\nTINY: ");
        if (!think(q,1) || delay_key(90)) break;
    }
done:
    if (!plain) ui_input("");
}

static unsigned char memory_on;

#ifdef TINY_FUJINET
#include "fujinet.inc"
#else
/* Becker registers. The Windows bridge handles HTTPS and persistence. */
#define NET_STATUS (*(unsigned char *)0xff41)
#define NET_DATA (*(unsigned char *)0xff42)
static int bridge(const char *q)
{
    static unsigned char sequence = 'A';
    unsigned char id, c, state = 0, discard = 0;
    unsigned start = ticks();
    id = sequence++;
    if (sequence > 'Z') sequence = 'A';
    NET_DATA = 10;
    NET_DATA = id;
    while (*q) NET_DATA = (unsigned char)*q++;
    NET_DATA = 10;
    do {
        if (key() == 3) break;
        if (NET_STATUS == 2) {
            c = NET_DATA;
            if (discard) {
                if (!c) discard = 0;
            } else if (!state) {
                if (c == id) state = 1;
                else if (c) discard = 1;
            } else if (state == 1) {
                memory_on = 1;
                if (c == '0') state = 2;
                else if (c == '1') state = 3;
                else { state = 0; discard = c != 0; }
            } else if (!c) {
                if (state == 3) ui_put('\n');
                return state == 3;
            } else if (state == 3) ui_put(c);
        }
    } while (ticks() - start < 7200u);
    memory_on = 0;
    return -1;
}

#endif

int main(void)
{
    static char line[MAXQ+1], q[MAXQ+1];
    if (START_MODE == 2) {
        batch = plain = 1;
        creativity = 0;
        BATCH_OUT[0] = 0;
        BATCH_END = 0;
        if (clean(BATCH_IN,q)) {
            if (is_word(q,"quit") || is_word(q,"exit")) BATCH_END = 1;
            else think(q,0);
        }
        return 0;
    }
    random_state = ticks();
    srand((unsigned)random_state);
    rain();
    ui_frame();
    ui_text("Ready: 4 layers, 96 wide. Ask a question.\n");
    if (!quiet) sound(120,2);
    if (START_MODE == 1) run_demo();
#ifdef TINY_FUJINET
    memory_on = START_MODE == 4;
#else
    memory_on = START_MODE == 3;
#endif
    while (read_line(line)) {
        if (!clean(line, q)) continue;
        if (is_word(q, "quit") || is_word(q, "exit")) break;
        if (is_word(q, "help")) {
            show_help();
        } else if (is_word(q,"demo") || is_word(q,"/demo")) {
            run_demo();
        } else if (is_word(q, "cls")) {
            if (plain) cls(255); else ui_frame();
        } else if (is_word(q, "/p")) {
            plain = 1;
            cls(255);
            ui_text("TINY 2.1 - plain text. /FULL restores the monitor.\n");
        } else if (is_word(q, "/full")) {
            plain = 0;
            ui_frame();
        } else if (is_word(q, "/quiet")) {
            quiet = !quiet;
            ui_text(quiet ? "Sound off\n" : "Sound on\n");
        } else if (is_word(q, "/voice")) {
            voice = !voice;
            ui_text(voice ? "Voice on\n" : "Voice off\n");
        } else if (q[0] == '/' && q[1] >= '0' && q[1] <= '9' && !q[2]) {
            set_creativity(q[1] - '0');
        } else if (q[0] == '/') {
            ui_text("Contacting bridge...\n");
            if (bridge(q) < 0) ui_text("Bridge unavailable or stopped.\n");
        } else if (!memory_on || bridge(q) <= 0) {
            strcpy(last_q,q);
            ui_text("TINY: ");
            think(q,0);
        }
    }
#ifdef TINY_FUJINET
    fn_close();
#endif
    cls(255);
    plain = 1;
    ui_text("Goodbye!\n");
    return 0;
}


