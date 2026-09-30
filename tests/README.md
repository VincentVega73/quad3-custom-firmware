# Validation

Public CI runs without vendor firmware and without emulator packages:

```sh
python -m compileall -q firmware_patch.py qualify_rc2.py tests
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
```

The unit tests cover exact input rejection, mapping evidence consistency, NEC
bit order and inverses, reserved buttons, source-file and hard-link protection,
preservation of existing output files, manifest rejection for a different image,
deterministic synthetic layout, branch-target decoding, corrupt candidate
rejection, and checks remaining active with Python optimization enabled.

Synthetic tests create filler in a temporary `generated/unit-*` directory and
substitute its hashes **inside the test process only**. They exercise file and
layout handling without distributing firmware. The command-line tools provide
no hash override, force option, or unverified-mapping bypass. Synthetic tests
do not qualify a real firmware image.

The publication guard checks Git-tracked filenames for firmware, archives, and
private output directories, then requires strict UTF-8 text. It cannot identify
proprietary material embedded in text; review the full staged diff separately.

`test_source_transitions.py` is an explicitly skipped integration entry point
in public CI. A skipped check is **not** a passed source-state test. Actual
dispatcher, source-worker, routing-image, persistence, stack, and register
validation uses the instructions from the locally supplied stock and candidate
images. Follow [local/README.md](local/README.md) to run those suites and the
independent handler review. The standard local command is:

```sh
python tests/local/run_rc2_validation.py \
  --original /private/QUAD3-stock.bin \
  --candidate /private/QUAD3_v1.14j-SK2-RC2.bin \
  --output generated/emulation
```

Alternatively, opt in to the integration entry point with environment variables
`QUAD3_RUN_LOCAL_EMULATION=1`, `QUAD3_ORIGINAL`, and `QUAD3_CANDIDATE`, then run
the unit-test command **without** `-O`. Keep those files and environment settings
local; never add the vendor image to GitHub Actions or upload it as an artifact.

Before emulation, build and statically qualify the real image:

```sh
python firmware_patch.py --input /private/QUAD3-stock.bin
python qualify_rc2.py --input /private/QUAD3-stock.bin \
  --candidate generated/QUAD3_v1.14j-SK2-RC2.bin \
  --report generated/static_qualification_rc2.json
```

Static qualification verifies the exact original and RC2 hashes, sizes, vector
table, four-byte hook, 124-byte payload, all changed regions, wide branches,
literal alignment, and the minimum compatible flash boundary. Generation and
qualification are separate from emulator success and physical installation.
No test here establishes bootloader recovery, universal hardware compatibility,
real HDMI/CEC/USB operation, or NVRAM reliability after power loss.
