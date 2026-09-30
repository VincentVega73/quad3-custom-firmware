> [!CAUTION]
> **USE AT YOUR OWN RISK.** Modified firmware may leave your amplifier partially or completely unusable. No warranty, compatibility, or recovery is promised. Installing it is entirely your decision and risk. Read [DISCLAIMER.md](../DISCLAIMER.md).

# Installation reference

**SK2 RC2 is a Release Candidate and has not been physically validated.** Check the exact candidate's [qualification status](SK2_RC2.md) before considering installation. This reference does not certify a candidate or establish compatibility with your amplifier.

## Before a candidate update

Use only a candidate generated from the exact supported, legally obtained original image. Keep the original unchanged and separate. Check the candidate SHA256 and size against the manifest from the same build, and require the local qualification report to pass. Recheck the installation copy after writing it to USB. A matching hash proves file identity, not hardware compatibility.

Record your existing firmware versions, hardware information if known, settings, and baseline operation. The project has not established compatibility across hardware revisions. The system version display may remain `114j` after patching, so it does not identify the custom image; use the hash and test record.

Use the official instructions supplied with the firmware package for any required filename and directory placement. **This project has not established an exact required updater filename or directory layout.** Do not infer one from the local candidate name or from instructions for another QUAD model. Keep the vendor original intact when creating a separate installation copy.

## USB media

Recommend a small USB flash drive, preferably USB 2.0, formatted as FAT32 with a simple single-partition layout. These are conservative recommendations, not proven universal requirements. USB-media compatibility is imperfect.

The QUAD 3 updater appears sensitive to USB media. In one verified test, a 32 GB FAT32 drive repeatedly failed with `FILE CAN'T FIND`, while an 8 GB FAT32 drive successfully completed the update. Small, simple USB 2.0 FAT32 media are therefore recommended. Exactly 8 GB is not mandatory, and the observation does not establish a universal upper capacity limit. See [USB updater notes](USB_UPDATER_NOTES.md).

## Stock update sequence

The [official QUAD 3 manual](https://quad-hifi.co.uk/cdn/shop/files/QUAD_3_User_Manual_Online_260506_R31.pdf?v=1778140900726), printed page 6, describes this flow:

1. Switch off mains power using the amplifier's power switch.
2. Insert the prepared media into the **USB-A UPDATE** socket.
3. Press the front-panel **STANDBY** button while switching mains power on.
4. Let the automatic update finish and wait for the display to confirm completion.
5. After the completion indication, remove the USB media and restart as the manual directs.

The UPDATE socket is separate from the USB-B audio connection. Consult the manual from the [official manuals page](https://quad-hifi.co.uk/pages/user-manual) and the instructions for your actual package before proceeding.

Entering update mode with a candidate present is a flashing attempt. A separate harmless “validate without writing” stage or mandatory confirmation prompt has not been established. File detection may proceed directly into erase/write. Maintain stable power and leave the media connected while an update is in progress.

If an error occurs after writing might have started, record the exact display and sequence, preserve power and media, and consult applicable guidance for the actual state. This project does not establish that power-cycling, renaming a file, or retrying an update will recover the device. No recovery procedure is provided or guaranteed.

## Record the outcome

After a confirmed completed update and successful boot, record the installed file hash, media, filename, update messages, and versions. Verify numeric source selection against the candidate's documented mapping and check audio, repeats, incomplete transitions, persistence, normal remote/front-panel functions, and relevant ARC/CEC behavior. Report each item as passed, failed, or not tested. Successful boot alone is not a full regression pass.

RC2 requires physical validation of all eight direct inputs before separate consideration for promotion. If behavior differs from the report, preserve the observations and stop further experiments until the discrepancy is understood.
