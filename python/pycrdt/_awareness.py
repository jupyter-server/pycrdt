from __future__ import annotations

import json
import time
from typing import Any, Callable

from ._doc import Doc
from ._sync import Decoder, YMessageType, read_message, write_var_uint


class Awareness:
    client_id: int
    meta: dict[int, dict[str, Any]]
    _states: dict[int, dict[str, Any]]
    _subscriptions: list[Callable[[dict[str, Any]], None]]
    _user: dict[str, str] | None

    def __init__(
        self,
        ydoc: Doc,
        on_change: Callable[[bytes], None] | None = None,
        user: dict[str, str] | None = None,
    ):
        self.client_id = ydoc.client_id
        self.meta = {}
        self._states = {}
        self.on_change = on_change

        if user is not None:
            self.user = user

        self._subscriptions = []

    @property
    def states(self) -> dict[int, dict[str, Any]]:
        return self._states

    @property
    def user(self) -> dict[str, str] | None:
        return self._user

    @user.setter
    def user(self, user: dict[str, str]):
        self._user = user
        self.set_local_state_field("user", self._user)

    def get_changes(self, message: bytes) -> dict[str, Any]:
        """
        Updates the states with a user state.
        This function sends the changes to subscribers.

        Args:
            message: Bytes representing the user state.
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
            client_meta = self.meta.get(client_id)
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
                self.meta[client_id] = {
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
            for callback in self._subscriptions:
                callback(changes)

        return changes

    def get_local_state(self) -> dict[str, Any]:
        """
        Returns:
            The local state (the state of the current awareness client).
        """
        return self._states.get(self.client_id, {})

    def set_local_state(self, state: dict[str, Any]) -> None:
        """
        Updates the local state and meta.
        This function calls the `on_change()` callback (if provided), with the serialized states
        as argument.

        Args:
            state: The dictionary representing the state.
        """
        timestamp = int(time.time() * 1000)
        clock = self.meta.get(self.client_id, {}).get("clock", -1) + 1
        self._states[self.client_id] = state
        self.meta[self.client_id] = {"clock": clock, "last_updated": timestamp}
        # Build the message to broadcast, with the following information:
        # - message type
        # - length in bytes of the updates
        # - number of updates
        # - for each update
        #   - client_id
        #   - clock
        #   - length in bytes of the update
        #   - encoded update
        msg = json.dumps(state, separators=(",", ":")).encode("utf-8")
        msg = write_var_uint(len(msg)) + msg
        msg = write_var_uint(clock) + msg
        msg = write_var_uint(self.client_id) + msg
        msg = write_var_uint(1) + msg
        msg = write_var_uint(len(msg)) + msg
        msg = write_var_uint(YMessageType.AWARENESS) + msg

        if self.on_change:
            self.on_change(msg)

    def set_local_state_field(self, field: str, value: Any) -> None:
        """
        Sets a local state field.

        Args:
            field: The field to set.
            value: The value of the field.
        """
        current_state = self.get_local_state()
        current_state[field] = value
        self.set_local_state(current_state)

    def observe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        Subscribes to awareness changes.

        Args:
            callback: Callback that will be called when the document changes.
        """
        self._subscriptions.append(callback)

    def unobserve(self) -> None:
        """
        Unsubscribes to awareness changes. This method removes all the callbacks.
        """
        self._subscriptions = []
