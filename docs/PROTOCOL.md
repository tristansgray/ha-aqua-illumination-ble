# Mobius BLE protocol (Aqua Illumination)

Reverse-engineered from Android HCI snoop captures of the myAI app and verified on an **Axis 40** pump (firmware 2.3.15). Other Mobius devices likely share the framing; their attributes are unknown until someone captures them (see [adding-devices.md](adding-devices.md)).

## Device

- Advertises as `MOBIUS`, service UUID `01ff0100-ba5e-f4ee-5ca1-eb1e5e4b1ce0`. macOS hides BLE MAC addresses, so match on name or UUID.
- No pairing, no bonding, no encryption.
- Device Information service (`2a29`/`2a24`/`2a26`/`2a25`): manufacturer `AI`, model `Nero 5` (yes, on an Axis 40), firmware, serial.
- One client at a time: while the myAI app is connected the device stops advertising.

## GATT map

Base UUID: `01ffXXXX-ba5e-f4ee-5ca1-eb1e5e4b1ce0`

| Char | Properties | Use |
|---|---|---|
| 0101 | NOTIFY | Reply fragments (not last) |
| 0102 | NOTIFY | Reply, last fragment |
| 0103 | WRITE NO RSP | Not used by app |
| 0104 | WRITE NO RSP | Commands (app to device) |
| 5551 | WRITE, INDICATE | App enables indicate only |
| 5552 | WRITE NO RSP | Not used by app |

## Connect sequence (as the app does it)

1. Connect. The app requests MTU 517; the pump answers 247.
2. Enable notify on 0101 and 0102, indicate on 5551. The pump sends one indication, `0200000f030242040000df` (meaning unknown).
3. Read attribute `0x03ED` (16 bytes, constant per device). Nothing derived from it is sent back, so it is not a challenge-response. Whether it is required is untested; the integration does it anyway.

## Frame format

```
02 | DIR | OP | SEQ | 00 | FLAGS(2, LE) | LEN(2, LE) | PAYLOAD | CRC(2, LE)
```

- `DIR`: `DE` app to device, `DF` device to app.
- `OP`: `17` read, `18` write, `25` list attributes.
- `SEQ`: increments per request; the reply echoes it.
- `FLAGS`: `0000` for read, `0400` (0x0004) for write.
- `CRC`: CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over `DIR` through end of payload, little-endian. Python: `binascii.crc_hqx(frame[1:-2], 0xFFFF)`.

Example (read `0x03ED`, seq 0x20): `02de17200000000400ed030001ef63`

Replies longer than one notification arrive on 0101 in parts; the last part arrives on 0102. Concatenate, then parse.

## Payload format

- Read request: repeat `[ATTR u16 LE][INDEX u8][COUNT u8]`. COUNT `FF` = all.
- Read reply: `[STATUS u8]` (00 = OK), then repeat `[ATTR u16 LE][INDEX u8][COUNT u8][VLEN u8][VALUE]`.
- Write request: repeat `[ATTR u16 LE][INDEX u8][COUNT u8][VLEN u8][VALUE]`.
- Write reply: `00 FF FF` = OK.

## Known attributes (Axis 40)

| Attr | Index | Size | Meaning | Notes |
|---|---|---|---|---|
| 0x02BC | 0 | u16 | Flow setpoint, 0.1% steps | 100 = 10.0%, 1000 = 100.0% |
| 0x0065 | 11 | u32 | Pump RPM | 1143 at 10%, 3034 at 100%, 0 off |
| 0x02C1 | 0 | u8 | Stop flag | 1 = off, 0 = release |
| 0x0191 | 0 | u32 | Feed select | 1 = feed, 0 = schedule |
| 0x0190 | 0..29 | 33 B | Named modes | see below |
| 0x0197 | 0 | 37 B | Timed override entry | see below |
| 0x03ED | 0 | 16 B | Read at connect | constant per device |
| 0x02C3 | 0 | u16 | Unknown, polled by app | 0 |
| 0x02C4 | 0 | u16 | Unknown, polled by app | 0 |

The app polls `c3020001 c4020001 65000b01 bc020001` about five times a second while the pump screen is open.

### 0x0190 named modes

Slot 0 is Feed Mode: `[u16 ?=1][u16 duration s][16 B name, NUL-padded][u8 ?=0x0d][u16 LE flow, 0.1%]...`. Example: `0100 5802 "Feed Mode"... 0d f401` = 600 s at 50.0%. Changing the Feed Mode speed in the app changes the flow field.

### 0x0197 timed override

37-byte value: `[u8 ?][3 B 0][u8 1][u8 0][u32 LE duration s][...0][u8 1][u16 LE flow, 0.1%][...0]`. Duration at offset 6, flow at offset 25. The app writes three entries (leading byte `02`, `07`, `08`; meaning unknown); reading index 0 returns the last one written. Schedule clears it.

## Commands

All opcode `18`, flags `0400`.

| Command | Payload |
|---|---|
| Off | `c10200010101` |
| Schedule | `c10200010100` `910100010400000000` |
| Feed | `c10200010100` `910100010401000000` |
| Full flow 1 h | `c10200010100` + 3 × `9701000125` `{02,07,08}` `0000000100100e0000000000000000000000000000000001e80300000000000000000000` |

Off stays off until Schedule. Feed runs at the Feed Mode flow (`0x0190` slot 0), not necessarily 0.

## Open questions

1. Is the `0x03ED` read required before commands?
2. Does the advertisement change with device state? If yes, state could be read without connecting.
3. Meaning of `0x02C3`, `0x02C4`, the 5551 indication, and the leading byte of each `0x0197` entry.
