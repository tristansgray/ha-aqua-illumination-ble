# Aqua Illumination for Home Assistant

Local Bluetooth control of Aqua Illumination (AI) aquarium devices. No cloud and no myAI app required.

> Not affiliated with or endorsed by Aqua Illumination or EcoTech Marine. The protocol was reverse-engineered from Bluetooth captures of the myAI app. This integration controls equipment on a live tank, so use it at your own risk.

## Supported devices

| Device | Firmware | Status |
|---|---|---|
| Axis 40 pump | 2.3.15 | Tested: sensors and all buttons |

Other devices that advertise as `MOBIUS` are discovered, but setup warns that they are untested and requires you to confirm. Want your device supported? See [docs/adding-devices.md](docs/adding-devices.md).

## Features (Axis 40)

- **Sensors:** Flow (%), Speed (rpm), polled every 60 s
- **Buttons:** Resume schedule, Feed, Full flow 1 hour, Off

**Off stays off** until you press Resume schedule. Consider an automation that resumes the schedule after a timeout. Feed runs at the Feed Mode speed set in the myAI app.

## Requirements

- A Bluetooth adapter or [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy) in range of the device
- The myAI app closed: the device accepts one Bluetooth client at a time and stops advertising while the app is connected. Home Assistant connects for a few seconds each poll, so the app can still connect between polls, and the sensors show unavailable while the app is open.

## Install

### HACS

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/tristansgray/ha-aqua-illumination` as an **Integration**.
2. Install **Aqua Illumination** and restart Home Assistant.
3. Your device should be discovered automatically. If it isn't, go to Settings → Devices & services → Add integration → **Aqua Illumination**.

### Manual

Copy `custom_components/aqua_illumination` into your `config/custom_components/` folder and restart.

## Tools

- `tools/axis.py`: command-line client for testing from a computer (`uv run tools/axis.py state`)
- `tools/snoop.py`: decodes myAI app commands from an Android Bluetooth capture

Protocol notes: [docs/PROTOCOL.md](docs/PROTOCOL.md).

## License

MIT
