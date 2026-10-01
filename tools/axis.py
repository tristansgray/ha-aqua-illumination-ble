# /// script
# requires-python = ">=3.11"
# dependencies = ["bleak"]
# ///
"""Aqua Illumination Mobius BLE client (pump commands verified on Axis 40). See docs/PROTOCOL.md.

uv run tools/axis.py selftest   # offline frame/CRC checks
uv run tools/axis.py state      # connect, print device info + flow/RPM
uv run tools/axis.py read 0190:0 # read attrs (hex attr:index)
uv run tools/axis.py feed|off|timed  # send command, check, then always Schedule
"""
import asyncio
import logging
import struct
import sys
from pathlib import Path

from bleak import BleakClient, BleakScanner

# import the protocol module directly; the package __init__ needs Home Assistant
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "aqua_illumination"))
from protocol import *  # noqa: E402,F403

# name -> (payload, pass check(flow, rpm, rpm_before))
TRIALS = {
    # feed speed is the 0x0190 slot 0 setting, not necessarily 0
    "feed": (FEED, lambda f, r, b: r < b),
    "off": (OFF, lambda f, r, b: f == 0),
    "timed": (TIMED, lambda f, r, b: f == 1000 and r > 0),
}


async def show(axis: Axis) -> tuple[int, int]:
    flow, rpm = await axis.state()
    print(f"  flow={flow / 10:.1f}%  rpm={rpm}")
    return flow, rpm


async def connect() -> BleakClient:
    dev = await BleakScanner.find_device_by_filter(
        lambda d, adv: d.name == "MOBIUS" or SERVICE in adv.service_uuids, timeout=15
    )
    if not dev:
        sys.exit("MOBIUS not found (is the myAI app closed on every phone?)")
    print(f"found {dev.name} {dev.address}")
    return BleakClient(dev)


async def main(cmd: str, args: list[str]):
    async with await connect() as client:
        print(f"  mtu={client.mtu_size}")
        for k, u in DEV_INFO.items():
            print(f"  {k}: {(await client.read_gatt_char(u)).decode(errors='replace')}")
        axis = Axis(client)
        await axis.start()
        if cmd == "read":  # e.g. read 0190:0 0197:0; generic, works on non-pump devices
            keys = [tuple(int(x, 16) for x in a.split(":")) for a in args]
            for (a, i), v in (await axis.read(*keys)).items():
                print(f"  {a:#06x}[{i}] ({len(v)} B): {v.hex()}")
            return
        _, before = await show(axis)
        if cmd not in TRIALS:
            return
        payload, ok = TRIALS[cmd]
        assert before > 0, "pump not running before test; aborting"
        if cmd == "timed":
            print(f"  0x0197: {(await axis.read(OVERRIDE))[OVERRIDE].hex()}")
        try:
            print(cmd.upper())
            await axis.write(payload)
            await asyncio.sleep(5)
            flow, rpm = await show(axis)
            print(f"  {cmd}", "PASS" if ok(flow, rpm, before) else "FAIL")
            if cmd == "timed":
                print(f"  0x0197: {(await axis.read(OVERRIDE))[OVERRIDE].hex()}")
        finally:  # safety rule 1: never leave the pump in Off/Feed/override
            print("SCHEDULE")
            await axis.write(SCHEDULE)
            await asyncio.sleep(10)
            flow, rpm = await show(axis)
            # flow depends on the schedule's current point; eyeball it against the app
            print("  schedule", "PASS" if flow > 0 and rpm > 0 else "FAIL")
            if cmd == "timed":
                print(f"  0x0197: {(await axis.read(OVERRIDE))[OVERRIDE].hex()}")


def selftest():
    assert build(OP_READ, 0x20, read_req(ID)).hex() == "02de17200000000400ed030001ef63"
    assert FEED.hex() == "c10200010100" "9101000104" "01000000"
    assert OFF.hex() == "c10200010101"
    assert len(TIMED) == 6 + 3 * 42 and TIMED[6 + 4] == 37  # each entry: 5 B header + VLEN 37
    assert SCHEDULE.hex() == "c10200010100" "9101000104" "00000000"
    reply = bytes.fromhex("00" "bc020001" "02" "6400")  # status OK, flow=100
    body = struct.pack("<BBBBHH", 0xDF, 0x17, 0x21, 0, 0, len(reply)) + reply
    op, seq, pay = parse(b"\x02" + body + struct.pack("<H", crc(body)))
    assert (op, seq) == (0x17, 0x21) and parse_read(pay) == {FLOW: b"\x64\x00"}
    print("selftest ok")


if __name__ == "__main__":
    logging.basicConfig(format="  %(message)s")
    logging.getLogger("protocol").setLevel(logging.DEBUG)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    selftest() if cmd == "selftest" else asyncio.run(main(cmd, sys.argv[2:]))
