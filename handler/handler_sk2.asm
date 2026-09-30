; SK2-RC2 Thumb-2 handler assembled at 0x0801D8F8.
; Physical buttons 0..7 confirmed by owner captures; decoder pairs checked in stock image.
; Save r1/r2 together to preserve eight-byte stack alignment; r5 is saved by the caller.
handler_sk2:
    ldrh r0, [r4]
    push {r1, r2}
    movw r1, #0x5017              ; Owner observed: physical 0, USB.
    cmp r0, r1
    beq select_usb
    movw r1, #0x5018              ; Owner observed: physical 1, AUX1.
    cmp r0, r1
    beq select_aux1
    movw r1, #0x5019              ; Owner observed: physical 2; SK2 changes ARC to AUX2.
    cmp r0, r1
    beq select_aux2
    movw r1, #0x501A
    cmp r0, r1
    beq select_phono
    movw r1, #0x501B
    cmp r0, r1
    beq select_coax
    movw r1, #0x501C
    cmp r0, r1
    beq select_optical
    movw r1, #0x501D
    cmp r0, r1
    beq select_arc
    movw r1, #0x501E
    cmp r0, r1
    beq select_bluetooth

; All unhandled events restore the overwritten stock operation and its flags.
    pop {r1, r2}
    subs r0, r0, #7
    b.w 0x0801334a

select_usb:
    movs r5, #1
    b apply_source
select_aux1:
    movs r5, #5
    b apply_source
select_aux2:
    movs r5, #6
    b apply_source
select_phono:
    movs r5, #7
    b apply_source
select_coax:
    movs r5, #3
    b apply_source
select_optical:
    movs r5, #2
    b apply_source
select_arc:
    movs r5, #4
    b apply_source
select_bluetooth:
    movs r5, #0
apply_source:
    pop {r1, r2}
    bl 0x080131f8                ; Native housekeeping, with caller-saved clobbers allowed.
    ldr r1, requested_source
    strb r5, [r1]
    b.w 0x080134d4               ; Native request, persistence scheduling, and UI tail.
    .align 2
requested_source:
    .word 0x20000ed3
