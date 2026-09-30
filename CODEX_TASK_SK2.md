# SK2 / RC2 implementation contract

Target repository: [VincentVega73/quad3-custom-firmware](https://github.com/VincentVega73/quad3-custom-firmware). Baseline: QUAD 3 System Firmware v1.14j. Development branch: `feature/sk2-rc2`; PR target: `main`. Do not merge automatically.

Deliver both a reproducible minimal firmware patch and an English public project with evidence, tests, risk disclosures, and no proprietary firmware redistribution. Documentation is part of the deliverable.

## Established hardware observations

The owner reports that SK1 RC1 installed through the stock USB updater on one QUAD 3, rebooted, operated, and selected USB/AUX1/ARC with physical numeric buttons `0`/`1`/`2` in amplifier mode. A 32 GB FAT32 drive repeatedly produced `FILE CAN'T FIND`; an 8 GB FAT32 drive succeeded. This is not evidence of universal compatibility or an exact capacity requirement.

The owner subsequently supplied VS1838B/ESP32 capture results for buttons `0–7` in amplifier mode: address bytes `32 EE`, command bytes `33 23 24 25 26 27 28 29` respectively, all hexadecimal, with complementary inverse bytes. This resolves the original absence of physical evidence for `3–7`; the records must still distinguish owner-reported capture evidence from firmware validation. The CD-mode bank `33 FD` is separate and must not be treated as an amplifier-mode numeric bank.

## Required target layout

| Button | SK2 target | Source ID |
|---:|---|---:|
| 0 | USB | 1 |
| 1 | AUX1 | 5 |
| 2 | AUX2 | 6 |
| 3 | Phono | 7 |
| 4 | Coax | 3 |
| 5 | Optical | 2 |
| 6 | ARC | 4 |
| 7 | Bluetooth | 0 |
| 8, 9 | Reserved; no added function | — |

Button `2` intentionally changes from SK1 ARC to AUX2. ARC moves to `6`.

For every button `0–7`, establish its physical identity, NEC address bytes, command/inverse bytes, decoder representation, internal ID/event, stock behavior, and target behavior. Label physical captures, owner hardware observations, firmware evidence, inference, and unverified entries accurately. Do not assume sequential IDs. If reliable physical evidence for `3–7` is missing, stop firmware generation and issue a precise capture request.

## Implementation constraints

Retain the proven dispatcher hook and appended handler approach. Use housekeeping `0x080131F8`, requested source `0x20000ED3`, native tail `0x080134D4`, request `0x08012F64`, and worker `0x08012E64`. Do not switch sources directly through GPIO or create a second worker or event queue.

Preserve stock Power/Standby, Volume/Mute, Bass/Tilt/Balance, source next/previous, front-panel controls, all input paths, ARC/CEC automatic selection, trigger behavior, protection, NVRAM format and last-source persistence, factory defaults, and display behavior. Document any intentional deviation; unnecessary changes to stock USB/CEC/protection block release.

Verify Thumb alignment, branch reach, literal pools, register preservation, fallback path, and eight-byte stack alignment across calls. Keep the image below exclusive flash boundary `0x08020000`. Publish exact stock-to-SK2 and SK1-to-SK2 changed ranges when a candidate exists; mark them pending while generation is blocked.

The patcher must reject an incorrect input hash, size, or patch-site bytes; build deterministically; preserve the input; print changed ranges; and produce `QUAD3_v1.14j-SK2-RC2.bin` and `patch_manifest_sk2_rc2.json` locally. Qualification must verify size, expected hash, unchanged vectors, branch/handler bytes, flash bounds, and absence of unexpected changes, exiting nonzero on failure.

## Validation

Test all eight targets from other inputs, from the same input, with rapid repeats, with two rapid different commands, and during unfinished transitions. Include USB → AUX1 → AUX2 → Phono → Coax → Optical → ARC → Bluetooth → USB and USB → USB, ARC → ARC, Phono → Phono.

Where the real firmware is locally available, execute the modified instructions and native dispatcher, worker, routing-image generation, and persistence logic in Unicorn. Verify RAM writes, calls, registers, and stack behavior; list every mocked hardware call. Synthetic tests or inherited SK1 results cannot replace RC2 emulation. Emulation cannot replace hardware validation.

## Publication and release

Maintain the prominent README warning and dedicated `DISCLAIMER.md`. Include the public structure, evidence records, installation/media notes, test instructions, qualification tooling, release process, and an RC2 report answering every requested status question. Use meaningful commits and a PR reporting the actual state, including blockers. CI must work without proprietary firmware and must not upload firmware artifacts.

Keep original and modified firmware images, bootloader dumps, proprietary extracted code/data, and vendor blobs out of the repository and public attachments. Publish original project source, patch definitions, hashes, manifests, and reports only when they contain no such material.

An RC2 that becomes buildable remains a **Release Candidate**. Promotion after successful hardware testing of all eight inputs requires separate review; a possible reviewed candidate tag is `v1.14j-sk2-rc2`. Do not create a tag or release while generation is blocked.

## Stop conditions and completion

Stop installable output for missing physical button evidence, flash overflow, unproven ABI, invalid branches, unexpected changed regions, source-state regressions, or unnecessary changes to stock USB/CEC/protection. Report the blocker; do not guess or describe partial preparation as completed firmware.

The task is complete only when the SK2 code exists, mappings `0–7` are evidence-backed, local generation is reproducible, qualification passes, English public documentation and warnings are complete, proprietary material is excluded, the branch is pushed, and a PR is open. RC2 hardware status must remain explicitly unverified until the owner tests it. The current implementation and validation results belong in [docs/SK2_RC2.md](docs/SK2_RC2.md); this contract is not a substitute for those results.
