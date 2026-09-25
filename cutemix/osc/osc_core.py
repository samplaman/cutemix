"""
Pure-Python OSC 1.0 Encoder and Decoder.
Zero external dependencies. Fully compliant with Open Sound Control 1.0 specification.
Supports:
  - Types: i (int32), f (float32), s (string), b (blob), T (True), F (False), d (double), h (int64)
  - Messages and Bundles (#bundle)
  - 4-byte boundary padding
"""

import struct
import time
from typing import Any, List, Tuple, Union


class OscDecodeError(ValueError):
    pass


class OscEncodeError(ValueError):
    pass


def _pad4(length: int) -> int:
    """Returns number of null padding bytes needed to align to 4 bytes."""
    rem = length % 4
    return (4 - rem) if rem != 0 else 0


def encode_string(s: str) -> bytes:
    """Encodes a string as null-terminated and padded to 4-byte boundary."""
    data = s.encode("utf-8") + b"\x00"
    pad = _pad4(len(data))
    return data + (b"\x00" * pad)


def decode_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """Decodes a null-terminated, 4-byte padded string from data at offset."""
    null_idx = data.find(b"\x00", offset)
    if null_idx == -1:
        raise OscDecodeError("String not null-terminated")
    raw_str = data[offset:null_idx]
    s = raw_str.decode("utf-8", errors="replace")
    next_offset = null_idx + 1
    next_offset += _pad4(next_offset - offset)
    return s, next_offset


def encode_blob(b: bytes) -> bytes:
    """Encodes a binary blob with 32-bit length prefix and 4-byte padding."""
    length = len(b)
    data = struct.pack(">i", length) + b
    pad = _pad4(len(data))
    return data + (b"\x00" * pad)


def decode_blob(data: bytes, offset: int = 0) -> Tuple[bytes, int]:
    """Decodes a 32-bit length-prefixed blob at offset."""
    if offset + 4 > len(data):
        raise OscDecodeError("Not enough data for blob length")
    length = struct.unpack(">i", data[offset:offset + 4])[0]
    offset += 4
    if offset + length > len(data):
        raise OscDecodeError(f"Blob claims length {length} but only {len(data) - offset} bytes remain")
    blob = data[offset:offset + length]
    next_offset = offset + length
    pad = _pad4(length)
    return blob, next_offset + pad


class OscMessage:
    """Represents an OSC message with address and arguments."""

    def __init__(self, address: str, args: Union[List[Any], Tuple[Any, ...]] = None):
        if not address.startswith("/"):
            raise OscEncodeError(f"OSC address must start with '/', got: {address}")
        self.address = address
        self.args = list(args) if args is not None else []

    def encode(self) -> bytes:
        """Serializes message to OSC 1.0 byte format."""
        addr_bytes = encode_string(self.address)
        type_tags = [","]
        args_payload = bytearray()

        for arg in self.args:
            if isinstance(arg, bool):
                type_tags.append("T" if arg else "F")
            elif isinstance(arg, int):
                if -2147483648 <= arg <= 2147483647:
                    type_tags.append("i")
                    args_payload.extend(struct.pack(">i", arg))
                else:
                    type_tags.append("h")
                    args_payload.extend(struct.pack(">q", arg))
            elif isinstance(arg, float):
                type_tags.append("f")
                args_payload.extend(struct.pack(">f", arg))
            elif isinstance(arg, str):
                type_tags.append("s")
                args_payload.extend(encode_string(arg))
            elif isinstance(arg, (bytes, bytearray)):
                type_tags.append("b")
                args_payload.extend(encode_blob(bytes(arg)))
            else:
                # Default fallback: cast to string
                s = str(arg)
                type_tags.append("s")
                args_payload.extend(encode_string(s))

        tags_bytes = encode_string("".join(type_tags))
        return addr_bytes + tags_bytes + bytes(args_payload)

    @classmethod
    def decode(cls, data: bytes) -> "OscMessage":
        """Deserializes bytes into an OscMessage."""
        if not data.startswith(b"/"):
            raise OscDecodeError("OSC message must start with '/'")
        address, offset = decode_string(data, 0)
        args = []

        if offset < len(data) and data[offset:offset + 1] == b",":
            type_tags, offset = decode_string(data, offset)
            for tag in type_tags[1:]:  # skip initial comma
                if tag == "i":
                    if offset + 4 > len(data):
                        raise OscDecodeError("Truncated int32")
                    val = struct.unpack(">i", data[offset:offset + 4])[0]
                    args.append(val)
                    offset += 4
                elif tag == "f":
                    if offset + 4 > len(data):
                        raise OscDecodeError("Truncated float32")
                    val = struct.unpack(">f", data[offset:offset + 4])[0]
                    args.append(val)
                    offset += 4
                elif tag == "s":
                    val, offset = decode_string(data, offset)
                    args.append(val)
                elif tag == "b":
                    val, offset = decode_blob(data, offset)
                    args.append(val)
                elif tag == "T":
                    args.append(True)
                elif tag == "F":
                    args.append(False)
                elif tag == "d":
                    if offset + 8 > len(data):
                        raise OscDecodeError("Truncated double")
                    val = struct.unpack(">d", data[offset:offset + 8])[0]
                    args.append(val)
                    offset += 8
                elif tag == "h":
                    if offset + 8 > len(data):
                        raise OscDecodeError("Truncated int64")
                    val = struct.unpack(">q", data[offset:offset + 8])[0]
                    args.append(val)
                    offset += 8
                else:
                    # Unsupported/ignored type tag
                    pass

        return cls(address, args)

    def __repr__(self) -> str:
        return f"OscMessage(address='{self.address}', args={self.args})"


