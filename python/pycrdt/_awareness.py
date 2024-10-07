from __future__ import annotations

import json
import time
from typing import Any, Callable
from uuid import uuid4

from typing_extensions import deprecated

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

    @deprecated("Use `apply_awareness_update()` instead")
    def get_changes(self, message: bytes) -> dict[str, Any]:
        """
        Apply states update and sends the changes to subscribers.

        Args:
            message: The binary changes.

        Returns:
            A dictionary summarizing the changes.
        """
        changes = self.apply_awareness_update(message, "remote")
        states_changes = changes["changes"]
        client_ids = [*states_changes["added"], *states_changes["filtered_updated"]]
        states = [self._states[client_id] for client_id in client_ids]
        states_changes["states"] = states
        return states_changes

    def apply_awareness_update(self, update: bytes, origin: str) -> dict[str, Any]:
        """
        Apply states update and sends the changes to subscribers.

        Args:
            message: The binary changes.
            origin: The origin of the change.

        Returns:
            A dictionary with the changes and the origin.
        """
        update = read_message(update)
        decoder = Decoder(update)
        states = []
        length = decoder.read_var_uint()
        states_changes = {
            "added": [],
            "updated": [],
            "filtered_updated": [],
            "removed": [],
        }

        for _ in range(length):
            client_id = decoder.read_var_uint()
            clock = decoder.read_var_uint()
            state_str = decoder.read_var_string()
            state = None if not state_str else json.loads(state_str)
            if state is not None:
                states.append(state)
            self._update_states(client_id, clock, state, states_changes)

        changes = {
            "changes": states_changes,
            "origin": origin,
        }

        # Do not trigger the callbacks if it is only a keep alive update
        if (
            states_changes["added"]
            or states_changes["filtered_updated"]
            or states_changes["removed"]
        ):
            for callback in self._subscriptions.values():
                callback(changes)

        return changes

    def get_local_state(self) -> dict[str, Any]:
        """
        Returns:
            The local state.
        """
        return self._states.get(self.client_id, {})

    def set_local_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Updates the local state and meta, and sends the changes to subscribers.

        Args:
            state: The new local state.

        Returns:
            A dictionary with the changes and the origin (="local").
        """
        clock = self._meta.get(self.client_id, {}).get("clock", 0) + 1
        states_changes = {
            "added": [],
            "updated": [],
            "filtered_updated": [],
            "removed": [],
        }
        self._update_states(self.client_id, clock, state, states_changes)

        changes = {
            "changes": states_changes,
            "origin": "local",
        }

        if (
            states_changes["added"]
            or states_changes["filtered_updated"]
            or states_changes["removed"]
        ):
            for callback in self._subscriptions.values():
                callback(changes)

        return changes

    def set_local_state_field(self, field: str, value: Any) -> dict[str, Any]:
        """
        Sets a local state field, and optionally returns the encoded new state.

        Args:
            field: The field of the local state to set.
            value: The value associated with the field.

        Returns:
            A dictionary with the changes and the origin (="local").
        """
        current_state = self.get_local_state()
        current_state[field] = value
        return self.set_local_state(current_state)

    def encode_awareness_update(self, client_ids: list[int]) -> bytes | None:
        """
        Encode the states of the client ids.

        Args:
            client_ids: The list of clients' state to update.

        Returns:
            The encoded clients' state.
        """
        messages = []
        for client_id in client_ids:
            if client_id not in self._states:
                continue
            state = self._states[client_id]
            meta = self._meta[client_id]
            update = json.dumps(state, separators=(",", ":")).encode()
            client_msg = [update]
            client_msg.insert(0, write_var_uint(len(update)))
            client_msg.insert(0, write_var_uint(meta.get("clock", 0)))
            client_msg.insert(0, write_var_uint(client_id))
            messages.append(b"".join(client_msg))

        if not messages:
            return

        messages.insert(0, write_var_uint(len(client_ids)))
        encoded_messages = b"".join(messages)

        message = [
            write_var_uint(YMessageType.AWARENESS),
            write_var_uint(len(encoded_messages)),
            encoded_messages,
        ]
        return b"".join(message)

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

    def _update_states(
        self, client_id: int, clock: int, state: Any, states_changes: dict[str, list[str]]
    ) -> None:
        """
        Update the states of the clients, and the states_changes dictionary.

        Args:
            client_id: The client's state to update.
            clock: The clock of this client.
            state: The updated state.
            states_changes: The changes to updates.
        """
        timestamp = int(time.time() * 1000)
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
                states_changes["added"].append(client_id)
            elif client_meta is not None and state is None:
                states_changes["removed"].append(client_id)
            elif state is not None:
                if state != prev_state:
                    states_changes["filtered_updated"].append(client_id)
                states_changes["updated"].append(client_id)
