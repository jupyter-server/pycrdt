import json

from pycrdt import Array, Doc, Map, Text


def test_str():
    doc = Doc()
    map2 = Map({"key2": "val2"})
    array1 = Array([0, 1, map2])
    map0 = Map({"key1": array1})
    doc["map"] = map0
    assert str(map0) == '{"key1":[0,1,{"key2":"val2"}]}'


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
    items = {keys[i]: values[i] for i in range(5)}
    map0 = Map(items)
    doc["map0"] = map0
    assert list(map0.keys()) == keys
    assert list(map0.values()) == values
    assert dict(map0.items()) == items
    map0.clear()
    assert len(map0) == 0
