# USB updater observations

The QUAD 3 updater appears sensitive to USB media. In one verified test, a 32 GB FAT32 drive repeatedly failed with `FILE CAN'T FIND`, while an 8 GB FAT32 drive successfully completed the update. Small, simple USB 2.0 FAT32 media are therefore recommended.

This is an owner-reported physical observation from the SK1 RC1 experiment on one amplifier. The updater accepted the custom image using the successful media, and the amplifier rebooted and operated. See [SK1 validation](SK1_VALIDATION.md).

| Media reported | Observed outcome |
|---|---|
| 32 GB, FAT32 | Repeated `FILE CAN'T FIND` message |
| 8 GB, FAT32 | Successful firmware update |

## What this establishes

USB-media compatibility is imperfect in the reported setup. Exactly 8 GB is **not** mandatory, and the experiment does not show that all 32 GB devices fail or that capacity alone caused the difference. The drive models, USB controllers, partition metadata, and allocation units were not documented in the supplied observation.

For a future qualified candidate, a small drive, preferably USB 2.0, FAT32, and a simple single-partition layout is a conservative recommendation. USB 2.0 and a single partition were not independently established as requirements by this experiment. Formatting an existing drive destroys its contents; use appropriately prepared media without relying on this project to preserve data.

`FILE CAN'T FIND` alone does not identify a firmware checksum failure, signature policy, exact filename requirement, or flash-capacity problem. Record the literal message, file hash and size, file placement, media model, format, partition layout, and update sequence before drawing a conclusion.

## Procedure and limits

The [official QUAD 3 manual](https://quad-hifi.co.uk/cdn/shop/files/QUAD_3_User_Manual_Online_260506_R31.pdf?v=1778140900726), printed page 6, describes the USB-A UPDATE procedure. The reviewed manual passage does not establish a mandatory media capacity, filesystem, filename, or directory layout. Follow any instructions supplied with the official package for the actual device; do not import requirements from other QUAD models.

There is no established harmless detection-only phase. Entering update mode may lead directly to erase/write. Successful installation on one unit does not establish a recovery procedure or a universal bootloader acceptance policy. Refer to [installation](INSTALLATION.md) and [the disclaimer](../DISCLAIMER.md) before any future update attempt.
