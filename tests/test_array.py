import json
from functools import partial

from pycrdt import Array, Doc, Map, Text


def callback(events, event):
    events.append(
        dict(
            delta=event.delta,
            path=event.path,
        )
    )


def test_str():
    doc = Doc()
    map2 = Map({"key": "val"})
    array1 = Array([2, 3, map2])
    map1 = Map({"foo": array1})
    array0 = Array([0, 1, None, map1])
    doc["array"] = array0
    assert str(array0) == '[0.0,1.0,null,{"foo":[2.0,3.0,{"key":"val"}]}]'


def test_nested():
    doc = Doc()
    text1 = Text("my_text1")
    array1 = Array([0, "foo", 2])
    text2 = Text("my_text2")
    map1 = Map({"foo": [3, 4, 5], "bar": "hello", "baz": text2})
    array0 = Array([text1, array1, map1])
    doc["array"] = array0
    ref = [
        "my_text1",
        [0, "foo", 2],
        {"bar": "hello", "foo": [3, 4, 5], "baz": "my_text2"},
    ]
    assert json.loads(str(array0)) == ref
    assert isinstance(array0[2], Map)
    assert isinstance(array0[2]["baz"], Text)


def test_array():
    doc = Doc()
    array = Array()
    doc["array"] = array
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
        -6,
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
        array[-1] = -6

    assert json.loads(str(array)) == ref
    assert len(array) == len(ref)
    assert array[9] == ref[9]
    assert array[1:10:2] == ref[1:10:2]

    assert events == [
        {
            "delta": [{"insert": ref}],
            "path": [],
        }
    ]


def test_observe():
    doc = Doc()
    array = Array()
    doc["array"] = array

    def callback(e):
        pass

    sid0 = array.observe(callback)
    sid1 = array.observe(callback)
    sid2 = array.observe_deep(callback)
    sid3 = array.observe_deep(callback)
    assert sid0 == "o_0"
    assert sid1 == "o_1"
    assert sid2 == "od0"
    assert sid3 == "od1"


def test_api():
    # pop
    doc = Doc()
    array = Array([1, 2, 3])
    doc["array"] = array
    v = array.pop()
    assert v == 3
    v = array.pop(0)
    assert v == 1
    assert str(array) == "[2.0]"

    # insert
    doc = Doc()
    array = Array([1, 2, 3])
    doc["array"] = array
    array.insert(1, 4)
    assert str(array) == "[1.0,4.0,2.0,3.0]"


def test_move():
    doc = Doc()
    doc["array"] = array = Array([1, 2, 3, 4])
    array.move(1, 3)
    assert str(array) == "[1.0,3.0,2.0,4.0]"


def test_to_py():
    doc = Doc()
    submap = Map({"foo": "bar"})
    subarray = Array([1, submap])
    doc["array"] = array = Array([0, subarray])
    assert array.to_py() == [0, [1, {"foo": "bar"}]]
