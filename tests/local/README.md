# Local instruction-execution validation

These suites require a user-supplied, legally obtained copy of the exact QUAD 3
v1.14j stock image. They execute actual stock and modified Thumb instructions
under Unicorn. Neither a vendor image nor an extracted SRAM snapshot is stored
in this directory. Read the [project disclaimer](../../DISCLAIMER.md) before
generating or installing firmware.

## Run

From the repository root, with Python and the native emulator wheels available:

```console
python -m pip install -r requirements-emulation.txt
python firmware_patch.py --input firmware/stock.bin
python qualify_rc2.py --input firmware/stock.bin --candidate generated/QUAD3_v1.14j-SK2-RC2.bin
python tests/local/run_rc2_validation.py --original firmware/stock.bin --candidate generated/QUAD3_v1.14j-SK2-RC2.bin
```

`firmware/stock.bin` is a local input placeholder. The SHA256 and exact image
size are enforced regardless of its filename. Keep it in an ignored location;
do not commit or upload it. Use each tool's `--help` for output options.

The runner writes JSON under `generated/emulation/`. It fails on a subprocess
failure, incorrect candidate, or failed check. It checks both inputs again at
completion and records script hashes, report hashes, and runtime versions in
`emulation_verification_rc2.json`. The individual suites also accept explicit
`--original`, `--candidate`, and `--output` paths. Their report paths cannot
alias either input image.

If the two individual suites have just been run, `--collect-existing` combines
their existing reports without running them again. It checks the stock and
candidate identities, PASS status, and the required eight-source coverage,
then binds the current source and report text hashes. This mode is explicitly
recorded as `existing_reports`; it is not a new emulator run and must not be
used after semantic test changes without rerunning the affected suite. Source
and JSON hashes use UTF-8 text with CRLF normalized to LF so that Git line-ending
conversion does not invalidate otherwise identical evidence. Firmware hashes
always use the original raw bytes.

Do not use `python -O`: these are assertion-based validation suites and they
explicitly reject optimized execution. The production patcher and qualifier
use ordinary exceptions rather than relying on assertions.

## Independent handler review

The separate builder-independent handler review is also reproducible:

```console
python tests/local/review_rc2.py --original firmware/stock.bin --candidate generated/QUAD3_v1.14j-SK2-RC2.bin --report generated/independent_review_rc2.json
```

Its branch, literal, fallback-register/flag, stack, and active-target checks are
additional evidence; they do not replace the two complete execution suites.

## Runtime initialization

`emulate_startup.py` runs the real initializer at `0x0801CBE8` in mapped emulator
memory. Stock and candidate initialized SRAM must match. The 8,120-byte initial
RAM state stays in memory and is reconstructed for every invocation; no vendor
RAM blob is needed or exported. The CPU has no connection to physical devices.

## Dispatcher and decoder suite

`verify_dispatcher_rc2.py` validates:

- independent Keystone assembly of the public handler and hook bytes;
- branch targets at decoded instruction boundaries, unchanged vectors, and
  candidate equality to the frozen deterministic build;
- every 16-bit event except the eight intended short-release additions, with
  fallback register, stack, and APSR equivalence at the stock return site;
- all original table IDs in eight event forms, eight sources, seven power
  states, and seven representative UI pages;
- eight new commands across all 32 UI pages, eight sources, and four existing
  cleanup/transition-state profiles;
- exact native Source-next side-effect equivalence when both paths select the
  same source;
- all 36 table commands under both stock address banks;
- the owner's eight AMP-mode capture frames through the real decoder, event
  generator, patched dispatcher, and requested-source write;
- filtering of those numeric frames under the CD address bank, plus the stock
  decoder's failure to enforce an inverse-command byte;
- all 64 prior-AMP/current-CD numeric pairs without resetting decoder RAM,
  preserving an incomplete source transition after the AMP event was consumed;
- eight-byte handler stack alignment and preserved callee-saved registers.

Only the 18 explicit external targets in `STUB_TARGETS` may be stubbed. Their
addresses and observed callsites are in the report. Every stub returns zero,
sets caller-saved r1-r3 to zero, and resumes after the intercepted call. An
unlisted target or execution outside approved code ranges fails immediately.
This suite does not run the source worker; the separate worker suite does.

## Native worker, routing, and persistence suite

`verify_transitions_rc2.py` runs the real dispatcher, housekeeping, source
request, worker, routing-image generator, UI tail, timer fragments, settings
pack/save, flash-record scan, and restore code. The Bluetooth helper at
`0x08014446` also executes: its actual instruction stores 1 at `0x20000F53`.

The scenarios cover:

- every target matched against a stock Source-next request, across worker
  stages 0-4, zero/nonzero timers, ready flags 0/1, and all eight applied IDs;
- every initial/target source pair, including same-source ready fast exits;
- completed same-source repeats for all eight sources with both ready states;
- three immediate repeats for every command and every ordered pair of two
  different commands before the worker runs;
- every old/new target pair during stages 1-4, zero/nonzero timers, and two
  AUX2/AV-direct contexts; the latest request must win through the stock path;
- USB -> AUX1 -> AUX2 -> Phono -> Coax -> Optical -> ARC -> Bluetooth -> USB,
  checking analog one-hot routing bits and optical/coax/ARC selector bits;
- power/protection gates compared with stock, without resetting an existing
  transition;
- all eight source IDs packed into the unchanged seven-word NVRAM format and
  restored by the stock scanner/restore. The requested source is deliberately
  changed before restoration, including when testing Bluetooth ID zero.

The worker retains a strict 12-call hardware stub allowlist:

| Address | Modeled boundary |
|---|---|
| `0x08011F40` | Routing-image serial output |
| `0x08011A0C` | Analog/digital downstream selection |
| `0x08012B20` | AUX2 AV-direct boundary helper |
| `0x08014B9E`, `0x08014CC6` | Digital/USB coordination |
| `0x08015E9E`, `0x08015E2C` | Digital reconfiguration request |
| `0x08018242` | CEC queue call; argument must be `0xC0` |
| `0x0801ABAE`, `0x0801ABCE`, `0x0801ACC0` | Flash control helpers |
| `0x0801B03C` | Flash-program primitive; writes emulator memory only |

These stubs return zero and clobber r1-r3 to zero. The simulated flash primitive
checks alignment, address, and argument before writing a word in mapped memory.
Unknown calls fail. Physical flash erase/programming is never performed.

## Time model and limits

The source timer runs by executing one original decrement fragment between
worker calls. A full transition consumes 50 + 10 + 100 decrement opportunities.
An already applied source with ready flag 1 completes after 50, leaving timer
10; with ready flag 0 it runs the full transition. These are firmware counter
operations, not measured milliseconds. The separate save timer executes its
own original decrement fragment and is not assigned the same frequency.

The tests exercise finite states with explicit external-call models. They do
not establish physical audio correctness, peripheral timing, arbitrary
interrupt preemption, concurrent CEC/USB/power/protection task scheduling,
physical NVRAM endurance or power-loss behavior, updater acceptance, actual
MCU flash capacity, or recovery. A passing emulator report is not a hardware
test. RC2 remains physically untested until a separate owner experiment.

Results from these suites belong to the exact RC2 hash in their reports. They
must not be combined with or relabeled from the historical SK1 counts.
