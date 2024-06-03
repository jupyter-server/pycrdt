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
    undo_manager = UndoManager(data, capture_timeout_millis=0)
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
    undo_manager = UndoManager(data, capture_timeout_millis=0)
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
    undo_manager = UndoManager(data, capture_timeout_millis=0)
    val0 = {}
    val1 = {"key0": "val0"}
    val2 = {"key1": "val1"}
    val3 = dict(**val1, **val2)
    data.update(val1)
    assert data.to_py() == val1
    data.update(val2)
    assert data.to_py() == val3
    undo_redo(data, undo_manager, val0, val1, val3)
