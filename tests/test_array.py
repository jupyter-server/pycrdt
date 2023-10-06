from functools import partial

from pycrdt import Array, Doc, Map, Text
from yaml import CLoader as Loader
from yaml import load

json_loads = partial(load, Loader=Loader)


def callback(events, event):
    events.append(
        dict(
            delta=event.delta,
            path=event.path,
        )
    )


def test_nested():
    doc = Doc()
    array0 = Array(name="array", doc=doc)
    text1 = Text(prelim="my_text1")
    array1 = Array(prelim=[0, "foo", 2])
    text2 = Text(prelim="my_text2")
    map1 = Map(prelim={"foo": [3, 4, 5], "bar": "hello", "baz": text2})
    array0.init([text1, array1, map1])
    ref = [
        "my_text1",
        [0, "foo", 2],
        {"bar": "hello", "foo": [3, 4, 5], "baz": "my_text2"},
    ]
    with doc.transaction():
        assert json_loads(str(array0)) == ref
        assert isinstance(array0[2], Map)
        assert isinstance(array0[2]["baz"], Text)


def test_array():
    doc = Doc()
    array = doc.get_array("array")
    events = []

    array.observe(partial(callback, events))
    ref = [
        -1,
        -2,
        "foo",
        10,
        11,
        12,
        3.1,
        False,
        [4, 5.2],
        {"foo": 3, "bar": True, "baz": [6, 7]},
        -3,
        -4,
        -5,
    ]
    with doc.transaction():
        array.append("foo")
        array.append(1)
        array.append(2)
        array.append(3)
        array.append(3.1)
        array.append(False)
        array.append([4, 5.2])
        array.append({"foo": 3, "bar": True, "baz": [6, 7]})
        del array[1]
        del array[1:3]
        array[1:1] = [10, 11, 12]
        array = [-1, -2] + array
        array = array + [-3, -4]
        array += [-5]
        assert json_loads(str(array)) == ref
        assert len(array) == len(ref)
        assert array[9] == ref[9]

    assert events == [
        {
            "delta": [
                {
                    "insert": [
                        -1,
                        -2,
                        "foo",
                        10,
                        11,
                        12,
                        3.1,
                        False,
                        [4, 5.2],
                        {"bar": True, "foo": 3, "baz": [6, 7]},
                        -3,
                        -4,
                        -5,
                    ]
                }
            ],
            "path": [],
        }
    ]
