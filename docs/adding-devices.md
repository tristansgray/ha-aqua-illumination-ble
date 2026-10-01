# Adding support for another AI device

Every Aqua Illumination device seen so far speaks the same Mobius Bluetooth framing ([PROTOCOL.md](PROTOCOL.md)). Adding a device means finding which attributes it uses, and the way to find them is to record what the myAI app sends.

You don't need to write any code. There are two routes:

- **[Just ask](#route-1-just-ask)**: open a request with what you know. Fine even if you can't make a capture.
- **[Capture it yourself](#route-2-capture-the-myai-app)**: about 15 minutes with an Android phone, and it makes support far more likely.

## Route 1: just ask

[Open a device request](https://github.com/tristansgray/ha-aqua-illumination-ble/issues/new?template=device_request.yml). The form asks for:

1. **Which device**, as sold (e.g. "Nero 5", "Prime 16HD").
2. **Model and firmware as the device reports them over Bluetooth.** The easiest way to get these is to add the device in Home Assistant. It will be flagged as untested; accept, then open Settings → Devices & services → Aqua Illumination (Bluetooth) → your device. The model and firmware are shown there. Nothing is sent to the device until you press a button.
3. **What you want Home Assistant to do**, e.g. "show current intensity" or "switch to acclimation mode".
4. **A capture, if you can make one** (route 2). If you can't, say so; a request without one still helps show which devices people want.

## Route 2: capture the myAI app

### What you need

- An Android phone with myAI installed and paired to the device. iPhones can capture Bluetooth through a sysdiagnose with Apple's Bluetooth logging profile, but it's much more work; ask in your request if that's all you have.
- About 15 minutes, and the device somewhere you can safely change modes. It's running a live tank.

### Record

1. Enable **Developer options**: Settings → About phone → tap **Build number** seven times.
2. Settings → System → Developer options → **Enable Bluetooth HCI snoop log** → **Enabled**.
3. **Turn Bluetooth off and on.** Logging starts only after a restart of Bluetooth.
4. Open myAI and do each action you want supported **one at a time, about 10 seconds apart**. Write each one down with the time as you go:

   ```
   time zone: EDT
   21:44  opened myAI, connected to the pump
   21:45  Off
   21:46  Resume schedule
   21:47  Feed
   21:48  changed Feed Mode speed 50% -> 30%
   ```

   Tips for a capture that's easy to decode:
   - Include **opening the device's screen** in the app. Its status polls show which values to turn into sensors.
   - For sliders, set a **few distinctive values** (e.g. 10%, 50%, 100%) and note each one.
   - Return the device to normal operation at the end.
5. Developer options → **Take bug report** → **Full report**. When it's ready (a few minutes), share the zip to your computer.
6. Turn **Enable Bluetooth HCI snoop log** back off.

In the zip, the log is usually `FS/data/misc/bluetooth/logs/btsnoop_hci.log`. Some phones put it elsewhere, so search the zip for `btsnoop`. With a computer and `adb`, `adb bugreport bugreport.zip` produces the same zip.

### Decode (optional, but please try)

With Python 3 on your computer and a copy of this repository:

```
python3 tools/snoop.py btsnoop_hci.log
```

Each line is one command the app sent, with its UTC time and decoded `attr[index]=value` entries:

```
01:45:47.281 op=18 seq=10 crc=ok 0x02c1[0]=00 0x0191[0]=01000000
```

Add `--reads` to include the app's status polls. Match the times against your notes (the decoder prints UTC; your notes are local time).

### Privacy

- **Decoded output** contains only the commands and values: no addresses, no serial number. Paste it into the request.
- **The raw `btsnoop_hci.log`** contains your phone's and device's Bluetooth addresses and the device's serial number, and may include traffic from other Bluetooth devices (headphones, watches). Only attach it if the decoded output isn't enough and you're comfortable with that. Never attach the whole bug report zip: it contains far more than Bluetooth.

## Testing from a computer

If you want to go further, `tools/axis.py` talks to a device directly (needs [uv](https://docs.astral.sh/uv/); runs on macOS, Linux and Windows):

```
uv run tools/axis.py state           # device info, then Axis flow/RPM
uv run tools/axis.py read 02bc:0     # read any attribute (hex attr:index)
```

On a device that isn't an Axis, `state` prints the device info and then fails on the pump-specific reads. That's expected.

Rules that kept a live reef tank safe while the Axis 40 was reverse-engineered:

1. **Force-close myAI on every phone** first. The device takes one client at a time.
2. **Read before you write.** Confirm the attributes you plan to write exist and hold the values you expect.
3. **Write only what you captured**, byte for byte. Change one field at a time, and only after the exact replay works.
4. **Always restore normal operation** after each test (for pumps: Schedule), then read back to confirm.
5. **Check lengths:** each write entry's `VLEN` byte must equal its value length. A mistyped hex string can turn into a write to a different attribute.

## What happens next

A maintainer decodes the capture, works out the attributes, and posts proposed commands in the issue. You'll be asked to try them from a test build, since only you have the device. Once every command is confirmed on your hardware, its model and firmware go into the tested list and it ships in the next release. See [CONTRIBUTING.md](../CONTRIBUTING.md) if you'd like to make the code change yourself.
