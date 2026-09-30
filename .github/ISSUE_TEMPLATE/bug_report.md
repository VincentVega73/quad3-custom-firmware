---
name: Bug or hardware observation
about: Report a reproducible tool defect or a precisely scoped device observation
title: ""
labels: ""
assignees: ""
---

Read [the disclaimer](../../DISCLAIMER.md). Do not attach original or patched firmware, memory dumps, credentials, or private device identifiers. Use a minimal synthetic reproducer for software defects where possible.

## Summary

What did you expect, and what actually happened?

## Revision and image identity

- Repository commit:
- Tool command and Python/dependency versions, if relevant:
- Candidate name, size, and SHA256, if one exists:
- Original image size and SHA256, if relevant:
- Qualification result (including failed or skipped checks):

## Device and update context

Complete only if relevant. Do not imply that unknown details were verified.

- Known hardware revision / MCU marking (or unknown):
- System and USB firmware versions:
- USB drive model, capacity, filesystem, and partition layout:
- Actual filename and placement on the drive:
- Exact display messages and their order:
- Had erase/write started, or is that uncertain?
- Did update completion appear? Did the amplifier boot?

## Reproduction and observed scope

List the steps, repeat count, source before and after, audio behavior, and any CEC activity. For IR evidence, give the physical button, remote mode, receiver/tool, raw capture, byte-order convention, address/command/inverse bytes, and repeat frames separately.

State which results are physical observations, emulator results, static findings, or inferences. List relevant features that were not tested. Attach only non-proprietary logs or photos that do not expose private information.

## Regression / comparison

Does the issue also occur with stock firmware or a prior candidate? State only comparisons actually performed. Do not attempt another flash or a recovery procedure solely to fill this section.
