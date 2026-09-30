# Published evidence

Only hashes, patch definitions, addresses, test observations and reports belong here. Original/modified firmware, bootloader dumps, proprietary extracted code and RAM snapshots are not included. Obtain the exact baseline legally and generate the candidate locally.

| Record | What it establishes | What it does not establish |
|---|---|---|
| `owner_observations.json` | Owner-reported SK1 installation/operation on one unit and VS1838B/ESP32 captures for physical buttons 0–7 | Independent recapture, universal compatibility or RC2 hardware behavior |
| `patch_manifest_sk2_rc2.json` | Pinned baseline/candidate identity, source targets and exact patch regions | Updater acceptance or physical correctness |
| `static_qualification_rc2.json` | File/hash/layout, vectors, hook/payload, branch and literal checks against the local original | Instruction-execution or physical tests |
| `independent_review_rc2.json` | Separate builder-independent hash/diff/Thumb/ABI checks with a clobbering housekeeping stub | Full peripheral implementation or certification |
| `verify_dispatcher_rc2.json` | Real decoded instructions, event/fallback equivalence, register/stack and RAM checks, captured AMP/CD frame paths | Every possible RAM state, arbitrary interrupts or physical receiver timing |
| `verify_transitions_rc2.json` | Native worker, routing-image and persistence logic under the explicit stub model | Real analog routing, CEC concurrency, flash programming or recovery |
| `emulation_verification_rc2.json` | Input/output identities and hashes binding local execution reports and their supporting source | Hardware validation |

The scripts and rerun commands are documented in [tests/README.md](../tests/README.md) and [INDEPENDENT_REVIEW.md](../docs/INDEPENDENT_REVIEW.md). Reports identify SK2 RC2 separately from historical SK1 observations; a pass in one category does not imply a pass in another. No RC2 physical test has been performed as part of this task.
