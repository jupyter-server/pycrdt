from __future__ import annotations

from enum import IntEnum
from typing import Iterator

from pycrdt import Doc


class YMessageType(IntEnum):
    """
    A generic Y message type.

    Attributes:
        SYNC: A message type used for synchronizing documents.
        AWARENESS: A message type used for the awareness protocol.
    """

    SYNC: int = 0
    AWARENESS: int = 1


class YSyncMessageType(IntEnum):
    """
    A message type used for synchronizing documents.

    Attributes:
        SYNC_STEP1: A synchronization message type used to send a document state.
        SYNC_STEP2: A synchronization message type used to reply to a
            [SYNC_STEP1][pycrdt.YSyncMessageType], consisting of all missing updates and all
            deletions.
        SYNC_UPDATE: A synchronization message type used to send document updates.
    """

    SYNC_STEP1: int = 0
    SYNC_STEP2: int = 1
    SYNC_UPDATE: int = 2


def write_var_uint(num: int) -> bytes:
    """
    Encodes a payload length.

    Args:
        num: The payload length to encode.

    Returns:
        The encoded payload length.
    """
    res = []
    while num > 127:
        res.append(128 | (127 & num))
        num >>= 7
    res.append(num)
    return bytes(res)


def create_message(data: bytes, msg_type: int) -> bytes:
    """
    Creates a binary Y message.

    Args:
        data: The data to send in the message.
        msg_type: The [message type][pycrdt.YSyncMessageType].

    Returns:
        The binary Y message.
    """
    return bytes([YMessageType.SYNC, msg_type]) + write_var_uint(len(data)) + data


def create_sync_step1_message(data: bytes) -> bytes:
    """
    Creates a [SYNC_STEP1][pycrdt.YSyncMessageType.SYNC_STEP1] message consisting
    of a document state.

    Args:
        data: The document state.

    Returns:
        A [SYNC_STEP1][pycrdt.YSyncMessageType.SYNC_STEP1] message.
    """
    return create_message(data, YSyncMessageType.SYNC_STEP1)


def create_sync_step2_message(data: bytes) -> bytes:
    """
    Creates a [SYNC_STEP2][pycrdt.YSyncMessageType.SYNC_STEP2] message in
    reply to a [SYNC_STEP1][pycrdt.YSyncMessageType.SYNC_STEP1] message.

    Args:
        data: All missing updates and deletetions.

    Returns:
        A [SYNC_STEP2][pycrdt.YSyncMessageType.SYNC_STEP2] message.
    """
    return create_message(data, YSyncMessageType.SYNC_STEP2)


def create_update_message(data: bytes) -> bytes:
    """
    Creates a [SYNC_UPDATE][pycrdt.YSyncMessageType] message that
    contains a document update.

    Args:
        data: The document update.

    Returns:
        A [SYNC_UPDATE][pycrdt.YSyncMessageType] message.
    """
    return create_message(data, YSyncMessageType.SYNC_UPDATE)


class Decoder:
    """
    A decoder capable of reading messages from a byte stream.
    """

    def __init__(self, stream: bytes):
        """
        Args:
            stream: The byte stream from which to read messages.
        """
        self.stream = stream
        self.length = len(stream)
        self.i0 = 0

    def read_var_uint(self) -> int:
        """
        Decodes the current message length.

        Returns:
            The decoded length of the message.
        """
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
        """
        Reads a message from the byte stream, ready to read the next message if any.

        Returns:
            The current message, if any.
        """
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

    def read_messages(self) -> Iterator[bytes]:
        """
        A generator that reads messages from the byte stream.

        Returns:
            A generator that yields messages.
        """
        while True:
            message = self.read_message()
            if message is None:
                return
            yield message

    def read_var_string(self) -> str:
        """
        Reads a message as an UTF-8 string from the byte stream, ready to read the next message if
        any.

        Returns:
            The current message as a string.
        """
        message = self.read_message()
        if message is None:
            return ""
        return message.decode("utf-8")


def read_message(stream: bytes) -> bytes:
    """
    Reads a message from a byte stream.

    Args:
        stream: The byte stream from which to read the message.

    Returns:
        The message read from the byte stream.
    """
    message = Decoder(stream).read_message()
    assert message is not None
    return message


def handle_sync_message(message: bytes, ydoc: Doc) -> bytes | None:
    """
    Processes a [synchronization message][pycrdt.YSyncMessageType] on a document.

    Args:
        message: A synchronization message.
        ydoc: The [Doc][pycrdt.Doc] that this message targets.

    Returns:
        The [SYNC_STEP2][pycrdt.YSyncMessageType] reply message, if the message
        was a [SYNC_STEP1][pycrdt.YSyncMessageType].
    """
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
    """
    Creates a [SYNC_STEP1][pycrdt.YSyncMessageType] message that
    contains the state of a [Doc][pycrdt.Doc].

    Args:
        ydoc: The [Doc][pycrdt.Doc] for which to create the message.

    Returns:
        A [SYNC_STEP1][pycrdt.YSyncMessageType] message.
    """
    state = ydoc.get_state()
    message = create_sync_step1_message(state)
    return message
