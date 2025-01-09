import pytest
from pycrdt import Array, Doc, Map, Text, UndoManager


def undo_redo(data, undo_manager, val0, val1, val3):
    assert undo_manager.can_undo()
    undone = undo_manager.undo()
    assert undone
    assert data.to_py() == val1
    assert undo_manager.can_undo()
    undone = undo_manager.undo()
    assert undone
    assert data.to_py() == val0
    assert not undo_manager.can_undo()
    undone = undo_manager.undo()
    assert not undone
    assert undo_manager.can_redo()
    redone = undo_manager.redo()
    assert redone
    assert data.to_py() == val1
    assert undo_manager.can_redo()
    redone = undo_manager.redo()
    assert redone
    assert data.to_py() == val3
    assert not undo_manager.can_redo()
    redone = undo_manager.redo()
    assert not redone
    assert undo_manager.can_undo()
    undo_manager.clear()
    assert not undo_manager.can_undo()


def test_text_undo():
    doc = Doc()
    doc["data"] = data = Text()
    undo_manager = UndoManager(scopes=[data], capture_timeout_millis=0)
    val0 = ""
    val1 = "Hello"
    val2 = ", World!"
    val3 = val1 + val2
    data += val1
    assert data.to_py() == val1
    data += val2
    assert data.to_py() == val3
    undo_redo(data, undo_manager, val0, val1, val3)


def test_array_undo():
    doc = Doc()
    doc["data"] = data = Array()
    undo_manager = UndoManager(scopes=[data], capture_timeout_millis=0)
    val0 = []
    val1 = ["foo"]
    val2 = ["bar"]
    val3 = val1 + val2
    data += val1
    assert data.to_py() == val1
    data += val2
    assert data.to_py() == val3
    undo_redo(data, undo_manager, val0, val1, val3)


def test_map_undo():
    doc = Doc()
    doc["data"] = data = Map()
    undo_manager = UndoManager(scopes=[data], capture_timeout_millis=0)
    val0 = {}
    val1 = {"key0": "val0"}
    val2 = {"key1": "val1"}
    val3 = dict(**val1, **val2)
    data.update(val1)
    assert data.to_py() == val1
    data.update(val2)
    assert data.to_py() == val3
    undo_redo(data, undo_manager, val0, val1, val3)


def test_scopes():
    doc = Doc()
    doc["text"] = text = Text()
    doc["array"] = array = Array()
    doc["map"] = map = Map()
    undo_manager = UndoManager(scopes=[text], capture_timeout_millis=0)

    text += "Hello"
    text += ", World!"
    assert str(text) == "Hello, World!"
    undo_manager.undo()
    assert str(text) == "Hello"

    array.append(0)
    assert array.to_py() == [0]
    undo_manager.undo()
    assert array.to_py() == [0]
    undo_manager.expand_scope(array)
    array.append(1)
    assert array.to_py() == [0, 1]
    undo_manager.undo()
    assert array.to_py() == [0]

    map["key0"] = "val0"
    assert map.to_py() == {"key0": "val0"}
    undo_manager.undo()
    assert map.to_py() == {"key0": "val0"}
    undo_manager.expand_scope(map)
    map["key1"] = "val1"
    assert map.to_py() == {"key0": "val0", "key1": "val1"}
    undo_manager.undo()
    assert map.to_py() == {"key0": "val0"}


def test_wrong_creation():
    with pytest.raises(RuntimeError) as excinfo:
        UndoManager()
    assert str(excinfo.value) == "UndoManager must be created with doc or scopes"

    doc = Doc()
    doc["text"] = text = Text()
    with pytest.raises(RuntimeError) as excinfo:
        UndoManager(doc=doc, scopes=[text])
    assert str(excinfo.value) == "UndoManager must be created with doc or scopes"


def test_undo_redo_stacks():
    doc = Doc()
    doc["text"] = text = Text()
    undo_manager = UndoManager(scopes=[text], capture_timeout_millis=0)
    assert len(undo_manager.undo_stack) == 0
    assert len(undo_manager.redo_stack) == 0
    text += "Hello"
    assert len(undo_manager.undo_stack) == 1
    assert len(undo_manager.redo_stack) == 0
    text += ", World!"
    assert len(undo_manager.undo_stack) == 2
    assert len(undo_manager.redo_stack) == 0
    undo_manager.undo()
    assert len(undo_manager.undo_stack) == 1
    assert len(undo_manager.redo_stack) == 1
    undo_manager.undo()
    assert len(undo_manager.undo_stack) == 0
    assert len(undo_manager.redo_stack) == 2


def test_origin():
    doc = Doc()
    doc["text"] = text = Text()
    undo_manager = UndoManager(scopes=[text], capture_timeout_millis=0)

    class Origin:
        pass

    origin = Origin()
    undo_manager.include_origin(origin)
    text += "Hello"
    assert not undo_manager.can_undo()
    with doc.transaction(origin=origin):
        text += ", World!"
    assert str(text) == "Hello, World!"
    assert undo_manager.can_undo()
    undo_manager.undo()
    assert str(text) == "Hello"
    assert not undo_manager.can_undo()
    undo_manager.exclude_origin(origin)
    text += ", World!"
    assert str(text) == "Hello, World!"
    assert undo_manager.can_undo()
    undo_manager.undo()
    assert str(text) == "Hello"
    assert not undo_manager.can_undo()


def test_timestamp():
    timestamp = 0
    timestamp_called = 0

    def timestamp_callback():
        nonlocal timestamp, timestamp_called
        timestamp_called += 1
        return timestamp

    doc = Doc()
    doc["text"] = text = Text()
    undo_manager = UndoManager(
        scopes=[text], capture_timeout_millis=1, timestamp=timestamp_callback
    )
    text += "a"
    timestamp += 1
    text += "b"
    text += "c"
    timestamp += 1
    undo_manager.undo()
    assert str(text) == "a"
    assert timestamp_called == 4
