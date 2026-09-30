# Physical remote codes and firmware events

The owner supplied results from an earlier **VS1838B/ESP32 physical capture** of the stock QUAD remote in **AMP / A** mode. These are physical capture observations reported by the owner; this task did not independently repeat the capture. The capture session date, receiver firmware version and original raw timing log were not supplied. Buttons 0/1/2 also have separate SK1 hardware-action confirmation on one amplifier.

Each captured command was independently resolved through the exact vendor image's decoder representation and command table. Internal IDs below were obtained by table lookup, not inferred from button numbering or the numerical NEC command.

## Confirmed mapping

All command and address bytes in this document are **hexadecimal**. The address bytes on the wire are `32 EE` for every active row. The inverse command is the fourth byte; it is not a second address byte.

| Physical button | Full NEC bytes | Decoder command | Table file offset | Internal ID (decimal) | Short-release event | Intended SK2 source (ID) | SK1 hardware observation |
|---:|---|---|---|---:|---|---|---|
| 0 | `32 EE 33 CC` | `CC` | `0xCB82` | 23 | `0x5017` | USB (1) | USB |
| 1 | `32 EE 23 DC` | `C4` | `0xCB84` | 24 | `0x5018` | AUX1 (5) | AUX1 |
| 2 | `32 EE 24 DB` | `24` | `0xCB86` | 25 | `0x5019` | **AUX2 (6)** | ARC |
| 3 | `32 EE 25 DA` | `A4` | `0xCB88` | 26 | `0x501A` | Phono (7) | Not assigned/tested |
| 4 | `32 EE 26 D9` | `64` | `0xCB8A` | 27 | `0x501B` | Coax (3) | Not assigned/tested |
| 5 | `32 EE 27 D8` | `E4` | `0xCB8C` | 28 | `0x501C` | Optical (2) | Not assigned/tested |
| 6 | `32 EE 28 D7` | `14` | `0xCB8E` | 29 | `0x501D` | ARC (4) | Not assigned/tested |
| 7 | `32 EE 29 D6` | `94` | `0xCB90` | 30 | `0x501E` | Bluetooth (0) | Not assigned/tested |
| 8 | Not supplied | Unknown physical mapping | — | — | — | Reserved; no added function | Not tested |
| 9 | Not supplied | Unknown physical mapping | — | — | — | Reserved; no added function | Not tested |

All eight active commands are accepted/mapped by stock firmware. No functional case for their short-release events was found in the reviewed dispatcher and prehandlers. This is a bounded reverse-engineering result, not a claim that every possible stock context was tested on hardware.

**No SK2 source assignment has been tested on an amplifier yet.** Button 2 intentionally changes from SK1 ARC to SK2 AUX2; ARC moves to button 6. The provenance and null fields for reserved buttons are machine-readable in [ir_mapping.json](../data/ir_mapping.json). The complete semantic stock table is in [firmware_ir_commands.json](../data/firmware_ir_commands.json); it does not establish physical labels by itself.

## Bit order and address-bank isolation

NEC transmits bits within each byte least-significant first. Some receiver libraries display the extended address as `0xEE32`. The stock firmware accumulates incoming bits by shifting left, producing address `0x4C77` and the bit-reversed command shown above. The table occupies `0x0801CB68..0x0801CBAF`; its entries are decoder-command/internal-ID byte pairs. The short-release event is `0x5000 + internal_id`; long-release events use `0x7000 + internal_id` and are not added by this patch.

For example, physical button 3 supplies command `0x25`; bit reversal produces `0xA4`. The entry at file offset `0xCB88` maps that byte to ID 26 (`0x1A`), giving event `0x501A`. Only then is that event assigned to source ID 7 (Phono).

In **CD** mode the remote uses wire address bytes `33 FD` (stock decoder representation `0xCCBF`). The existing decoder restricts that bank to its native Power/Mute handling. SK2 leaves the decoder and table unchanged and intercepts only the eight AMP short-release events after native guards. Decoder tests must show that CD numeric frames do not generate the added source requests.

The supplied inverse bytes satisfy `command XOR inverse == 0xFF`. The inspected stock decoder does **not** validate the inverse byte; SK2 does not change this behavior. An unmapped raw command may leave a previous internal ID stale. Do not describe all unknown frames as harmless or add arbitrary transmitter codes without checking the complete decoder/event path.

The general NEC framing reference is [Vishay, Data Formats for IR Remote Control](https://www.vishay.com/docs/80071/dataform.pdf). The specific remote values above come from the owner's captures and the firmware, not from that generic protocol reference. Carrier frequency was not measured in this task.

## Evidence classification

| Claim | Classification | Limitation |
|---|---|---|
| Labels 0–7 and wire frames in AMP/A mode | Confirmed from physical capture, as reported by owner | No fresh capture or archived timing log in this repository |
| Labels 0/1/2 produce USB/AUX1/ARC under SK1 | Owner-reported physical hardware observation | One tested unit; applies to SK1 |
| Decoder bytes, table IDs and event formation | Confirmed from exact firmware and checked by emulation | Peripheral/timing inputs are modeled |
| SK2 target source IDs | Project design requirement | Real amplifier behavior remains unverified |
| Physical codes for 8/9 | Unverified and reserved | No event assignments invented |
| Flash-family capacity model | Inference | Not a physical MCU identification |

Future capture reports should record remote mode/model, receiver and tool version, byte-order convention and three independent short presses per label. Include full frames rather than repeat-only messages. Preserve contradictory evidence instead of extrapolating neighboring labels.
