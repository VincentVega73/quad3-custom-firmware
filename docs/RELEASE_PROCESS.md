# Candidate and release process

**Current status: SK2 RC2 is a Release Candidate, owner-tested on one physical amplifier.** The owner reports successful installation and operation; see [hardware validation](SK2_HARDWARE_VALIDATION.md). Owner-reported captures now establish physical numeric mappings `0–7`. Use the [RC2 report](SK2_RC2.md) for the exact output and actual software qualification results; the presence of this process document does not establish that its checks passed.

## 1. Establish evidence

Review the capture evidence in [IR_CODES.md](IR_CODES.md). Record each physical key's mode, raw capture where available, NEC address/command/inverse bytes, decoder representation, internal ID/event, stock behavior, and intended target. Validate the evidence against the local stock firmware. If any future change lacks reliable physical evidence, stop generation, issue a capture request, and do not fill unknown keys by sequential inference or create a bypass.

Keep buttons `8/9` without added functions. Confirm that `2` intentionally changes from SK1 ARC to SK2 AUX2 and that `6` selects ARC.

## 2. Prepare a local candidate

Work on `feature/sk2-rc2`, preserving the original baseline and using a legally obtained local vendor image. Follow the actual CLI and dependency instructions in [tests/README.md](../tests/README.md) and [SK2_RC2.md](SK2_RC2.md). Generate only into an ignored local directory, with a separate manifest. Never overwrite the input.

Before accepting output, require exact original size, SHA256, and patch-site checks; deterministic output; reviewed hook and handler bytes; unchanged vector table and all unrelated vendor bytes; valid Thumb branches and literals; preserved registers and eight-byte call-stack alignment; and exclusive EOF at or below the assumed boundary `0x08020000` without using any address at or above it. Resolve any stricter implementation limit in favor of refusing the candidate.

Record the final size, SHA256, handler range, EOF, remaining capacity, and every changed range. Update the stock-to-SK2 and SK1-to-SK2 diff documents with actual output facts. Pending figures must not become invented release values.

## 3. Qualify the exact output

Run public tests without firmware and the local qualification/emulator checks with the real supported input. Bind reports to the exact input, output, and relevant tool revisions. A candidate fails if there is an unexpected changed region, invalid branch, unproven ABI, flash overflow, or source-state regression.

Exercise all eight inputs from another and the same source, rapid repeats, two rapid different commands, and commands during unfinished transitions. Include USB → AUX1 → AUX2 → Phono → Coax → Optical → ARC → Bluetooth → USB, plus USB → USB, ARC → ARC, and Phono → Phono. Execute real modified instructions and native worker/routing/persistence logic where applicable; list every mocked call and concurrency limitation. Retain stock USB/CEC/protection behavior and do not add unnecessary modifications.

Report synthetic, static, emulator, and hardware results separately. Skipped tests remain skipped. Historical SK1 evidence is not an RC2 pass. Do not flash to compensate for a failed software check.

## 4. Review and publish source

Use logical commits and open a PR to `main`. Include the final target mapping, evidence status, changed binary ranges, test and emulator results, unresolved risks, hardware status, and an explicit statement that no proprietary firmware is included. A blocked preparation PR must say it is blocked and must not claim the eight-input patch is complete. Do not merge automatically.

Before pushing, inspect staged and tracked files plus all commits being published. Exclude original and modified firmware, bootloader dumps, proprietary extracted code/data, and vendor blobs regardless of filename. Do not upload them through PR attachments or CI artifacts. `.gitignore` is a guard against accidents, not proof that the complete history is clean.

CI must run without the vendor image. It may exercise syntax, static data, synthetic fixtures, and manifest validation. Local-only tests must have explicit instructions and accurately recorded results.

## 5. Candidate and hardware status

After evidence, generation, qualification, and review succeed, an appropriate candidate tag is `v1.14j-sk2-rc2`. Do not create it while blocked. Any RC2 available before full physical validation must be labeled **Release Candidate — unverified on hardware**, not stable.

Use [INSTALLATION.md](INSTALLATION.md) only after those gates pass and only at the owner's decision and risk. Record the exact installed file hash and media. Validate all eight direct inputs and stock regressions, including audio, repeats, unfinished transitions, normal controls, ARC/CEC, and persistence. Distinguish untested features from passed ones. Hardware testing does not establish universal compatibility or recovery.

Promotion after successful physical validation requires a separate review of the complete results. No automatic merge, stable label, or release promotion is authorized by this process.

## Public release contents

Permitted assets include original project source, patch definitions, manifests containing no firmware dump, hashes, and reports. **Do not attach vendor-derived `.bin` files**, original vendor images, bootloader dumps, or proprietary extracted material. Users generate their own local image from a lawfully obtained baseline. Preserve the prominent disclaimer and license exclusions in every release description.
