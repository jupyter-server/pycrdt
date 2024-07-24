import pytest
from pycrdt import Array, Doc, Map, Text


def test_callback_transaction():
    text = Text()
    array = Array()
    map_ = Map()
    Doc(
        {
            "text": text,
            "array": array,
            "map": map_,
        }
    )
    events = []

    def callback(event):
        target = event.target
        doc = target.doc
        with doc.transaction():
            events.append(target.to_py())
            with doc.transaction():
                events.append(str(target))

    sub0 = text.observe(callback)  # noqa: F841
    sub1 = array.observe(callback)  # noqa: F841
    sub2 = map_.observe(callback)  # noqa: F841
    with text.doc.transaction():
        text += "hello"
        text += " world"
    array.append(1)
    map_["foo"] = "bar"
    assert events == [
        "hello world",
        "hello world",
        [1],
        "[1]",
        {"foo": "bar"},
        '{"foo":"bar"}',
    ]


def test_origin():
    doc = Doc()
    doc["text"] = text = Text()

    class Origin:
        pass

    origin0 = Origin()
    origin1 = None

    def callback(event, txn):
        nonlocal origin1
        origin1 = txn.origin

    text.observe(callback)

    with doc.transaction(origin=origin0) as txn:
        text += "Hello"

    assert origin1 is origin0

    with pytest.raises(RuntimeError) as excinfo:
        txn.origin()

    assert str(excinfo.value) == "No current transaction"

    with pytest.raises(TypeError) as excinfo:
        doc.transaction(origin={})

    assert str(excinfo.value) == "Origin must be hashable"

    with doc.transaction() as txn:
        assert txn.origin is None


def test_observe_callback_params():
    doc = Doc()
    doc["text"] = text = Text()

    cb0_called = False
    cb1_called = False
    cb2_called = False

    def callback0():
        nonlocal cb0_called
        cb0_called = True

    def callback1(event):
        nonlocal cb1_called
        cb1_called = True

    def callback2(event, txn):
        nonlocal cb2_called
        cb2_called = True

    text.observe(callback0)
    text.observe(callback1)
    text.observe(callback2)

    with doc.transaction():
        text += "Hello, World!"

    assert cb0_called
    assert cb1_called
    assert cb2_called
