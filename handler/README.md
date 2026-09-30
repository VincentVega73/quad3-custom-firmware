# SK2-RC2 handler

`handler_sk2.asm` assembles at `0x0801D8F8` to the 124-byte payload pinned in
`firmware_patch.py`: 120 bytes of Thumb-2 instructions followed by one 32-bit
literal. The stock image is required locally to build or execute the candidate.

The three established short-release events are `0x5017`, `0x5018`, and `0x5019`.
The owner observed physical buttons 0, 1, and 2 activate the matching SK1 actions.
SK2 deliberately changes event `0x5019` from ARC to AUX2. The owner supplied
AMP-mode captures for all eight buttons using a VS1838B and ESP32; see
[IR_CODES.md](../docs/IR_CODES.md). Their command bytes were matched against the
exact stock decoder table independently of button-number order. Buttons 8 and
9 receive no new functions.

The intended entry is `0x0801D8F8`, immediately after the stock image. The design
preserves the four-byte dispatcher hook at file offset `0x3346`, fallback to
`0x0801334A`, housekeeping call `0x080131F8`, requested-source byte
`0x20000ED3`, and native source-selection tail `0x080134D4`.

Saving `{r1, r2}` consumes eight bytes. Both registers must be restored before
housekeeping or the stock tail; the stock dispatcher owns the saved `r5`.
Fallback reproduces `subs r0, r0, #7` and its flags. Instruction execution checks
cover this calling convention; they cannot prove physical peripheral operation
or compatibility with other hardware revisions.

The source is assembled independently in the local validation workflow and
compared with the frozen payload. Execute the tests in
[tests/README.md](../tests/README.md) before any hardware experiment. The patch
retains the native source worker and routing logic; it adds no second state
machine or direct peripheral writes.
