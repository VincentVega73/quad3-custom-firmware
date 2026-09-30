## Problem and result

Describe the concrete change and its current state. If blocked, state the missing evidence and do not claim an installable candidate exists.

## Target mapping and evidence

List affected physical buttons, internal events, and source IDs. Distinguish capture evidence, owner hardware observations, firmware analysis, inference, and unverified entries.

## Binary scope

Give changed ranges, handler range, size, SHA256, EOF, and remaining flash when a candidate exists. Otherwise mark those values as not generated. Explain how the stock source path and fallback behavior are preserved.

## Validation

- Public / synthetic checks:
- Local static qualification:
- Emulator execution and explicit stubs:
- Hardware validation and exact scope:
- Failed, skipped, or unavailable checks:

## Risks and release status

State unresolved IR, ABI, flash, updater, concurrency, hardware-revision, and recovery limits relevant to this change. RC2 is a Release Candidate until separately reviewed hardware validation; a blocked preparation branch is not a completed candidate.

## Publication checks

- [ ] No proprietary firmware, patched vendor image, bootloader dump, or proprietary extracted data is included in this PR or its history.
- [ ] Public documentation and comments are in English.
- [ ] README disclaimer and license exclusions remain prominent and intact.
- [ ] Reports describe only checks actually performed and identify the exact candidate where applicable.
- [ ] Generated binaries and local firmware inputs remain ignored and unpublished.
- [ ] This PR does not request or perform an automatic merge.
