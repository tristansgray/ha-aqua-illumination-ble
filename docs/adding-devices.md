# Adding support for another AI device

Every Aqua Illumination device seen so far uses the same Mobius framing ([PROTOCOL.md](PROTOCOL.md)), so adding a device is mostly a matter of finding its attributes. You capture what the myAI app sends, decode it, and replay it carefully.

## 1. Capture the myAI app (Android)

1. Enable **Developer options** (Settings → About phone → tap *Build number* 7 times).
2. Developer options → **Enable Bluetooth HCI snoop log** → *Enabled*. Turn Bluetooth off and on.
3. Open myAI and perform each action you want to support, **one at a time, about 10 s apart**. Write down the order (e.g. "21:45 off, then schedule, then feed").
4. Get the log: `adb bugreport bugreport.zip`, unzip, and find `FS/data/misc/bluetooth/logs/btsnoop_hci.log` (some phones put it elsewhere; search for `btsnoop`).
5. Turn the snoop log back off.

iOS can capture Bluetooth via a sysdiagnose with Apple's Bluetooth logging profile, but it is much more work. Android is recommended.

**Before sharing a capture**, remember it contains your device's Bluetooth address and serial number.

## 2. Decode it

```
python3 tools/snoop.py btsnoop_hci.log            # writes only
python3 tools/snoop.py btsnoop_hci.log --reads    # include the app's status polls
```

Each line is one app→device frame with its UTC time and decoded `attr[index]=value` entries. Match the times against your notes. The app's status poll (`--reads`) shows which attributes it reads for the screen you had open; those are your sensor candidates.

## 3. Test from a computer, safely

`tools/axis.py` talks to a device directly (needs [uv](https://docs.astral.sh/uv/); macOS/Linux/Windows):

```
uv run tools/axis.py state           # device info + Axis flow/RPM
uv run tools/axis.py read 02bc:0     # read any attribute (hex attr:index)
```

Rules that kept a live reef tank safe while the Axis 40 was reverse-engineered:

1. **Force-close myAI on every phone** first. The device takes one client at a time.
2. **Read before you write.** Confirm the attributes you plan to write exist and hold the values you expect.
3. **Write only what you captured**, byte for byte. Change one field at a time, and only after the exact replay works.
4. **Always restore normal operation** after each test (for pumps: Schedule), then read back to confirm.
5. **Check lengths:** each write entry's `VLEN` byte must equal its value length. A mistyped hex string can turn into a write to a different attribute.

## 4. Add it to the integration

Open an issue or pull request with the decoded frames (not the raw log), your device's model string and firmware as shown by `tools/axis.py state`, and what you tested. Supported model/firmware pairs live in `TESTED` in `custom_components/aqua_illumination/__init__.py`.
