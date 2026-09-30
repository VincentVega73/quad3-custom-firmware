# Image format and integrity evidence

The supported input is a 55,544-byte raw application at `0x08010000`, identified by SHA256 `7dff59e986643543c28c7f71c1f43f78c936867b25b078e0c1bd0ea5a6fe3853`. The supplied file does not contain the lower flash region. No bootloader was dumped or analyzed as part of this project.

The original investigation tested a finite set of image-internal length/checksum hypotheses: candidate header/trailer fields, little/big-endian interpretations, common CRC16/CRC32 variants, STM32 word CRC, Fletcher16/32, additive sums, complements/XOR and hash prefix/trailer comparisons. No explicit required image-local checksum, length field or separate signature block was identified. This does not exclude an untested checksum convention, external metadata, an updater-enforced policy or hardware-specific behavior.

The 508-byte tail at file offsets `0xD6FC..0xD8F7` is read by the actual runtime memory initializer. Its use was observed under Unicorn, so it was not treated as disposable footer or padding. The patch keeps it byte-identical and appends at the exact original EOF. Runtime initialization of the stock and RC2 images produces identical modeled SRAM; no extracted RAM image is published.

SK1 RC1 added 64 bytes while preserving all original bytes outside the hook. The owner subsequently reported that the stock USB updater accepted that candidate, the amplifier rebooted and its three direct commands worked. That establishes a successful experiment on one unit. It does not establish that arbitrary file sizes, images or hardware revisions will be accepted, and does not establish recovery.

SK2 RC2 uses the same hook and appends a 124-byte handler. It does not invent or rewrite a checksum/signature field. Its exact local output is checked by pinned SHA256, whole-image rebuild equality, preserved vector table, expected hook/payload, decoded branch targets, aligned literal, flash bounds and exhaustive changed-region comparison. These are byte-identity and structural checks, not an emulation of the bootloader or an installability guarantee.

See [TECHNICAL_BACKGROUND.md](TECHNICAL_BACKGROUND.md), [FLASH_LAYOUT.md](FLASH_LAYOUT.md), [SK1_VALIDATION.md](SK1_VALIDATION.md), and [SK2_RC2.md](SK2_RC2.md). No hidden acceptance-only update mode or validated recovery procedure is claimed.
