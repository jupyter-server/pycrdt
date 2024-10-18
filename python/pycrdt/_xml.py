from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, overload

from ._base import BaseEvent, BaseType, base_types, event_types
from ._pycrdt import XmlElement as _XmlElement
from ._pycrdt import XmlEvent as _XmlEvent
from ._pycrdt import XmlFragment as _XmlFragment
from ._pycrdt import XmlText as _XmlText

if TYPE_CHECKING:  # pragma: no cover
    from typing import Any, Iterable, Mapping, Sized, TypeVar

    from ._doc import Doc

    T = TypeVar("T")


def _integrated_to_wrapper(
    doc: Doc, inner: _XmlText | _XmlElement | _XmlFragment
) -> XmlText | XmlElement | XmlFragment:
    if isinstance(inner, _XmlElement):
        return XmlElement(_doc=doc, _integrated=inner)
    if isinstance(inner, _XmlFragment):
        return XmlFragment(_doc=doc, _integrated=inner)
    return XmlText(_doc=doc, _integrated=inner)


def _check_slice(value: Sized, key: slice) -> tuple[int, int]:
    if key.step is not None:
        raise RuntimeError("Step not supported")
    if key.start is None:
        start = 0
    elif key.start < 0:
        raise RuntimeError("Negative start not supported")
    else:
        start = key.start
    if key.stop is None:
        stop = len(value)
    elif key.stop < 0:
        raise RuntimeError("Negative stop not supported")
    else:
        stop = key.stop
    return start, stop


class _XmlBaseMixin(BaseType):
    _integrated: _XmlElement | _XmlText | _XmlFragment | None

    @property
    def parent(self) -> XmlFragment | XmlElement | XmlText | None:
        """
        The parent of this node, if any.
        """
        inner = self.integrated.parent()
        if inner is None:
            return None
        return _integrated_to_wrapper(self.doc, inner)

    def __str__(self):
        with self.doc.transaction() as txn:
            return self.integrated.get_string(txn._txn)

    def __eq__(self, other: object):
        if not isinstance(other, _XmlBaseMixin):
            return False
        return self.integrated == other.integrated

    def __hash__(self) -> int:
        return hash(self.integrated)


class _XmlFragmentTraitMixin(_XmlBaseMixin):
    _integrated: _XmlElement | _XmlFragment | None

    @property
    def children(self) -> XmlChildrenView:
        """
        A list-like view into this object's child nodes.
        """
        return XmlChildrenView(self)


class _XmlTraitMixin(_XmlBaseMixin):
    _integrated: _XmlElement | _XmlText | None

    @property
    def attributes(self) -> XmlAttributesView:
        """
        A dict-like view into this object's attributes.
        """
        return XmlAttributesView(self)


class XmlFragment(_XmlFragmentTraitMixin):
    _prelim: list[XmlFragment | XmlElement | XmlText] | None
    _integrated: _XmlFragment | None

    def __init__(
        self,
        init: Iterable[XmlFragment | XmlElement | XmlText] | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _XmlFragment | None = None,
    ) -> None:
        super().__init__(
            init=list(init) if init is not None else None,
            _doc=_doc,
            _integrated=_integrated,
        )

    def to_py(self) -> None:
        raise ValueError("XmlFragment has no Python equivalent")

    def _get_or_insert(self, name: str, doc: Doc) -> Any:
        return doc._doc.get_or_insert_xml_fragment(name)

    def _init(self, value: list[XmlElement | str] | None) -> None:
        if value is None:
            return
        for obj in value:
            self.children.append(obj)


class XmlElement(_XmlFragmentTraitMixin, _XmlTraitMixin):
    _prelim: tuple[str, list[tuple[str, str]], list[str | XmlElement | XmlText]] | None
    _integrated: _XmlElement | None

    def __init__(
        self,
        tag: str | None = None,
        attributes: dict[str, str] | Iterable[tuple[str, str]] | None = None,
        contents: Iterable[XmlFragment | XmlElement | XmlText] | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _XmlElement | None = None,
    ) -> None:
        if tag is None and attributes is None and contents is None:
            init = None
        elif (attributes is not None or contents is not None) and tag is None:
            raise ValueError("Tag is required if specifying attributes or contents")
        else:
            if isinstance(attributes, dict):
                init_attrs = list(attributes.items())
            elif attributes is not None:
                init_attrs = list(attributes)
            else:
                init_attrs = []

            init = (
                tag,
                init_attrs,
                list(contents) if contents is not None else [],
            )

        super().__init__(
            init=init,
            _doc=_doc,
            _integrated=_integrated,
        )

    def to_py(self) -> None:
        raise ValueError("XmlElement has no Python equivalent")

    def _get_or_insert(self, _name: str, _doc: Doc) -> Any:
        raise ValueError("Cannot get an XmlElement from a doc - get an XmlFragment instead.")

    def _init(
        self, value: tuple[str, list[tuple[str, str]], list[str | XmlElement | XmlText]] | None
    ):
        if value is None:
            return
        _, attrs, contents = value
        with self.doc.transaction():
            for k, v in attrs:
                self.attributes[k] = v
            for child in contents:
                self.children.append(child)

    @property
    def tag(self) -> str | None:
        return self.integrated.tag()


