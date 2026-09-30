# QUAD 3 Custom Firmware

> [!CAUTION]
> **USE AT YOUR OWN RISK.**
>
> This project modifies firmware on physical hardware. A mistake, hardware revision difference, interrupted update, incorrect firmware image, unexpected bootloader behavior, or software defect may render your QUAD 3 partially or completely unusable.
>
> The project owner and contributors make no warranty and no promise that any firmware patch, address, IR mapping, update procedure, generated binary, or recovery procedure is correct for your amplifier.
>
> If you install modified firmware, **you accept the entire risk yourself**.
>
> The authors are not responsible for damaged or bricked hardware, repair costs, loss of warranty, loss of functionality, data loss, downtime, consequential damage, or any other loss arising from use of this project, to the maximum extent permitted by applicable law.

An independent community project to add direct input selection to **QUAD 3 System Firmware v1.14j**, using numeric buttons on the stock remote in amplifier mode. It is not affiliated with or endorsed by QUAD, IAG, or their distributors. Read the full [disclaimer](DISCLAIMER.md).

## Current status

| Revision | Status |
|---|---|
| SK1 RC1 | The owner reports successful installation through the stock USB updater, a successful reboot, and working direct selection of USB, AUX1, and ARC on **one physical QUAD 3**. |
| SK2 RC2 | **Release Candidate — unverified on hardware.** The owner has supplied physical IR captures for buttons `0–7`. Local generation and qualification results are recorded in the [RC2 report](docs/SK2_RC2.md). No RC2 hardware test has been reported. |

The SK1 observations establish results on that unit only. They do not establish compatibility with every hardware revision, a complete regression pass, or a recovery procedure. See [SK1 validation](docs/SK1_VALIDATION.md) and [the RC2 status report](docs/SK2_RC2.md).

## Intended SK2 layout

This is the required RC2 layout. The owner supplied VS1838B/ESP32 captures for physical buttons `0–7` in amplifier mode. Buttons `0–2` also have the SK1 hardware observations above. Physical identities come from that evidence, not from numeric order or consecutive firmware IDs.

| Button | SK1 hardware observation | Intended SK2 input | Source ID |
|---:|---|---|---:|
| `0` | USB | USB | 1 |
| `1` | AUX1 | AUX1 | 5 |
| `2` | ARC | AUX2 | 6 |
| `3` | Not established | Phono | 7 |
| `4` | Not established | Coax | 3 |
| `5` | Not established | Optical | 2 |
| `6` | Not established | ARC | 4 |
| `7` | Not established | Bluetooth | 0 |
| `8` | Not established | Reserved; no added function | — |
| `9` | Not established | Reserved; no added function | — |

**Button `2` deliberately changes from ARC in SK1 to AUX2 in SK2. ARC moves to button `6`.** All eight assignments in the RC2 image still require physical validation. The [IR evidence](docs/IR_CODES.md) distinguishes owner-reported captures, hardware observations, firmware analysis, and inference. The machine-readable record is [data/ir_mapping.json](data/ir_mapping.json).

## How the patch works

The baseline is an ARM Cortex-M3 / Thumb-2 application at `0x08010000`, consistent with an STM32F100-family device. The exact MCU marking and hardware revision have not been independently read.

SK1 replaces one four-byte instruction site in the stock IR dispatcher and appends a short handler. SK2 retains that strategy: recognize an established short-release event, call stock housekeeping, write the requested source at `0x20000ED3`, and enter the stock source-selection tail at `0x080134D4`. The existing request function and worker perform switching, mute, routing, UI updates, and persistence. Other events return to the original dispatcher path.

The project does not introduce another source state machine. Preserving stock Power, Volume, Mute, front-panel controls, USB Audio, ARC/CEC, protection, trigger behavior, and NVRAM is a design requirement; it still needs regression evidence for each candidate. See [technical background](docs/TECHNICAL_BACKGROUND.md) and [flash layout](docs/FLASH_LAYOUT.md).

## Local generation and verification

No vendor firmware is distributed here. Obtain the required original image legally and retain it unchanged. The patcher must accept only its exact size, hash, and expected patch-site bytes, then produce a separate output and manifest locally. Generated files belong in an ignored directory.

Using Python, with a legally obtained baseline outside tracked files:

```sh
python -m unittest discover -s tests -v
python firmware_patch.py --input "path/to/original.bin" --output generated/QUAD3_v1.14j-SK2-RC2.bin --manifest generated/patch_manifest_sk2_rc2.json
python qualify_rc2.py --input "path/to/original.bin" --candidate generated/QUAD3_v1.14j-SK2-RC2.bin
```

Do not proceed on any failed check. Read [tests/README.md](tests/README.md), the [RC2 report](docs/SK2_RC2.md), and [release process](docs/RELEASE_PROCESS.md) for dependencies, local emulator checks, and the actual verification scope. A static check or passing synthetic test is not an emulator pass; an emulator pass is not physical validation.

## Installation and USB media

RC2 has not been physically validated. Candidate installation remains entirely at the user's risk; read the [installation guide](docs/INSTALLATION.md) and check the exact candidate's qualification report first. Recovery is not established or guaranteed.

The QUAD 3 updater appears sensitive to USB media. In one verified test, a 32 GB FAT32 drive repeatedly failed with `FILE CAN'T FIND`, while an 8 GB FAT32 drive successfully completed the update. Small, simple USB 2.0 FAT32 media are therefore recommended. This owner-reported result does **not** make exactly 8 GB mandatory or prove that every 32 GB drive fails. See [USB updater notes](docs/USB_UPDATER_NOTES.md).

## Project policy

Keep changes small, reproducible, and traceable to evidence. Preserve the vendor image, use the native source path, reject unsupported inputs, and report blocked work honestly. Publish source, patch definitions, hashes, and appropriately scoped reports; keep original and modified firmware, bootloader dumps, and proprietary extracted data out of Git history, issues, CI artifacts, and release assets.

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md). The [MIT license](LICENSE) covers original project contributions only; it grants no rights to QUAD/IAG firmware or other third-party material. RC2 remains a **Release Candidate** and must not be described as stable before separate physical validation of all eight inputs and review.
