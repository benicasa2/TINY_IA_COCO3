        org     $1e00
        lbra    check
        lbra    install

; DAT check: all four 512 KiB quadrants must keep distinct bytes in slot 3.
; The probe uses page 8 of each quadrant and restores all touched bytes.
check   pshs    cc,d,x,y
        orcc    #$50
        clr     $1ef1
        ldx     #banks
        ldy     #saved
read    lda     ,x+
        sta     $ffa3
        ldb     $6000
        stb     ,y+
        cmpx    #banks+4
        blo     read
        ldx     #banks
write   lda     ,x+
        sta     $ffa3
        sta     $6000
        cmpx    #banks+4
        blo     write
        ldx     #banks
verify  lda     ,x+
        sta     $ffa3
        cmpa    $6000
        bne     restore
        cmpx    #banks+4
        blo     verify
        inc     $1ef1
restore ldx     #banks
        ldy     #saved
undo    lda     ,x+
        sta     $ffa3
        ldb     ,y+
        stb     $6000
        cmpx    #banks+4
        blo     undo
        lda     #$3b
        sta     $ffa3
        puls    cc,d,x,y,pc

; The LOADM stage is at $6000. Use $4000 to address the destination page.
install pshs    cc,d,x,y
        orcc    #$50
        lda     $1ef0
        sta     $ffa2
        ldx     #$6000
        ldy     #$4000
copy    ldd     ,x++
        std     ,y++
        cmpy    #$6000
        blo     copy
        lda     #$3a
        sta     $ffa2
        puls    cc,d,x,y,pc

banks   fcb     $08,$48,$88,$c8
saved   fcb     0,0,0,0
        org     $1ef0
        fcb     0,0
        end     $1e00
