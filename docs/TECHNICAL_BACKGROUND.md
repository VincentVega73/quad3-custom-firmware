# Firmware research baseline

This document records reverse-engineering results for one exact vendor image. It does not identify every QUAD 3 hardware revision or establish compatibility. Read [DISCLAIMER.md](../DISCLAIMER.md).

## Identity and evidence boundaries

| Property | Result | Evidence class |
|---|---|---|
| System firmware | QUAD 3 v1.14j | Supplied vendor image |
| SHA256 | `7dff59e986643543c28c7f71c1f43f78c936867b25b078e0c1bd0ea5a6fe3853` | Calculated from the original file |
| Size | 55,544 bytes (`0xD8F8`) | Calculated |
| Format | Raw little-endian ARM Cortex-M3 / Thumb-2 application | Vectors, instruction decoding and bounded execution |
| Application base | `0x08010000` | Vector references and VTOR setup |
| Initial stack pointer | `0x20001FB8` | Initial vector |
| Reset vector | `0x0801D419` (Thumb entry `0x0801D418`) | Reset vector |
| Vector-table extent preserved by SK1 | `0x0000..0x011F` | Static analysis |
| MCU family | STM32F100-compatible | Inference from peripheral/register layout |
| Minimum compatible model | 128 KiB flash, 8 KiB SRAM | Image address requirements and STM32F100xB model; actual chip not read |

The [ST STM32F100x4/x6/x8/xB datasheet](https://www.st.com/resource/en/datasheet/stm32f100cb.pdf) describes the candidate family. It is not evidence that the tested amplifier contains a particular part number. The modeled flash limit is `0x08020000`; see [FLASH_LAYOUT.md](FLASH_LAYOUT.md).

The startup memory initializer at `0x0801CBE8` reads the entire 508-byte image tail `0xD6FC..0xD8F7`. That region cannot be treated as free padding. Bounded searches did not identify an explicit image-local length field, separate signature block or checksum that needs recomputation. This is a negative research result, not proof that every updater lacks validation. The owner subsequently reported successful installation of the exact SK1 RC1 candidate on one unit.

## Native source-selection path

| Address | Role |
|---|---|
| `0x0801C5A2` | IR decoder, EXTI1/PA1 and TIM2 timing path |
| `0x0801CB68` | 36-entry command-to-internal-ID table |
| `0x0801C6C2` | IR event generation |
| `0x20000EAE` | 16-bit IR event mailbox |
| `0x080132E8` | IR dispatcher |
| `0x08013346` | Four-byte SK1 hook (file offset `0x3346`) |
| `0x0801334A` | Stock continuation for unhandled events |
| `0x080131F8` | Existing housekeeping called before a direct request |
| `0x20000ED3` | Requested source byte |
| `0x20000436` | Applied/previous source byte |
| `0x080134D4` | Existing source-selection tail |
| `0x08012F64` | Request: set stage to 1 and timer to 0 |
| `0x08012E64` | Asynchronous source worker |
| `0x08012F8C` | Routing wrapper |
| `0x08011FB4` | Routing-image construction |
| `0x20000EEA`, `0x20000EEB` | Worker stage and timer |
| `0x20000FA7` | Deferred-save countdown |
| `0x08016EF0` | Native page/UI update |

The intended SK2 extension follows the proven path:

```text
stock IR decoder -> stock short-release event -> existing dispatcher guards
 -> appended handler -> housekeeping -> requested-source byte
 -> existing source tail -> request -> worker -> native routing/UI/save
```

The patch must not write GPIOs, bypass the worker or introduce another source state machine. Source IDs are in [source_enum.json](../data/source_enum.json).

The dispatcher retains the original power guard (`0x20000ED1 == 1`) and protection/page guard (`0x20000F29 != 0x12`). The native tail schedules persistence with value 3 and changes the UI to page 4. The original handler prologue preserves `r5`; SK1 additionally pushes/pops `{r1,r2}` to maintain eight-byte stack alignment across calls. Fallback replays the displaced instructions and returns to `0x0801334A`.

## Worker and persistence observations

Under the bounded Unicorn model, normal transitions use timer counts 50, 10 and 100. These are counter decrements, not measured elapsed milliseconds. A new request during a transition resets the worker to stage 1/timer 0; the latest requested source wins without a custom queue.

Selecting the already-applied source is not an unconditional hardware no-op. With ready flag `0x20000EE0 == 1`, the modeled worker stops at stage 2 after 50 decrements, leaves timer 10 and clears bit 0 of `0x20000EEF`. With ready flag 0, the normal modeled 160-decrement path runs. Preserve this behavior instead of adding a shortcut.

The original save/restore logic packs seven words (28 bytes); source selection occupies bits 19:16. Research used the actual serialization and restore instructions with simulated flash storage. It did not exercise physical erase/program operations or prove endurance or interruption behavior.

## Preservation scope

Stock Power/Standby, volume, mute, Bass/Tilt/Balance, source cycling, front-panel controls, ARC/CEC, USB Audio, Optical/Coax, analog inputs, Bluetooth, triggers, protection, NVRAM layout, factory defaults and display behavior remain under native control. RC2 checks establish byte preservation outside the hook, bounded dispatcher equivalence, native source-transition equivalence, routing-image construction and simulated persistence. These checks do not certify every subsystem end to end; physical concurrency, peripheral behavior and audio paths still require hardware tests. Exact results and limitations are in [SK2_RC2.md](SK2_RC2.md).

See [SK1_VALIDATION.md](SK1_VALIDATION.md) for owner observations, [tests/README.md](../tests/README.md) for comparisons against the actual stock instructions, and [SK2_RC2.md](SK2_RC2.md) for candidate qualification and hardware status.
