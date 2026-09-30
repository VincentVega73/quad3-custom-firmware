# Security and safety reports

There is no security-support guarantee or guaranteed response time. SK2 RC2 is a Release Candidate unverified on hardware; SK1 hardware observations cover one unit only. Read [DISCLAIMER.md](DISCLAIMER.md).

Report reproducible patcher validation bypasses, unintended output overwrites, unexpected changed ranges, ABI failures, or source-state regressions through this repository. Include the affected commit, command, expected result, actual result, and a minimal synthetic reproducer where possible. Do not attach proprietary firmware, memory dumps, credentials, or personal identifiers.

If GitHub offers **Report a vulnerability** in the repository's Security tab, use it for sensitive security details. If it does not, open an issue requesting a private reporting channel without disclosing those details. This document does not claim that private reporting is enabled or that a specific contact channel exists.

For update failures, state the last observed display message and whether erase/write had started or was uncertain. Do not assume that a power cycle or another flash attempt is a recovery procedure. Preserve diagnostic information and refer to applicable vendor guidance for the actual device state. No recovery procedure has been established by this project.

Maintainers should reproduce software defects using synthetic fixtures first, retain the exact affected commit and hashes, document the scope of any fix, and withdraw affected qualification claims. A failing safety-relevant check blocks candidate generation and publication as an installable release.
