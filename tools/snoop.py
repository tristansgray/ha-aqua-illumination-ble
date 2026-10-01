"""Dump myAI app -> device Mobius frames from Android btsnoop (H4) logs.

python3 tools/snoop.py btsnoop_hci.log [--reads]

Prints each frame with UTC time, opcode, seq, CRC check, and decoded write entries.
Status polls (opcode 17, reads) are hidden unless --reads is given.
"""
import binascii
import datetime as dt
import struct
import sys

EPOCH_DELTA = 0x00DCDDB30F2F8000  # btsnoop us since 0 AD -> unix us


def records(path):
    with open(path, "rb") as f:
        if f.read(16)[:8] != b"btsnoop\0":
            sys.exit(f"{path}: not a btsnoop file")
        while hdr := f.read(24):
            _, incl, flags, _, ts = struct.unpack(">IIIIq", hdr)
            yield ts, flags, f.read(incl)


def att_pdus(path):
    """Reassemble ACL -> L2CAP; yield (ts, sent_by_phone, att_pdu) for the ATT channel."""
    bufs = {}
    for ts, flags, pkt in records(path):
        if not pkt or pkt[0] != 0x02:  # H4 ACL
            continue
        hf, n = struct.unpack_from("<HH", pkt, 1)
        h, pb, data = hf & 0x0FFF, (hf >> 12) & 3, pkt[5 : 5 + n]
        key = (h, flags & 1)
        bufs[key] = (bufs.get(key, b"") + data) if pb == 1 else data
        b = bufs[key]
        if len(b) >= 4 and len(b) - 4 >= struct.unpack_from("<H", b)[0]:
            ln, cid = struct.unpack_from("<HH", b)
            if cid == 4:
                yield ts, not (flags & 1), b[4 : 4 + ln]
            bufs[key] = b""


def entries(payload: bytes):
    """Decode write payload: repeat [ATTR u16][INDEX u8][COUNT u8][VLEN u8][VALUE]."""
    i = 0
    while i + 5 <= len(payload):
        attr, idx, _, vlen = struct.unpack_from("<HBBB", payload, i)
        yield f"{attr:#06x}[{idx}]={payload[i + 5 : i + 5 + vlen].hex()}"
        i += 5 + vlen


def main(paths, reads):
    for path in paths:
        print(f"== {path}")
        for ts, sent, pdu in att_pdus(path):
            # ATT write command (0x52) / write request (0x12) carrying a Mobius app->device frame
            if not (sent and pdu[0] in (0x52, 0x12) and pdu[3:5] == b"\x02\xde"):
                continue
            fr = pdu[3:]
            if fr[2] == 0x17 and not reads:
                continue
            t = dt.datetime.fromtimestamp((ts - EPOCH_DELTA) / 1e6, dt.UTC).strftime("%H:%M:%S.%f")[:-3]
            ok = struct.unpack_from("<H", fr, len(fr) - 2)[0] == binascii.crc_hqx(fr[1:-2], 0xFFFF)
            payload = fr[9:-2]
            body = " ".join(entries(payload)) if fr[2] == 0x18 else payload.hex()
            print(f"{t} op={fr[2]:02x} seq={fr[3]:02x} crc={'ok' if ok else 'BAD'} {body}")


if __name__ == "__main__":
    args = sys.argv[1:]
    main([a for a in args if a != "--reads"], "--reads" in args)