class OscBundle:
    """Represents an OSC bundle containing messages or nested bundles."""

    def __init__(self, timetag: float = 1.0, elements: List[Union[OscMessage, "OscBundle"]] = None):
        self.timetag = timetag
        self.elements = elements if elements is not None else []

    def encode(self) -> bytes:
        head = encode_string("#bundle")
        # 64-bit NTP timestamp or 1 for immediate execution
        if self.timetag == 1.0:
            tt_bytes = struct.pack(">Q", 1)
        else:
            # Convert Unix time to NTP timestamp
            ntp_time = self.timetag + 2208988800.0
            sec = int(ntp_time)
            frac = int((ntp_time - sec) * (1 << 32))
            tt_bytes = struct.pack(">II", sec, frac)

        elem_bytes = bytearray()
        for elem in self.elements:
            encoded_elem = elem.encode()
            elem_bytes.extend(struct.pack(">i", len(encoded_elem)))
            elem_bytes.extend(encoded_elem)

        return head + tt_bytes + bytes(elem_bytes)

    @classmethod
    def decode(cls, data: bytes) -> "OscBundle":
        if not data.startswith(b"#bundle\x00"):
            raise OscDecodeError("Not an OSC bundle")
        offset = 8  # length of '#bundle\0'
        if offset + 8 > len(data):
            raise OscDecodeError("Bundle truncated at timetag")
        tt_raw = struct.unpack(">Q", data[offset:offset + 8])[0]
        offset += 8
        timetag = 1.0 if tt_raw == 1 else float(tt_raw >> 32)  # Simplified NTP seconds

        elements = []
        while offset < len(data):
            if offset + 4 > len(data):
                break
            size = struct.unpack(">i", data[offset:offset + 4])[0]
            offset += 4
            if offset + size > len(data):
                raise OscDecodeError("Bundle element size exceeds packet length")
            elem_data = data[offset:offset + size]
            offset += size
            if elem_data.startswith(b"#bundle"):
                elements.append(OscBundle.decode(elem_data))
            else:
                elements.append(OscMessage.decode(elem_data))

        return cls(timetag, elements)

    def __repr__(self) -> str:
        return f"OscBundle(timetag={self.timetag}, elements={self.elements})"


def decode_packet(data: bytes) -> Union[OscMessage, OscBundle]:
    """Decodes raw UDP packet bytes into either an OscMessage or OscBundle."""
    if data.startswith(b"#bundle"):
        return OscBundle.decode(data)
    elif data.startswith(b"/"):
        return OscMessage.decode(data)
    else:
        raise OscDecodeError("Packet is neither an OSC message nor a bundle")
