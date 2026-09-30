# Audit independent of the patch builder

`tests/local/review_rc2.py` reads the original and finished candidate directly and does not import `firmware_patch.py`. It pins both SHA256 values and independently checks the changed byte positions. This is a separate implementation of checks, not an external certification or hardware audit.

The recorded run in [independent_review_rc2.json](../evidence/independent_review_rc2.json) passed for candidate SHA256 `08555b7437781bcef803f6469eb56428aa1dc30716a262938f7b211a0e863146`:

- 19 branch checks, including hook entry, every conditional and local branch, stock fallback, housekeeping and native tail. Each target is an instruction boundary and within its Thumb encoding's displacement range.
- 120 bytes of complete halfword-aligned instructions; a separate aligned four-byte literal at `0x0801D970` resolves to `0x20000ED3` through the actual PC-relative load.
- Balanced `{r1,r2}` saves/restores, plus unchanged dispatcher prologue/epilogue preserving the outer `r5` frame.
- 60 fallback comparisons across event boundaries and incoming flag patterns; registers, flags, SP and LR match the displaced stock operations.
- 16 active handler cases covering all eight sources and two initial stack positions. Every executed handler instruction keeps eight-byte stack alignment. The housekeeping stub deliberately clobbers `r0–r3`, and every request still reaches the correct native tail with the correct source.
- All 55,540 original bytes outside the four-byte hook remain identical. Named preserved ranges additionally cover vectors, USB, CEC, routing, digital audio coordination, protection, power, Bluetooth, NVRAM, defaults, front-panel source logic, worker, decoder/table, version string and initialized-data tail.

Run locally after installing `requirements-emulation.txt`:

```console
python tests/local/review_rc2.py --original firmware/stock.bin --candidate generated/QUAD3_v1.14j-SK2-RC2.bin --report generated/independent_review_rc2.json
```

The report contains addresses, hashes and test facts, not firmware or extracted RAM. Original and candidate inputs are read only; report/input aliases are rejected. Report generation does not communicate with the amplifier.

The ABI experiment stubs only the housekeeping entry and stops at the native tail. Full dispatcher and worker execution belongs to the separate local suites. Named subsystem boundaries are reviewed anchors, not complete subsystem reconstructions; byte identity is broader than behavioral coverage. This audit does not validate the physical MCU, updater, peripherals, audio, timing, concurrent CEC, physical NVRAM or recovery.
