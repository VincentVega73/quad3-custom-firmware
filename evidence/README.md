# Published evidence

Only hashes, patch definitions, addresses, test observations and reports belong here. Original/modified firmware, bootloader dumps, proprietary extracted code and RAM snapshots are not included. Obtain the exact baseline legally and generate the candidate locally.

| Record | What it establishes | What it does not establish |
|---|---|---|
| `owner_observations.json` | Owner-reported SK1/RC2 installation and operation on one unit, plus VS1838B/ESP32 captures | Independent recapture, universal compatibility or an exhaustive per-feature checklist |
| `rc2_hardware_validation.json` | Subsequent owner-reported successful RC2 installation and operation | Independently measured installed hash or itemized regression coverage |
| `patch_manifest_sk2_rc2.json` | Pinned baseline/candidate identity, source targets and exact patch regions | Updater acceptance or physical correctness |
| `static_qualification_rc2.json` | File/hash/layout, vectors, hook/payload, branch and literal checks against the local original | Instruction-execution or physical tests |
| `independent_review_rc2.json` | Separate builder-independent hash/diff/Thumb/ABI checks with a clobbering housekeeping stub | Full peripheral implementation or certification |
| `verify_dispatcher_rc2.json` | Real decoded instructions, event/fallback equivalence, register/stack and RAM checks, captured AMP/CD frame paths | Every possible RAM state, arbitrary interrupts or physical receiver timing |
| `verify_transitions_rc2.json` | Native worker, routing-image and persistence logic under the explicit stub model | Real analog routing, CEC concurrency, flash programming or recovery |
| `emulation_verification_rc2.json` | Input/output identities and hashes binding local execution reports and their supporting source | Hardware validation |

The scripts and rerun commands are documented in [tests/README.md](../tests/README.md) and [INDEPENDENT_REVIEW.md](../docs/INDEPENDENT_REVIEW.md). Reports identify SK2 RC2 separately from historical SK1 observations; a pass in one category does not imply a pass in another. The owner subsequently reported successful physical RC2 installation and operation; see [the hardware report](../docs/SK2_HARDWARE_VALIDATION.md). Frozen build manifests, emulator reports and `data/ir_mapping.json` retain their pre-installation snapshot fields (including false/NOT_PERFORMED hardware flags). Those fields describe what the original generation/verification runs established; `rc2_hardware_validation.json` records the current owner-reported hardware status without rewriting historical test evidence.
