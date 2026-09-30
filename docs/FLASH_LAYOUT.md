# Flash layout

All ends below are exclusive unless marked "last byte". These are application-file addresses, not a dump of the complete device. The actual MCU identity and flash capacity have not been read from hardware.

| Property | Stock v1.14j | SK1 RC1 | SK2 RC2 |
|---|---:|---:|---|
| Application base | `0x08010000` | `0x08010000` | `0x08010000` |
| File size | 55,544 (`0xD8F8`) | 55,608 (`0xD938`) | 55,668 (`0xD974`) |
| Exclusive EOF | `0x0801D8F8` | `0x0801D938` | `0x0801D974` |
| Last used byte | `0x0801D8F7` | `0x0801D937` | `0x0801D973` |
| Appended handler | None | `0x0801D8F8..0x0801D937` | `0x0801D8F8..0x0801D973` |
| Modeled flash limit | `0x08020000` | `0x08020000` | `0x08020000` |
| Remaining bytes to modeled limit | 9,992 (`0x2708`) | 9,928 (`0x26C8`) | 9,868 (`0x268C`) |

The minimum compatible STM32F100xB model has 128 KiB flash starting at `0x08000000`. The application base leaves 64 KiB between application start and the model limit. The lower 64 KiB is outside the supplied file; its contents were not inspected. No bootloader dump is included.

The model uses 1 KiB flash pages; stock, SK1 and SK2 all end within `0x0801D800..0x0801DBFF`. That calculation alone does not describe the updater's erase strategy or other data stored beyond the file's EOF. The [ST datasheet](https://www.st.com/resource/en/datasheet/stm32f100cb.pdf) supports the candidate family model, not a physical part identification.

SK1 adds 60 bytes of executable instructions followed by a four-byte RAM-address literal at `0x0801D934`. Its only overwritten vendor range is file offset `0x3346..0x3349`; all other original bytes are preserved.

SK2 contains 120 bytes of executable handler instructions and the four-byte literal at `0x0801D970`. The handler is 60 bytes larger than SK1, while the hook stays identical. RC2 SHA256 is `08555b7437781bcef803f6469eb56428aa1dc30716a262938f7b211a0e863146`. Recalculate these fields from the actual candidate with `qualify_rc2.py`; do not identify a firmware image by its filename or display version alone. See the [generated manifest](../evidence/patch_manifest_sk2_rc2.json) and [exact byte diff](../PATCH_DIFF_STOCK_TO_SK2.md).
