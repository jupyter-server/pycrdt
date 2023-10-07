import json

from pycrdt import Array, Doc, Map, Text


def test_str():
    doc = Doc()
    map0 = Map(name="map", doc=doc)
    map2 = Map(prelim={"key2": "val2"})
    array1 = Array(prelim=[0, 1, map2])
    map0.init({"key1": array1})
    assert str(map0) == '{"key1":[0,1,{"key2":"val2"}]}'


def test_nested():
    doc = Doc()
    map0 = Map(name="map", doc=doc)
    text1 = Text(prelim="my_text")
    array1 = Array(prelim=[0, "foo", 2])
    map1 = Map(prelim={"foo": [3, 4, 5], "bar": "baz"})
    map0.init({"text1": text1, "array1": array1, "map1": map1})
    ref = {
        "text1": "my_text",
        "array1": [0, "foo", 2],
        "map1": {"bar": "baz", "foo": [3, 4, 5]},
    }
    assert json.loads(str(map0)) == ref
