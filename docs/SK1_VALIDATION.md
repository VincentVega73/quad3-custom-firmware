# SK1 RC1 validation record

## Physical experiment

The following are **owner-reported observations from one physical QUAD 3**, provided for this project. They establish the reported outcomes; they are not inferred from disassembly or emulator results.

- The SK1 RC1 custom candidate was generated and installed using the stock USB firmware updater.
- The updater accepted the image and completed the update.
- The amplifier rebooted and operated after flashing.
- The added IR source-selection commands worked on hardware with the stock remote in amplifier mode.

| Physical button | Observed SK1 source | SK1 short-release event | Source ID |
|---:|---|---|---:|
| `0` | USB | `0x5017` | 1 |
| `1` | AUX1 | `0x5018` | 5 |
| `2` | ARC | `0x5019` | 4 |

The physical label-to-function relationship comes from the owner's experiment. The event IDs and source IDs come from the identified SK1 implementation. No raw physical capture is claimed by this record. It does not establish the codes of buttons `3–7`.

During that testing, a **32 GB FAT32** USB flash drive repeatedly produced `FILE CAN'T FIND`. An **8 GB FAT32** drive successfully performed the update. The exact media models, controller characteristics, partition details, and cause of the difference were not supplied. See [USB updater notes](USB_UPDATER_NOTES.md).

## Candidate identity

| Image | Size | SHA256 |
|---|---:|---|
| Original v1.14j baseline | 55,544 bytes | `7dff59e986643543c28c7f71c1f43f78c936867b25b078e0c1bd0ea5a6fe3853` |
| SK1 RC1 candidate | 55,608 bytes | `36e78abe00ce2ba7351f29ce695019e9b9a18a263f993d3eddf21f87071f4e98` |

These identify the prepared artifacts in the local RC1 records. A separate hash of the physical USB installation copy was not included in the owner's report. Original and modified firmware files are deliberately excluded from this repository.

SK1 RC1 replaces bytes at file offsets `0x3346–0x3349` and appends a 64-byte handler at `0xD8F8`. The original application starts at `0x08010000`; the candidate ends at exclusive address `0x0801D938`. The existing version display remains unchanged and does not distinguish the custom image.

## Prior software evidence

The local RC1 qualification reports recorded passing checks for exact changed regions, unchanged vectors and stock regions, branch/handler correctness, register preservation, and stack alignment. Unicorn checks exercised the stock dispatcher, source worker, routing-image generation, and simulated NVRAM persistence, including repeated and unfinished transitions. Hardware-facing calls were stubbed explicitly in those tests.

These are **historical RC1 results**, not a claim that those suites were rerun against an RC2 in this repository. They explain why the SK1 architecture is the baseline. They do not prove analog behavior, real flash programming, asynchronous CEC/IRQ interactions, or operation on another hardware revision.

## Scope and limits

The SK1 hardware report supplies no independently verified MCU marking, board revision, exhaustive peripheral regression matrix, failure-recovery experiment, or measurements for buttons `3–7`. The owner subsequently supplied separate VS1838B/ESP32 captures for all eight numeric keys; those are recorded in [IR evidence](IR_CODES.md). Do not interpret general successful SK1 operation as proof that every stock feature was individually tested.

The successful update establishes acceptance of this SK1 candidate on the reported unit. It does not establish that the updater accepts every modified image, that RC2 will work, that a particular checksum policy applies to all revisions, or that interrupted updates are recoverable.

For SK2, button `2` deliberately changes from ARC to AUX2, and ARC moves to `6`. The new RC2 handler and all eight assignments require their own physical validation, including the targets retained from SK1. See [IR evidence](IR_CODES.md) and [RC2 status](SK2_RC2.md).
