/* Minimal FujiNet N-device wire client for HDB-DOS. Network unit 1.
 * Wire format follows FujiNet fujinet-lib and FujiDWPacket.
 * The neural scratch area is free while a network request is running. */
#define FN_BUFFER ((unsigned char *)&output_work)
#define FN_SPEC ((const char *)0x1f00)
#define FN_PORT_READ (*(const unsigned *)0xd93f)
#define FN_PORT_WRITE (*(const unsigned *)0xd941)

static unsigned char fn_open;

asm unsigned char dw_read(unsigned char *data, unsigned size)
{
    asm {
        pshs x,y,u
        ldx 8,s
        ldy 10,s
        jsr [$d93f]
        tfr cc,b
        lsrb
        lsrb
        andb #1
        puls x,y,u,pc
    }
}

asm void dw_write(const unsigned char *data, unsigned size)
{
    asm {
        pshs x,y,u
        ldx 8,s
        ldy 10,s
        jsr [$d941]
        puls x,y,u,pc
    }
}

static int fn_ready(void)
{
    static const unsigned char ping[] = {0xe2,0};
    unsigned char result;
    dw_write(ping, 2);
    return dw_read(&result, 1) && result == 1;
}

static int fn_request(unsigned char command, unsigned aux,
                      const unsigned char *data, unsigned size)
{
    unsigned char packet[5], result;
    if (!fn_ready()) return 0;
    packet[0] = 0xe3;
    packet[1] = 1;
    packet[2] = command;
    packet[3] = (unsigned char)(aux >> 8);
    packet[4] = (unsigned char)aux;
    dw_write(packet, 5);
    if (size) dw_write(data, size);
    if (!fn_ready()) return 0;
    packet[2] = 2;
    packet[3] = packet[4] = 0;
    dw_write(packet, 5);
    return dw_read(&result, 1) && (result == 1 || result == 136);
}

static int fn_response(unsigned char *data, unsigned size)
{
    unsigned char packet[5];
    if (!fn_ready()) return 0;
    packet[0] = 0xe3;
    packet[1] = 1;
    packet[2] = 1;
    packet[3] = (unsigned char)(size >> 8);
    packet[4] = (unsigned char)size;
    dw_write(packet, 5);
    return dw_read(data, size);
}

static void fn_close(void)
{
    if (fn_open) {
        fn_open = 0;
        fn_request('C',0,0,0);
    }
}

static int bridge(const char *q)
{
    static unsigned char sequence = 'A';
    unsigned char id, c, state = 0, discard = 0, status[4];
    unsigned start, available, i;
    if (!fn_open) {
        if (START_MODE != 4 || FN_PORT_READ < 0xc000 || FN_PORT_READ >= 0xe000 ||
            FN_PORT_WRITE < 0xc000 || FN_PORT_WRITE >= 0xe000)
            return -1;
        memset(FN_BUFFER, 0, 256);
        strcpy((char *)FN_BUFFER,FN_SPEC);
        if (!fn_request('O',0x0c00,FN_BUFFER,256)) {
            fn_request('C',0,0,0);
            return -1;
        }
        fn_open = 1;
    }
    id = sequence++;
    if (sequence > 'Z') sequence = 'A';
    FN_BUFFER[0] = id;
    i = 1;
    while (*q) FN_BUFFER[i++] = (unsigned char)*q++;
    FN_BUFFER[i++] = 10;
    if (!fn_request('W',i,FN_BUFFER,i)) goto failed;
    start = ticks();
    do {
        if (key() == 3) goto failed;
        if (!fn_request('S',0,0,0) || !fn_response(status,4)) goto failed;
        available = ((unsigned)status[0] << 8) | status[1];
        if (!available && (!status[2] || status[3] > 1)) goto failed;
        if (available > 128) available = 128;
        if (available) {
            if (!fn_request('R',available,0,0) || !fn_response(FN_BUFFER,available))
                goto failed;
            for (i = 0; i < available; ++i) {
                c = FN_BUFFER[i];
                if (discard) {
                    if (!c) discard = 0;
                } else if (!state) {
                    if (c == id) state = 1;
                    else if (c) discard = 1;
                } else if (state == 1) {
                    if (c != '0' && c != '1') goto failed;
                    state = c == '1' ? 3 : 2;
                } else if (!c) {
                    if (state == 3) ui_put('\n');
                    return state == 3;
                } else if (state == 3) ui_put(c);
            }
        }
    } while (ticks() - start < 3600u);
failed:
    fn_close();
    return -1;
}