class XmlText(_XmlTraitMixin):
    """
    A piece of text in an XML tree.

    This is similar to the `Text` object, but instead of existing in a doc on its own, it is a child
    of an `XmlElement` or `XmlFragment`.
    """

    _prelim: str | None
    _integrated: _XmlText | None

    def __init__(
        self,
        init: str | None = None,
        *,
        _doc: Doc | None = None,
        _integrated: _XmlText | None = None,
    ) -> None:
        super().__init__(
            init=init,
            _doc=_doc,
            _integrated=_integrated,
        )

    def _get_or_insert(self, _name: str, _doc: Doc) -> Any:
        raise ValueError("Cannot get an XmlText from a doc - get an XmlFragment instead.")

    def to_py(self) -> str | None:
        if self._integrated is None:
            return self._prelim
        return str(self)

    def _init(self, value: str | None) -> None:
        if value is None:
            return
        with self.doc.transaction() as txn:
            self.integrated.insert(txn._txn, 0, value)

    def __len__(self) -> int:
        with self.doc.transaction() as txn:
            return self.integrated.len(txn._txn)

    def __iadd__(self, value: str) -> XmlText:
        with self.doc.transaction():
            self.insert(len(self), value)
        return self

    def insert(self, index: int, value: str, attrs: Mapping[str, Any] | None = None) -> None:
        """
        Inserts text at the specified index, optionally with attributes
        """
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            self.integrated.insert(
                txn._txn, index, value, attrs.items() if attrs is not None else iter([])
            )

    def insert_embed(self, index: int, value: Any, attrs: dict[str, Any] | None = None) -> None:
        """
        Insert 'value' as an embed at a given index in the text.
        """
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            self.integrated.insert_embed(
                txn._txn, index, value, iter(attrs.items()) if attrs is not None else None
            )

    def format(self, start: int, stop: int, attrs: dict[str, Any]) -> None:
        """
        Formats existing text with attributes.

        Affects the text from the 'start' index (inclusive) to the 'stop' index (exclusive).
        """
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            start, stop = _check_slice(self, slice(start, stop))
            length = stop - start
            if length > 0:
                self.integrated.format(txn._txn, start, length, iter(attrs.items()))

    def diff(self) -> list[tuple[Any, dict[str, Any] | None]]:
        """
        Returns list of formatted chunks that the current text corresponds to.

        Each list item is a tuple containing the chunk's contents and formatting attributes. The
        contents is usually the text as a string, but may be other data for embedded objects.
        """
        with self.doc.transaction() as txn:
            return self.integrated.diff(txn._txn)

    def __delitem__(self, key: int | slice) -> None:
        with self.doc.transaction() as txn:
            self._forbid_read_transaction(txn)
            if isinstance(key, int):
                self.integrated.remove_range(txn._txn, key, 1)
            elif isinstance(key, slice):
                start, stop = _check_slice(self, key)
                length = stop - start
                if length > 0:
                    self.integrated.remove_range(txn._txn, start, length)
            else:
                raise RuntimeError(f"Index not supported: {key}")

    def clear(self) -> None:
        """Remove the entire range of characters."""
        del self[:]


class XmlEvent(BaseEvent):
    __slots__ = ["children_changed", "target", "path", "delta", "keys"]


