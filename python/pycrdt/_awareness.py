from __future__ import annotations

import json
import time
from typing import Any, Callable
from uuid import uuid4

from ._doc import Doc
from ._sync import Decoder, YMessageType, read_message, write_var_uint


class Awareness:
    client_id: int
    _meta: dict[int, dict[str, Any]]
    _states: dict[int, dict[str, Any]]
    _subscriptions: dict[str, Callable[[dict[str, Any]], None]]

    def __init__(self, ydoc: Doc):
        """
        Args:
            ydoc: The [Doc][pycrdt.Doc] to associate the awareness with.
        """
        self.client_id = ydoc.client_id
        self._meta = {}
        self._states = {}

        self._subscriptions = {}

    @property
    def meta(self) -> dict[int, dict[str, Any]]:
        """The clients' metadata."""
        return self._meta

    @property
    def states(self) -> dict[int, dict[str, Any]]:
        """The client states."""
        return self._states

    def get_changes(self, message: bytes) -> dict[str, Any]:
        """
        Updates the states and sends the changes to subscribers.

        Args:
            message: The binary changes.

        Returns:
            A dictionary summarizing the changes.
        """
        message = read_message(message)
        decoder = Decoder(message)
        timestamp = int(time.time() * 1000)
        added = []
        updated = []
        filtered_updated = []
        removed = []
        states = []
        length = decoder.read_var_uint()
        for _ in range(length):
            client_id = decoder.read_var_uint()
            clock = decoder.read_var_uint()
            state_str = decoder.read_var_string()
            state = None if not state_str else json.loads(state_str)
            if state is not None:
                states.append(state)
            client_meta = self._meta.get(client_id)
            prev_state = self._states.get(client_id)
            curr_clock = 0 if client_meta is None else client_meta["clock"]
            if curr_clock < clock or (
                curr_clock == clock and state is None and client_id in self._states
            ):
                if state is None:
                    if client_id == self.client_id and self._states.get(client_id) is not None:
                        clock += 1
                    else:
                        if client_id in self._states:
                            del self._states[client_id]
                else:
                    self._states[client_id] = state
                self._meta[client_id] = {
                    "clock": clock,
                    "last_updated": timestamp,
                }
                if client_meta is None and state is not None:
                    added.append(client_id)
                elif client_meta is not None and state is None:
                    removed.append(client_id)
                elif state is not None:
                    if state != prev_state:
                        filtered_updated.append(client_id)
                    updated.append(client_id)

        changes = {
            "added": added,
            "updated": updated,
            "filtered_updated": filtered_updated,
            "removed": removed,
            "states": states,
        }

        # Do not trigger the callbacks if it is only a keep alive update
        if added or filtered_updated or removed:
            for callback in self._subscriptions.values():
                callback(changes)

        return changes

    def get_local_state(self) -> dict[str, Any]:
        """
        Returns:
            The local state.
        """
        return self._states.get(self.client_id, {})

    def set_local_state(self, state: dict[str, Any], encode: bool = True) -> bytes | None:
        """
        Updates the local state and meta, and optionally returns the encoded new state.

        Args:
            state: The new local state.
            encode: Whether to encode the new state and return it.

        Returns:
            The encoded new state, if `encode==True`.
        """
        timestamp = int(time.time() * 1000)
        clock = self._meta.get(self.client_id, {}).get("clock", -1) + 1
        self._states[self.client_id] = state
        self._meta[self.client_id] = {"clock": clock, "last_updated": timestamp}
        if encode:
            update = json.dumps(state, separators=(",", ":")).encode()
            message0 = [update]
            message0.insert(0, write_var_uint(len(update)))
            message0.insert(0, write_var_uint(clock))
            message0.insert(0, write_var_uint(self.client_id))
            message0.insert(0, bytes(1))
            message0_bytes = b"".join(message0)
            message1 = [
                bytes(YMessageType.AWARENESS),
                write_var_uint(len(message0_bytes)),
                message0_bytes,
            ]
            message = b"".join(message1)
            return message
        return None

    def set_local_state_field(self, field: str, value: Any, encode: bool = True) -> bytes | None:
        """
        Sets a local state field, and optionally returns the encoded new state.

        Args:
            field: The field of the local state to set.
            value: The value associated with the field.

        Returns:
            The encoded new state, if `encode==True`.
        """
        current_state = self.get_local_state()
        current_state[field] = value
        return self.set_local_state(current_state, encode)

    def observe(self, callback: Callable[[dict[str, Any]], None]) -> str:
        """
        Registers the given callback to awareness changes.

        Args:
            callback: The callback to call with the awareness changes.

        Returns:
            The subscription ID that can be used to unobserve.
        """
        id = str(uuid4())
        self._subscriptions[id] = callback
        return id

    def unobserve(self, id: str) -> None:
        """
        Unregisters the given subscription ID from awareness changes.

        Args:
            id: The subscription ID to unregister.
        """
        del self._subscriptions[id]
