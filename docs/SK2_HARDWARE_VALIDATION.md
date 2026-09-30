# SK2 RC2 hardware observation

**Release Candidate — owner-tested on one physical QUAD 3.**

After receiving RC2, the owner reported successful installation and said that everything works great. This updates the project's hardware status from untested to owner-reported successful installation and operation on one amplifier.

The report refers to SK2 RC2, whose published reference candidate is 55,668 bytes with SHA256 `08555b7437781bcef803f6469eb56428aa1dc30716a262938f7b211a0e863146`. An independently measured installed-image hash, hardware revision, test date and itemized per-input/regression checklist were not supplied. The general success report must not be expanded into individual passes for every audio path, ARC/CEC concurrency, persistence scenario, protection condition or recovery procedure.

The intended numeric layout remains 0 USB, 1 AUX1, 2 AUX2, 3 Phono, 4 Coax, 5 Optical, 6 ARC and 7 Bluetooth, with 8/9 reserved. The firmware, patch bytes, hashes and existing offline qualification results are unchanged.

The machine-readable current observation is [rc2_hardware_validation.json](../evidence/rc2_hardware_validation.json). Existing build manifests, emulator reports and IR mapping metadata remain historical pre-installation snapshots; their hardware flags describe the scope of those original runs, not the latest owner report.

RC2 retains its Release Candidate designation. This update does not create a stable release or establish compatibility with other hardware revisions. The [disclaimer](../DISCLAIMER.md), installation risks and absence of an experimentally established recovery procedure remain applicable.
