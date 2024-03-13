import json
from functools import partial

import pytest
from pycrdt import Array, Doc, Map, Text


def callback(events, event):
    events.append(event)


def callback_deep(_events, events):
    _events.append(events)


def test_binary_entry():
    doc = Doc({"m": Map({"bytes": b"012"})})
    assert doc["m"]["bytes"] == b"012"


def test_str():
    doc = Doc()
    map2 = Map({"key2": "val2"})
    array1 = Array([0, 1, map2])
    map0 = Map({"key1": array1})
    doc["map"] = map0
    assert str(map0) == '{"key1":[0.0,1.0,{"key2":"val2"}]}'


def test_nested():
    doc = Doc()
    text1 = Text("my_text")
    array1 = Array([0, "foo", 2])
    map1 = Map({"foo": [3, 4, 5], "bar": "baz"})
    map0 = Map({"text1": text1, "array1": array1, "map1": map1})
    doc["map"] = map0
    ref = {
        "text1": "my_text",
        "array1": [0, "foo", 2],
        "map1": {"bar": "baz", "foo": [3, 4, 5]},
    }
    assert json.loads(str(map0)) == ref


def test_api():
    doc = Doc()
    n = 5
    keys = [f"key{i}" for i in range(n)]
    values = [f"value{i}" for i in range(n)]
    items = {keys[i]: values[i] for i in range(n)}
    map0 = Map(items)
    doc["map0"] = map0
    with pytest.raises(RuntimeError) as excinfo:
        map0[1] = 2
    assert str(excinfo.value) == "Key must be of type string"
    key_list = list(map0.keys())
    value_list = list(map0.values())
    assert len(key_list) == n
    assert len(value_list) == n
    # Yrs Map doesn't keep order
    assert set([key for key in map0]) == set(keys)
    assert set(key_list) == set(keys)
    assert set(value_list) == set(values)
    assert dict(map0.items()) == items
    assert "key0" in map0
    assert "key5" not in map0
    assert map0.get("key1") == "value1"
    assert map0.get("key5") is None
    assert map0.get("key5", "value5") == "value5"
    assert map0.pop("key0") == "value0"
    assert "key0" not in map0
    with pytest.raises(KeyError) as excinfo:
        del map0["key0"]
    assert str(excinfo.value) == "'key0'"
    with pytest.raises(KeyError) as excinfo:
        map0.pop("key5")
    assert map0.pop("key5", "value5") == "value5"
    with pytest.raises(RuntimeError) as excinfo:
        del map0[0]
    assert str(excinfo.value) == "Key must be of type string"
    map0.clear()
    assert len(map0) == 0

    # pop
    doc = Doc()
    map0 = Map({"foo": 1, "bar": 2})
    doc["map0"] = map0
    v = map0.pop("foo")
    assert v == 1
    assert str(map0) == '{"bar":2.0}'
    v = map0.pop("bar")
    assert v == 2
    assert str(map0) == "{}"


def test_to_py():
    doc = Doc()
    submap = Map({"foo": "bar"})
    subarray = Array([0, submap])
    doc["map_"] = map_ = Map({"key0": "val0", "key1": subarray})
    assert map_.to_py() == {"key0": "val0", "key1": [0, {"foo": "bar"}]}


def test_prelim():
    map0 = Map({"0": 1})
    assert map0.to_py() == {"0": 1}

    map1 = Map()
    assert map1.to_py() is None


def test_observe():
    doc = Doc()
    doc["map0"] = map0 = Map()
    doc["map1"] = map1 = Map()
    events = []

    sub = map0.observe(partial(callback, events))
    print(f"{sub=}")
    map0["0"] = 0
    assert (
        str(events[0])
        == """{target: {"0":0.0}, keys: {'0': {'action': 'add', 'newValue': 0.0}}, path: []}"""
    )
    events.clear()
    map0.unobserve(sub)
    map0["1"] = 1
    assert events == []

    deep_events = []
    sub = map1.observe_deep(partial(callback_deep, deep_events))
    map1["1"] = 1
    assert (
        str(deep_events[0][0])
        == """{target: {"1":1.0}, keys: {'1': {'action': 'add', 'newValue': 1.0}}, path: []}"""
    )
    deep_events.clear()
    map1.unobserve(sub)
    map1["0"] = 0
    assert deep_events == []
