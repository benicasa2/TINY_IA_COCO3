        section code
_dot6309 export
unpackXtoFPA1AndPrep import

; dot6309(x, weights, count, &sum)
; Keep the same rounding boundaries as the CMOC BASIC floating-point
; helpers. Round the product to MBF, then round the running sum to MBF.
; Enter native mode only inside the dot product. Interrupts can run in
; 6809 mode between groups of eight terms and at the end of each row.
_dot6309
        pshs    cc,y,u
        orcc    #$50
        ldmd    #1
        leas    -9,s
        ldd     16,s
        std     5,s
        ldd     18,s
        std     7,s
        ldx     22,s
        ldq     #0
        stq     ,x
        clr     4,x
        ldw     20,s
loop
        ldx     5,s
        leay    5,x
        sty     5,s
        ldx     7,s
        ldb     ,x+
        stx     7,s
        tstb
        beq     next_term
        ldx     5,s
        tst     -5,x
        beq     next_term
        sex
        jsr     $b4f4
        ldx     5,s
        leax    -5,x
        lbsr    unpackXtoFPA1AndPrep
        lda     $005c
        ldb     $004f
        jsr     $bacc
        leax    ,s
        jsr     $bc35
        leax    ,s
        jsr     $bc14
        ldx     22,s
        jsr     $b9c2
        ldx     22,s
        jsr     $bc35
next_term
        decw
        beq     finished
        tfr     w,d
        bitb    #7
        bne     loop
        ldmd    #0
        lda     9,s
        tfr     a,cc
        nop
        orcc    #$50
        ldmd    #1
        bra     loop
finished
        leas    9,s
        ldmd    #0
        puls    cc,y,u,pc
        endsection
