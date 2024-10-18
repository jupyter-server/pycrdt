from __future__ import annotations

import copy
import json
import time
from typing import Any, Callable, cast
from uuid import uuid4

from ._doc import Doc
from ._sync import Decoder, Encoder


class Awareness:
    client_id: int
    _meta: dict[int, dict[str, Any]]
    _states: dict[int, dict[str, Any]]
    _subscriptions: dict[str, Callable[[str, tuple[dict[str, Any], Any]], None]]

    def __init__(self, ydoc: Doc):
        """
        Args:
            ydoc: The [Doc][pycrdt.Doc] to associate the awareness with.
        """
        self.client_id = ydoc.client_id
        self._meta = {}
        self._states = {}
        self._subscriptions = {}
        self.set_local_state({})

    @property
    def meta(self) -> dict[int, dict[str, Any]]:
        """The clients' metadata."""
        return self._meta

    @property
    def states(self) -> dict[int, dict[str, Any]]:
        """The client states."""
        return self._states

    def get_local_state(self) -> dict[str, Any] | None:
        """
        Returns:
            The local state, if any.
        """
        return self._states.get(self.client_id)

    def set_local_state(self, state: dict[str, Any] | None) -> None:
        """
        Updates the local state and meta, and sends the changes to subscribers.

        Args:
            state: The new local state, if any.
        """
        client_id = self.client_id
        curr_local_meta = self._meta.get(client_id)
        clock = 0 if curr_local_meta is None else curr_local_meta["clock"] + 1
        prev_state = self._states.get(client_id)
        if prev_state is not None:
            prev_state = copy.deepcopy(prev_state)
        if state is None:
            if client_id in self._states:
                del self._states[client_id]
        else:
            self._states[client_id] = state
        timestamp = int(time.time() * 1000)
        self._meta[client_id] = {"clock": clock, "lastUpdated": timestamp}
        added = []
        updated = []
        filtered_updated = []
        removed = []
        if state is None:
            removed.append(client_id)
        elif prev_state is None:
            if state is not None:
                added.append(client_id)
        else:
            updated.append(client_id)
            if prev_state != state:
                filtered_updated.append(client_id)
        if added or filtered_updated or removed:
            for callback in self._subscriptions.values():
                callback(
                    "change",
                    ({"added": added, "updated": filtered_updated, "removed": removed}, "local"),
                )
        for callback in self._subscriptions.values():
            callback("update", ({"added": added, "updated": updated, "removed": removed}, "local"))

    def set_local_state_field(self, field: str, value: Any) -> None:
        """
        Sets a local state field.

        Args:
            field: The field of the local state to set.
            value: The value associated with the field.
        """
        state = self.get_local_state()
        if state is not None:
            state = copy.deepcopy(state)
            state[field] = value
            self.set_local_state(state)

    def encode_awareness_update(self, client_ids: list[int]) -> bytes:
        """
        Creates an encoded awareness update of the clients given by their IDs.

        Args:
            client_ids: The list of client IDs for which to create an update.

        Returns:
            The encoded awareness update.
        """
        encoder = Encoder()
        encoder.write_var_uint(len(client_ids))
        for client_id in client_ids:
            state = self._states.get(client_id)
            clock = cast(int, self._meta.get(client_id, {}).get("clock"))
            encoder.write_var_uint(client_id)
            encoder.write_var_uint(clock)
            encoder.write_var_string(json.dumps(state, separators=(",", ":")))
        return encoder.to_bytes()

    def apply_awareness_update(self, update: bytes, origin: Any) -> None:
        """
        Applies the binary update and notifies subscribers with changes.

        Args:
            update: The binary update.
            origin: The origin of the update.
        """
        decoder = Decoder(update)
        timestamp = int(time.time() * 1000)
        added = []
        updated = []
        filtered_updated = []
        removed = []
        length = decoder.read_var_uint()
        for _ in range(length):
            client_id = decoder.read_var_uint()
            clock = decoder.read_var_uint()
            state_str = decoder.read_var_string()
            state = None if not state_str else json.loads(state_str)
            client_meta = self._meta.get(client_id)
            prev_state = self._states.get(client_id)
            curr_clock = 0 if client_meta is None else client_meta["clock"]
            if curr_clock < clock or (
                curr_clock == clock and state is None and client_id in self._states
            ):
                if state is None:
                    # Never let a remote client remove this local state.
                    if client_id == self.client_id and self.get_local_state() is not None:
                        # Remote client removed the local state. Do not remove state.
                        # Broadcast a message indicating that this client still exists by increasing
                        # the clock.
                        clock += 1
                    else:
                        if client_id in self._states:
                            del self._states[client_id]
                else:
                    self._states[client_id] = state
                self._meta[client_id] = {
                    "clock": clock,
                    "lastUpdated": timestamp,
                }
                if client_meta is None and state is not None:
                    added.append(client_id)
                elif client_meta is not None and state is None:
                    removed.append(client_id)
                elif state is not None:
                    if state != prev_state:
                        filtered_updated.append(client_id)
                    updated.append(client_id)
        if added or filtered_updated or removed:
            for callback in self._subscriptions.values():
                callback(
                    "change",
                    ({"added": added, "updated": filtered_updated, "removed": removed}, origin),
                )
        if added or updated or removed:
            for callback in self._subscriptions.values():
                callback(
                    "update", ({"added": added, "updated": updated, "removed": removed}, origin)
                )

    def observe(self, callback: Callable[[str, tuple[dict[str, Any], Any]], None]) -> str:
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
