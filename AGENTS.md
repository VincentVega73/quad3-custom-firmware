# Repository instructions

These instructions apply to this repository. They supplement the user's task and do not require additional approval for already authorized, reversible work.

- Keep public documentation, comments, reports, templates, and PR text in English.
- Read `CODEX_TASK_SK2.md`, `DISCLAIMER.md`, and the current `docs/SK2_RC2.md` before changing the candidate workflow.
- Preserve the prominent README disclaimer and the scope of the license. Do not imply vendor affiliation, universal compatibility, safety, or guaranteed recovery.
- Develop through a feature branch and PR to `main`; do not merge without explicit authorization. Use `feature/sk2-rc2` for this task.
- Never commit or publish vendor firmware, patched firmware, bootloader dumps, or proprietary extracted code/data. Keep local inputs and generated outputs in ignored locations. Inspect tracked files and history before publication.
- Do not assign physical numeric buttons by extrapolating firmware ID order. Record physical evidence separately from firmware evidence. Buttons `3–7` require reliable evidence before RC2 generation.
- Preserve the stock source-selection path, event fallback, power/protection guards, stack alignment, register preservation, and persistence format. Do not create another source state machine.
- Patching must verify the exact original size, SHA256, and patch-site bytes; refuse mismatches and input/output aliases. Never change the source image in place.
- Keep the application below the assumed minimum flash limit `0x08020000` until supported evidence establishes a different limit. Do not treat the inferred MCU family as a physical chip identification.
- Run the checks relevant to the change. Distinguish synthetic checks, static analysis, emulation with explicit stubs, and physical tests. Never convert skipped or unavailable tests into passes.
- If a stop condition applies, block installable output, document the missing evidence, and continue useful independent work. Do not create bypass flags to conceal unresolved conditions.
- Keep logical commits and describe the final implementation and actual validation in the PR. Candidate, release, and hardware status must agree across the README, reports, manifests, and PR.
