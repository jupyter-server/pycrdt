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
    doc0 = Doc()
    doc0["text"] = text = Text()

    class Origin:
        pass

    origin0 = Origin()
    origin1 = None

    def callback(event, txn):
        nonlocal origin1
        origin1 = txn.origin

    text.observe(callback)

    with doc0.transaction(origin=origin0) as txn:
        text += "Hello"

    assert origin1 is origin0

    with pytest.raises(RuntimeError) as excinfo:
        txn.origin()

    assert str(excinfo.value) == "No current transaction"

    with pytest.raises(TypeError) as excinfo:
        doc0.transaction(origin={})

    assert str(excinfo.value) == "Origin must be hashable"

    with doc0.transaction() as txn:
        assert txn.origin is None

    doc1 = Doc()
    with doc0.transaction(origin=origin0) as txn0:
        with doc1.transaction(origin=origin0) as txn1:
            assert txn0.origin == origin0
            assert txn1.origin == origin0
            assert len(doc0._origins) == 1
            assert list(doc0._origins.values())[0] == origin0
            assert doc0._origins == doc1._origins
        assert len(doc0._origins) == 1
        assert list(doc0._origins.values())[0] == origin0
        assert len(doc1._origins) == 0
    assert len(doc0._origins) == 0
    assert len(doc1._origins) == 0

    with doc0.transaction(origin=123):
        with doc0.transaction(origin=123):
            with doc0.transaction():
                with pytest.raises(RuntimeError) as excinfo:
                    with doc0.transaction(origin=456):
                        pass  # pragma: no cover

    assert str(excinfo.value) == "Nested transactions must have same origin as root transaction"


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
