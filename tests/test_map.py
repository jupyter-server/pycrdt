from functools import partial

from pycrdt import Array, Doc, Map, Text
from yaml import CLoader as Loader
from yaml import load

json_loads = partial(load, Loader=Loader)


def test_nested():
    doc = Doc()
    map0 = doc.get_map("map")
    text1 = Text(prelim="my_text")
    array1 = Array(prelim=[0, "foo", 2])
    map1 = Map(prelim={"foo": [3, 4, 5], "bar": "baz"})
    map0.init({"text1": text1, "array1": array1, "map1": map1})
    ref = {
        "text1": "my_text",
        "array1": [0, "foo", 2],
        "map1": {"bar": "baz", "foo": [3, 4, 5]},
    }
    with doc.transaction():
        assert json_loads(str(map0)) == ref