class XmlAttributesView:
    """
    A list-like view into an `XmlFragment` or `XmlElement`'s child nodes.

    Supports `len`, `in`, and getting, setting, and deleting by index. Iteration will iterate over
    key/value tuples.
    """

    inner: _XmlTraitMixin

    def __init__(self, inner: _XmlTraitMixin) -> None:
        self.inner = inner

    def get(self, key: str) -> Any | None:
        """
        Gets the value of an attribute, or `None` if there is no attribute with the passed in name.
        """
        with self.inner.doc.transaction() as txn:
            v = self.inner.integrated.attribute(txn._txn, key)
            if v is None:
                return None
            return v

    def __getitem__(self, key: str) -> Any:
        """
        Gets an attribute by name.
        """
        v = self.get(key)
        if v is None:
            raise KeyError(key)
        return v

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Sets an attribute.
        """
        with self.inner.doc.transaction() as txn:
            self.inner._forbid_read_transaction(txn)
            self.inner.integrated.insert_attribute(txn._txn, key, value)

    def __delitem__(self, key: str) -> None:
        """
        Deletes an attribute
        """
        with self.inner.doc.transaction() as txn:
            self.inner._forbid_read_transaction(txn)
            self.inner.integrated.remove_attribute(txn._txn, key)

    def __contains__(self, key: str) -> bool:
        """
        Checks if an attribute exists
        """
        return self.get(key) is not None

    def __len__(self) -> int:
        """
        Gets the number of attributes
        """
        with self.inner.doc.transaction() as txn:
            return len(self.inner.integrated.attributes(txn._txn))

    def __iter__(self) -> Iterable[tuple[str, Any]]:
        """
        Iterates over each attribute, as key/value tuples.
        """
        with self.inner.doc.transaction() as txn:
            return iter(self.inner.integrated.attributes(txn._txn))


class XmlChildrenView:
    """
    A list-like view into an `XmlFragment` or `XmlElement`'s child nodes.

    Supports `iter`, `len`, and getting, setting, and deleting by index.
    """

    inner: _XmlFragmentTraitMixin

    def __init__(self, inner: _XmlFragmentTraitMixin) -> None:
        self.inner = inner

    def __len__(self) -> int:
        """
        Gets the number of child nodes
        """
        with self.inner.doc.transaction() as txn:
            return self.inner.integrated.len(txn._txn)

    def __getitem__(self, index: int) -> XmlElement | XmlFragment | XmlText:
        """
        Gets a child by its index.
        """
        with self.inner.doc.transaction() as txn:
            if index >= len(self):
                raise IndexError(index)
            return _integrated_to_wrapper(
                self.inner.doc, self.inner.integrated.get(txn._txn, index)
            )

    def __delitem__(self, key: int | slice) -> None:
        """
        Removes a child (integer index) or a range of children (slice index).
        """
        with self.inner.doc.transaction() as txn:
            self.inner._forbid_read_transaction(txn)
            if isinstance(key, int):
                self.inner.integrated.remove_range(txn._txn, key, 1)
            elif isinstance(key, slice):
                start, stop = _check_slice(self, key)
                length = stop - start
                if length > 0:
                    self.inner.integrated.remove_range(txn._txn, start, length)
            else:
                raise RuntimeError(f"Index not supported: {key}")

    def __setitem__(self, key: int, value: str | XmlText | XmlElement):
        """
        Replaces a child. Equivalent to deleting the index and then inserting the new value.
        """
        with self.inner.doc.transaction():
            del self[key]
            self.insert(key, value)

    def __iter__(self) -> Iterator[XmlText | XmlElement | XmlFragment]:
        """
        Iterates over child nodes.
        """
        with self.inner.doc.transaction():
            children = [self[i] for i in range(len(self))]
        return iter(children)

    @overload
    def insert(self, index: int, element: str | XmlText) -> XmlText: ...
    @overload
    def insert(self, index: int, element: XmlElement) -> XmlElement: ...

    def insert(self, index: int, element: str | XmlText | XmlElement) -> XmlText | XmlElement:
        """
        Inserts a new node into the element's or fragment's children at the specified index.

        Passing in a `str` will convert it to an `XmlText`. Returns the passed in element, which
        will now be integrated into the tree.
        """
        with self.inner.doc.transaction() as txn:
            self.inner._forbid_read_transaction(txn)
            if index > len(self):
                raise IndexError(index)
            if isinstance(element, str):
                integrated = self.inner.integrated.insert_str(txn._txn, index, element)
                return XmlText(_doc=self.inner.doc, _integrated=integrated)
            elif isinstance(element, XmlText):
                if element._integrated is not None:
                    raise ValueError("Cannot insert an integrated XmlText")
                integrated = self.inner.integrated.insert_str(txn._txn, index, element.prelim)
                element._integrate(self.inner.doc, integrated)
                return element
            elif isinstance(element, XmlElement):
                if element._integrated is not None:
                    raise ValueError("Cannot insert an integrated XmlElement")
                prelim = element.prelim
                integrated = self.inner.integrated.insert_element_prelim(txn._txn, index, prelim[0])
                element._integrate(self.inner.doc, integrated)
                element._init(prelim)
                return element
            else:
                raise ValueError("Cannot add value to XML: " + repr(element))

    @overload
    def append(self, element: str | XmlText) -> XmlText: ...
    @overload
    def append(self, element: XmlElement) -> XmlElement: ...

    def append(self, element: str | XmlText | XmlElement) -> XmlText | XmlElement:
        """
        Appends a new node to the end of the element's or fragment's children.

        Equivalent to `insert` at index `len(self)`.
        """
        return self.insert(len(self), element)


base_types[_XmlFragment] = XmlFragment
base_types[_XmlElement] = XmlElement
base_types[_XmlText] = XmlText
event_types[_XmlEvent] = XmlEvent
