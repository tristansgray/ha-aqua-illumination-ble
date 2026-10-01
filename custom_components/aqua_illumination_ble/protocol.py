"""AI Axis 40 (Mobius BLE) wire protocol. No Home Assistant imports; axis.py CLI uses it too.

See docs/PROTOCOL.md for the frame format and attribute map.
"""
import asyncio
import binascii
import logging
import struct

from bleak import BleakClient

_LOGGER = logging.getLogger(__name__)

BASE = "01ff{}-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
SERVICE = BASE.format("0100")
RX_PART, RX_LAST, TX, IND = (BASE.format(c) for c in ("0101", "0102", "0104", "5551"))
DEV_INFO = {"manufacturer": "2a29", "model": "2a24", "firmware": "2a26", "serial": "2a25"}

OP_READ, OP_WRITE = 0x17, 0x18
FLOW, RPM, ID = (0x02BC, 0), (0x0065, 11), (0x03ED, 0)
STOP_REL = struct.pack("<HBBB", 0x02C1, 0, 1, 1) + b"\x00"
SCHEDULE = STOP_REL + struct.pack("<HBBBI", 0x0191, 0, 1, 4, 0)
FEED = STOP_REL + struct.pack("<HBBBI", 0x0191, 0, 1, 4, 1)
OFF = struct.pack("<HBBB", 0x02C1, 0, 1, 1) + b"\x01"
# Verbatim replay from btsnoop capture 2026-09-29 01:45:41Z: 37 B value, duration u32 LE at +6
# (100e0000 = 3600 s), flow u16 LE at +25 (e803 = 100.0%). Leading byte 02/07/08 unknown.
_ENTRY = "9701000125{}0000000100100e0000000000000000000000000000000001e80300000000000000000000"
TIMED = STOP_REL + bytes.fromhex("".join(_ENTRY.format(b) for b in ("02", "07", "08")))
OVERRIDE = (0x0197, 0)


def crc(b: bytes) -> int:
    return binascii.crc_hqx(b, 0xFFFF)  # CRC-16/CCITT-FALSE


def build(op: int, seq: int, payload: bytes) -> bytes:
    flags = 0x0004 if op == OP_WRITE else 0
    body = struct.pack("<BBBBHH", 0xDE, op, seq, 0, flags, len(payload)) + payload
    return b"\x02" + body + struct.pack("<H", crc(body))


def parse(frame: bytes) -> tuple[int, int, bytes]:
    """-> (op, seq, payload). Raises on bad framing/CRC."""
    if frame[0] != 0x02 or frame[1] != 0xDF:
        raise ValueError(f"bad header {frame.hex()}")
    _, op, seq, _, _, n = struct.unpack_from("<BBBBHH", frame, 1)
    payload = frame[9 : 9 + n]
    if len(payload) != n or struct.unpack_from("<H", frame, 9 + n)[0] != crc(frame[1 : 9 + n]):
        raise ValueError(f"bad length/CRC {frame.hex()}")
    return op, seq, payload


def parse_read(payload: bytes) -> dict[tuple[int, int], bytes]:
    if payload[0] != 0:
        raise ValueError(f"read status {payload[0]:#x}")
    out, i = {}, 1
    while i < len(payload):
        attr, idx, _count, vlen = struct.unpack_from("<HBBB", payload, i)
        out[(attr, idx)] = payload[i + 5 : i + 5 + vlen]
        i += 5 + vlen
    return out


def read_req(*keys: tuple[int, int]) -> bytes:
    return b"".join(struct.pack("<HBB", a, i, 1) for a, i in keys)


class Axis:
    def __init__(self, client: BleakClient):
        self.c, self.seq, self.buf = client, 0x20, b""
        self.replies: asyncio.Queue[bytes] = asyncio.Queue()

    async def start(self):
        await self.c.start_notify(RX_PART, lambda _, d: self._rx(d, False))
        await self.c.start_notify(RX_LAST, lambda _, d: self._rx(d, True))
        await self.c.start_notify(IND, lambda _, d: _LOGGER.debug("5551 indication: %s", d.hex()))
        # ponytail: open question whether this read is required; the app always does it
        _LOGGER.debug("0x03ED: %s", (await self.read(ID))[ID].hex())

    def _rx(self, data: bytes, last: bool):
        self.buf += data
        if last:
            self.replies.put_nowait(self.buf)
            self.buf = b""

    async def _req(self, op: int, payload: bytes) -> bytes:
        self.seq = (self.seq + 1) & 0xFF
        await self.c.write_gatt_char(TX, build(op, self.seq, payload), response=False)
        while True:
            rop, rseq, rpay = parse(await asyncio.wait_for(self.replies.get(), 5))
            if (rop, rseq) == (op, self.seq):
                return rpay
            _LOGGER.debug("skipping stray reply op=%#x seq=%#x", rop, rseq)

    async def read(self, *keys):
        return parse_read(await self._req(OP_READ, read_req(*keys)))

    async def write(self, payload: bytes):
        r = await self._req(OP_WRITE, payload)
        if r != b"\x00\xff\xff":
            raise RuntimeError(f"write rejected: {r.hex()}")

    async def state(self) -> tuple[int, int]:
        """-> (flow in 0.1% steps, rpm)."""
        r = await self.read(FLOW, RPM)
        return struct.unpack("<H", r[FLOW])[0], struct.unpack("<I", r[RPM])[0]
