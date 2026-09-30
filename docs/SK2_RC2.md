# SK2 RC2 qualification report

**Status: Release Candidate — owner-tested on one physical QUAD 3.** The owner reports that RC2 was installed and everything works well. See [the hardware observation and its scope](SK2_HARDWARE_VALIDATION.md). Read [DISCLAIMER.md](../DISCLAIMER.md).

## Identity and target behavior

| Item | Value |
|---|---|
| Baseline | QUAD 3 System Firmware v1.14j, exact pinned SHA256 |
| Local output | `QUAD3_v1.14j-SK2-RC2.bin` |
| Size | 55,668 bytes (`0xD974`) |
| SHA256 | `08555b7437781bcef803f6469eb56428aa1dc30716a262938f7b211a0e863146` |
| Last used address | `0x0801D973` |
| Exclusive EOF | `0x0801D974` |
| Remaining under the inferred 128 KiB model | 9,868 bytes to `0x08020000` |
| Added handler | 124 bytes: 120 code + 4 literal |
| Existing bytes changed | Four, file offset `0x3346..0x3349` |

| Button | Captured NEC frame (hex) | Internal ID | Short event | SK2 source ID / name |
|---:|---|---:|---|---|
| 0 | `32 EE 33 CC` | 23 | `0x5017` | 1 / USB |
| 1 | `32 EE 23 DC` | 24 | `0x5018` | 5 / AUX1 |
| 2 | `32 EE 24 DB` | 25 | `0x5019` | 6 / AUX2 |
| 3 | `32 EE 25 DA` | 26 | `0x501A` | 7 / Phono |
| 4 | `32 EE 26 D9` | 27 | `0x501B` | 3 / Coax |
| 5 | `32 EE 27 D8` | 28 | `0x501C` | 2 / Optical |
| 6 | `32 EE 28 D7` | 29 | `0x501D` | 4 / ARC |
| 7 | `32 EE 29 D6` | 30 | `0x501E` | 0 / Bluetooth |
| 8/9 | Not assigned | — | — | Reserved; no new function |

The owner reports VS1838B/ESP32 captures in AMP/A mode. Every active command was resolved through the exact stock decoder table. No numeric-label extrapolation was used. CD bank `33 FD` is outside the added behavior. [IR_CODES.md](IR_CODES.md) records bit order, table offsets, current stock behavior and evidence limits.

Button 2 intentionally changes from SK1 ARC to AUX2; ARC moves to button 6. Only short-release events are added. The handler preserves the native power/protection guards, calls housekeeping, writes the requested source and enters the existing source tail. It does not implement source routing itself.

## Binary changes and qualification

The stock hook `20 88 C0 1F` is replaced with `0A F0 D7 BA`, branching to `0x0801D8F8`. The appended range is `[0xD8F8, 0xD974)`; the final word at `0xD970` is `0x20000ED3`. All other original bytes, including vectors, decoder/table, runtime initializer tail, source worker, USB/CEC/protection and NVRAM implementation, remain identical.

Exact comparisons are in [stock to SK2](../PATCH_DIFF_STOCK_TO_SK2.md) and [SK1 to SK2](../PATCH_DIFF_SK1_TO_SK2.md). The [manifest](../evidence/patch_manifest_sk2_rc2.json) binds the original hash, candidate hash, source targets and changes. The original display version is not modified.

The following checks passed against the exact RC2 hash above. These are fresh RC2 results; no historical SK1 emulator count is reused.

| Check | Result |
|---|---|
| Public tests, normal and optimized Python | 22 passed per run; one optional local integration test explicitly skipped in this firmware-free suite |
| Static qualification | Original identity, candidate identity, vectors, hook/payload, exhaustive changed ranges, rebuilt bytes, decoded wide branches, literal and flash bounds passed |
| Assembly and separate ABI audit | Frozen payload matched assembly; 19 branch checks, 60 fallback/flag cases and 16 active handler cases passed |
| Dispatcher equivalence | 112,512 stock-equivalent scenarios; 384 active direct-command cases; 2,752 gated target cases; 8,192 extended states |
| Fallback event space | All 65,528 other 16-bit events matched stock trampoline register/flag behavior |
| Native source-tail side effects | 248 comparisons passed |
| Decoder/table | 72 stock table/address-bank cases, all eight captured AMP frame-to-source chains and 64 sequential AMP→CD pairs without resetting RAM passed; CD numeric frames preserved an existing transition |
| Full native source worker | 1,280 complete stock-versus-RC2 transition comparisons passed |
| Incomplete transitions | 1,024 latest-request cases passed |
| Old/target pairs | 128 cases, including same-source ready/non-ready behavior |
| Repeats and rapid commands | 16 completed same-source scenarios, eight triple-repeat scenarios and 56 ordered rapid different-command pairs |
| Required full cycle | USB → AUX1 → AUX2 → Phono → Coax → Optical → ARC → Bluetooth → USB passed |
| Power/protection worker setup | 176 gated cases retained stock behavior |
| Stack alignment in worker suite | 58,545 executed handler-instruction checks passed |
| Persistence | All eight sources packed into seven simulated flash words and restored through native code |

Published reports and their scope are indexed in [evidence/README.md](../evidence/README.md). Reproduction commands and the explicit hardware-call allowlists are in [tests/README.md](../tests/README.md); the builder-independent review is in [INDEPENDENT_REVIEW.md](INDEPENDENT_REVIEW.md). The public CI suite does not contain firmware. Its integration skip is separate from the completed local native runs above.

## Hardware status and unresolved behavior

The owner has now installed RC2 and reports successful operation on one unit. This is a physical observation supplied by the owner, separate from the emulator results. An itemized per-input/regression log and a hash read back from the installed image were not supplied. SK1 was accepted by the stock updater, rebooted and selected its three targets on one owner-tested unit; that is separate evidence described in [SK1_VALIDATION.md](SK1_VALIDATION.md).

For documented regression coverage beyond the general success report, record results for all eight selections and audio paths, same-source repeats, rapid sequences, requests during transitions, persistence after restart, Power/Standby, volume/mute/tone/balance, stock source cycling, front-panel operation, ARC/CEC automatic selection, USB Audio, Bluetooth, trigger behavior, protection, display and factory defaults. Exercise USB → AUX1 → AUX2 → Phono → Coax → Optical → ARC → Bluetooth → USB and repeated USB/ARC/Phono selections. Record what was actually exercised; do not infer full subsystem coverage from a successful boot.

The exact MCU and other hardware revisions remain unidentified. Updater policy, behavior during power loss, flash contents beyond the original EOF and recovery are not fully characterized. There is no experimentally established recovery procedure. The 128 KiB boundary is a compatible-device model, not a capacity read from the amplifier.

Emulation has finite RAM/counter states and explicit hardware stubs. It cannot establish analog audio correctness, real peripheral timing, arbitrary interrupt preemption, concurrent CEC behavior, physical flash programming, USB-updater acceptance or rollback. Preserve native behavior where unusual: same-source requests are not always immediate no-ops, and the stock decoder does not validate the inverse command byte. No warranty or compatibility promise follows from passing offline checks.

RC2 must remain a Release Candidate until separate review of real-hardware results. No vendor-derived binary belongs in a public release, issue, PR, CI artifact or Git history.
