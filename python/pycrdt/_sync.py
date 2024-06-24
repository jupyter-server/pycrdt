from __future__ import annotations

from enum import IntEnum

from pycrdt import Doc


class YMessageType(IntEnum):
    SYNC = 0
    AWARENESS = 1


class YSyncMessageType(IntEnum):
    SYNC_STEP1 = 0
    SYNC_STEP2 = 1
    SYNC_UPDATE = 2


def write_var_uint(num: int) -> bytes:
    res = []
    while num > 127:
        res.append(128 | (127 & num))
        num >>= 7
    res.append(num)
    return bytes(res)


def create_message(data: bytes, msg_type: int) -> bytes:
    return bytes([YMessageType.SYNC, msg_type]) + write_var_uint(len(data)) + data


def create_sync_step1_message(data: bytes) -> bytes:
    return create_message(data, YSyncMessageType.SYNC_STEP1)


def create_sync_step2_message(data: bytes) -> bytes:
    return create_message(data, YSyncMessageType.SYNC_STEP2)


def create_update_message(data: bytes) -> bytes:
    return create_message(data, YSyncMessageType.SYNC_UPDATE)


class Decoder:
    def __init__(self, stream: bytes):
        self.stream = stream
        self.length = len(stream)
        self.i0 = 0

    def read_var_uint(self) -> int:
        if self.length <= 0:
            raise RuntimeError("Y protocol error")
        uint = 0
        i = 0
        while True:
            byte = self.stream[self.i0]
            uint += (byte & 127) << i
            i += 7
            self.i0 += 1
            self.length -= 1
            if byte < 128:
                break
        return uint

    def read_message(self) -> bytes | None:
        if self.length == 0:
            return None
        length = self.read_var_uint()
        if length == 0:
            return b""
        i1 = self.i0 + length
        message = self.stream[self.i0 : i1]
        self.i0 = i1
        self.length -= length
        return message

    def read_messages(self):
        while True:
            message = self.read_message()
            if message is None:
                return
            yield message

    def read_var_string(self):
        message = self.read_message()
        if message is None:
            return ""
        return message.decode("utf-8")


def read_message(stream: bytes) -> bytes:
    message = Decoder(stream).read_message()
    assert message is not None
    return message


def handle_sync_message(message: bytes, ydoc: Doc) -> bytes | None:
    message_type = message[0]
    msg = message[1:]

    if message_type == YSyncMessageType.SYNC_STEP1:
        state = read_message(msg)
        update = ydoc.get_update(state)
        reply = create_sync_step2_message(update)
        return reply

    if message_type in (
        YSyncMessageType.SYNC_STEP2,
        YSyncMessageType.SYNC_UPDATE,
    ):
        update = read_message(msg)
        # Ignore empty updates
        if update != b"\x00\x00":
            ydoc.apply_update(update)

    return None


def create_sync_message(ydoc: Doc) -> bytes:
    state = ydoc.get_state()
    message = create_sync_step1_message(state)
    return message
