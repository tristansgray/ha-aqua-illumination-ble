# Contributing

Thanks for helping! This is a small hobby project, so replies may take a few days.

## Ways to help

- **Request a device**: [open a device request](https://github.com/tristansgray/ha-aqua-illumination-ble/issues/new?template=device_request.yml). [docs/adding-devices.md](docs/adding-devices.md) explains how to capture what the myAI app sends. No coding needed.
- **Report a bug**: [open a bug report](https://github.com/tristansgray/ha-aqua-illumination-ble/issues/new?template=bug_report.yml) with debug logs.
- **Test a change on your hardware**: when someone works on your device, trying their test build is the most valuable help there is.
- **Code**: fixes, new devices, better docs. Read on.

## Safety first

This integration controls equipment keeping animals alive. Any change that **writes** to a device must:

1. Replay a frame captured from the myAI app **byte for byte**, or explain every field that differs from the capture.
2. Be tested on real hardware by someone who owns the device, ending with the device back in normal operation.
3. Never write an attribute that wasn't seen in a capture.

A device's model and firmware go into `TESTED` (in `custom_components/aqua_illumination_ble/__init__.py`) only after **every** entity has been checked on that hardware. Until then it stays behind the "untested device" confirmation.

## Development setup

You need [uv](https://docs.astral.sh/uv/) and, for hassfest, Docker.

```
git clone https://github.com/tristansgray/ha-aqua-illumination-ble
cd ha-aqua-illumination-ble

# Protocol self-check (offline)
uv run tools/axis.py selftest

# Config flow tests
uv run --no-project --python 3.14 \
  --with pytest-homeassistant-custom-component,bleak,bleak-retry-connector,bluetooth-adapters,bluetooth-auto-recovery,bluetooth-data-tools,dbus-fast,habluetooth,aiousbwatcher,serialx,aiohasupervisor \
  python -m pytest tests -q -o asyncio_mode=auto

# Home Assistant's integration validator
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest
```

These are the same checks CI runs on every push and pull request.

To try a change in Home Assistant, copy `custom_components/aqua_illumination_ble` into your HA `config/custom_components/` and restart.

## Code layout

| Path | What it is |
|---|---|
| `custom_components/aqua_illumination_ble/protocol.py` | Frame building and parsing, commands, BLE session. **No Home Assistant imports**, so the CLI can share it. |
| `custom_components/aqua_illumination_ble/__init__.py` | Coordinator (connect, read, disconnect every 60 s), device check, base entity |
| `custom_components/aqua_illumination_ble/config_flow.py` | Discovery and setup, including the untested-device confirmation |
| `sensor.py`, `button.py` | Entities |
| `tools/axis.py` | CLI for testing against hardware |
| `tools/snoop.py` | Decodes myAI commands from Android Bluetooth captures |
| `docs/PROTOCOL.md` | Everything known about the protocol. Update it with every new attribute. |

Keep code in the style of what's around it: small, plain, no new dependencies unless unavoidable.

## Pull requests

- One change per pull request, linked to its issue.
- CI must pass.
- Fill in the template, including what hardware you tested on.
- Never commit raw captures, serial numbers or Bluetooth addresses.

## Releases (maintainers)

HACS installs from GitHub releases, and the default store requires each release to come **after** the checks pass:

1. Bump `version` in `custom_components/aqua_illumination_ble/manifest.json` ([semver](https://semver.org): patch for fixes, minor for new devices/features).
2. Push to `main` and wait for every CI job to pass.
3. Publish a GitHub release `vX.Y.Z` targeting that commit, with notes covering what changed and any upgrade steps.

**Never change the integration domain** (`aqua_illumination_ble`). It breaks every existing install.

## Code of conduct

Be kind and assume good intent. Most people here are reef keepers first and programmers second.
