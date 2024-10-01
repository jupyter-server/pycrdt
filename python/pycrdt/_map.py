from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, cast

from ._base import BaseDoc, BaseEvent, BaseType, base_types, event_types
from ._pycrdt import Map as _Map
from ._pycrdt import MapEvent as _MapEvent
from ._pycrdt import Subscription

if TYPE_CHECKING:  # pragma: no cover
    from ._doc import Doc


class Map(BaseType):
    """
    A collection used to store key-value entries in an unordered manner, similar to a Python `dict`.
    """

    _prelim: dict | None
    _integrated: _Map | None

    def __init__(
        self,
        init: dict | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _Map | None = None,
    ) -> None:
        """
        Creates a map with an optional initial value:
        ```py
        map0 = Map()
        map1 = Map({"foo": 0, "bar": 3, "baz": map0})
        ```

        Args:
            init: The list from which to initialize the array.
        """
        super().__init__(
            init=init,
            _doc=_doc,
            _integrated=_integrated,
        )

    def _init(self, value: dict[str, Any] | None) -> None:
        if value is None:
            return
        with self.doc.transaction():
            for k, v in value.items():
                self._set(k, v)

    def _set(self, key: str, value: Any) -> None:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            if isinstance(value, BaseDoc):
                # subdoc
                self.integrated.insert_doc(txn._txn, key, value._doc)
            elif isinstance(value, BaseType):
                # shared type
                assert txn._txn is not None
                self._do_and_integrate("insert", value, txn._txn, key)
            else:
                # primitive type
                self.integrated.insert(txn._txn, key, value)

    def _get_or_insert(self, name: str, doc: Doc) -> _Map:
        return doc._doc.get_or_insert_map(name)

    def __len__(self) -> int:
        """
        ```py
        Doc()["map0"] = map0 = Map({"foo": 0, "bar": 1})
        assert len(map0) == 2
        ```
        Returns:
            The length of the map.
        """
        with self.doc.transaction() as txn:
            return self.integrated.len(txn._txn)

    def __str__(self) -> str:
        """
        ```py
        Doc()["map0"] = map0 = Map({"foo": 0, "bar": 1})
        assert str(map0) == '{"foo":0,"bar":1}'
        ```

        Returns:
            The string representation of the map.
        """
        with self.doc.transaction() as txn:
            return self.integrated.to_json(txn._txn)

    def to_py(self) -> dict | None:
        """
        Recursively converts the map's items to Python objects, and
        returns them in a `dict`. If the map was not yet inserted in a document,
        returns `None` if the map was not initialized.

        Returns:
            The map recursively converted to Python objects, or `None`.
        """
        if self._integrated is None:
            py = self._prelim
            if py is None:
                return None
        else:
            py = dict(self)
        for key, val in py.items():
            if isinstance(val, BaseType):
                py[key] = val.to_py()
        return py

    def __delitem__(self, key: str) -> None:
        """
        Removes the item at the given key from the map:
        ```py
        Doc()["map0"] = map0 = Map({"foo": 0, "bar": 1})
        del map0["foo"]
        assert map0.to_py() == {"bar": 1}
        ```

        Args:
            key: The key of the item to remove.
        """
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            self._check_key(key)
            self.integrated.remove(txn._txn, key)

    def __getitem__(self, key: str) -> Any:
        """
        Gets the value at the given key:
        ```py
        Doc()["map0"] = map0 = Map({"foo": 0, "bar": 1})
        assert map0["foo"] == 0
        ```

        Returns:
            The value at the given key.
        """
        with self.doc.transaction() as txn:
            self._check_key(key)
            return self._maybe_as_type_or_doc(self.integrated.get(txn._txn, key))

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Sets a value at the given key:
        ```py
        Doc()["map0"] = map0 = Map({"foo": 0, "bar": 1})
        map0["foo"] = 2
        assert map0["foo"] == 2
        ```

        Args:
            key: The key to set.
            value: The value to set.

        Raises:
            RuntimeError: Key must be of type string.
        """
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        with self.doc.transaction():
            self._set(key, value)

    def __iter__(self) -> Iterable[str]:
        """
        ```py
        Doc()["map0"] = map0 = Map({"foo": 0, "bar": 0})
        for key in m0:
            assert map[key] == 0
        ```
        Returns:
            An iterable over the keys of the map.
        """
        return self.keys()

    def __contains__(self, item: str) -> bool:
        """
        Checks if the given key is in the map:
        ```py
        Doc()["map0"] = map0 = Map({"foo": 0, "bar": 0})
        assert "baz" not in map0:
        ```

        Args:
            item: The key to look for in the map.

        Returns:
            True if the key was found.
        """
        return item in self.keys()

    def get(self, key: str, default_value: Any | None = None) -> Any | None:
        """
        Returns the value corresponding to the given key if it exists, otherwise
        returns the `default_value`.

        Args:
            key: The key of the value to get.
            default_value: The optional default value to return if the key is not found.

        Returns:
            The value at the given key, or the default value.
        """
        with self.doc.transaction():
            if key in self.keys():
                return self[key]
            return default_value

    def pop(self, *args: Any) -> Any:
        """
        Removes the entry at the given key from the map, and returns the corresponding value.

        Args:
            args: The key of the value to pop, and an optional default value.

        Returns:
            The value at the given key, or the default value if passed.
        """
        key, *default_value = args
        with self.doc.transaction():
            if key not in self.keys():
                if not default_value:
                    raise KeyError
                return default_value[0]
            res = self[key]
            if isinstance(res, BaseType):
                res = res.to_py()
            del self[key]
            return res

    def _check_key(self, key: str):
        if not isinstance(key, str):
            raise RuntimeError("Key must be of type string")
        if key not in self.keys():
            raise KeyError(key)

    def keys(self) -> Iterable[str]:
        """
        Returns:
            An iterable over the keys of the map.
        """
        with self.doc.transaction() as txn:
            return iter(self.integrated.keys(txn._txn))

    def values(self) -> Iterable[Any]:
        """
        Returns:
            An iterable over the values of the map.
        """
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn._txn):
                yield self[k]

    def items(self) -> Iterable[tuple[str, Any]]:
        """
        Returns:
            An iterable over the key-value pairs of the map.
        """
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn._txn):
                yield k, self[k]

    def clear(self) -> None:
        """
        Removes all entries from the map.
        """
        with self.doc.transaction() as txn:
            for k in self.integrated.keys(txn._txn):
                del self[k]

    def update(self, value: dict[str, Any]) -> None:
        """
        Sets entries in the map from all entries in the passed `dict`.

        Args:
            value: The `dict` from which to get the entries to update.
        """
        self._init(value)

    def observe(self, callback: Callable[[MapEvent], None]) -> Subscription:
        """
        Subscribes a callback to be called with the map event.

        Args:
            callback: The callback to call with the [MapEvent][pycrdt.MapEvent].
        """
        return super().observe(cast(Callable[[BaseEvent], None], callback))


class MapEvent(BaseEvent):
    """
    A map change event.

    Attributes:
        target (Map): The changed map.
        delta (list[dict[str, Any]]): A list of items describing the changes.
        path (list[int | str]): A list with the indices pointing to the map that was changed.
    """

    __slots__ = "target", "keys", "path"


base_types[_Map] = Map
event_types[_MapEvent] = MapEvent
