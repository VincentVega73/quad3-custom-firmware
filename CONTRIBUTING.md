# Contributing

Read [DISCLAIMER.md](DISCLAIMER.md) before hardware work. Contributions must preserve the distinction between physical observations, firmware analysis, inference, and missing evidence.

## Workflow

1. Work on a feature branch and open a pull request against `main`. The SK2 integration branch is `feature/sk2-rc2`.
2. Keep commits focused: separate evidence, implementation, tests, and documentation when practical.
3. Write public documentation, code comments, issue reports, and PR descriptions in English.
4. Run the relevant checks in [tests/README.md](tests/README.md). Report failures, skips, mocked calls, and tests that require a local vendor image.
5. Include the candidate's hash and byte-range diff when a candidate exists. Do not imply that preparation work produced a firmware image.

## Evidence and patch requirements

- Record physical button labels together with remote mode, raw capture, protocol interpretation, byte order, repeats, and the tool used. A firmware table alone does not identify a physical key.
- Do not extrapolate buttons `3–7` from the established SK1 events for `0–2`.
- Use the native source request/worker path. Do not add direct peripheral switching or a second source state machine.
- Preserve stock guards, fallback events, register state, eight-byte stack alignment across calls, and NVRAM format.
- Keep every vendor byte unchanged except the reviewed patch site, and append only the reviewed handler. Explain any proposed expansion of that scope.
- Stop candidate generation if mappings, flash bounds, ABI correctness, branch targets, or regression results are unresolved. Continue independent documentation or test improvements with the blocker stated explicitly.

## Material that must stay local

Do not commit or upload original or modified firmware images, bootloader dumps, proprietary extracted code/data, credentials, or private device identifiers. This applies to issues, PR attachments, GitHub Actions artifacts, and releases as well as Git history. Use legally obtained firmware only in local checks. Share hashes, offsets, original patch code, concise findings, and non-proprietary synthetic fixtures instead.

Ignoring a file does not remove it from Git history. Review the staged diff and tracked file list before committing, and the complete branch history before publication. Do not weaken input verification or add a force option to bypass unresolved IR evidence.

## Hardware reports

Use the issue template and state which tests were actually performed. Include exact image SHA256, known firmware versions, media details, expected versus observed behavior, and whether writing had begun. Do not deliberately trigger protection faults, assume recovery exists, or claim a full regression pass from successful boot alone.

Original contributions are offered under the project [license](LICENSE). Submit only material you have the right to contribute. Vendor and third-party rights are excluded from that license.
