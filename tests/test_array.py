import json
from functools import partial

import pytest
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
    assert str(array0) == '[0,1,null,{"foo":[2,3,{"key":"val"}]}]'


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

    sub = array.observe(partial(callback, events))
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
        -7,
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
        array.extend([-7])

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

    array.clear()
    assert array.to_py() == []

    events.clear()
    array.unobserve(sub)
    array.append("foo")
    assert events == []


def test_observe():
    doc = Doc()
    array = Array()
    doc["array"] = array

    sub0 = array.observe(lambda x: x)  # noqa: F841
    sub1 = array.observe(lambda x: x)  # noqa: F841
    sub2 = array.observe_deep(lambda x: x)  # noqa: F841
    sub3 = array.observe_deep(lambda x: x)  # noqa: F841

    deep_events = []

    def cb(events):
        deep_events.append(events)

    sid4 = array.observe_deep(cb)
    array.append("bar")
    assert str(deep_events[0][0]) == """{target: ["bar"], delta: [{'insert': ['bar']}], path: []}"""
    deep_events.clear()
    array.unobserve(sid4)
    array.append("baz")
    assert deep_events == []


def test_api():
    # pop
    doc = Doc()
    array = Array([1, 2, 3])
    doc["array"] = array
    v = array.pop()
    assert v == 3
    v = array.pop(0)
    assert v == 1
    assert str(array) == "[2]"

    # pop nested
    doc = Doc()
    array = Array([])
    doc["array"] = array
    nested_doc = Doc()
    nested_doc["text"] = Text("text in subdoc")
    array.insert(0, nested_doc)
    v = array.pop()
    assert str(v["text"]) == "text in subdoc"
    assert str(array) == "[]"

    nested_text = Text("abc")
    array.insert(0, nested_text)
    v = array.pop()
    assert v == "abc"
    assert str(array) == "[]"

    nested_array = Array([4, 5, 6])
    array.insert(0, nested_array)
    v = array.pop()
    assert v == [4.0, 5.0, 6.0]
    assert str(array) == "[]"

    nested_map = Map({"x": "y"})
    array.insert(0, nested_map)
    v = array.pop()
    assert v == {"x": "y"}
    assert str(array) == "[]"

    # insert
    doc = Doc()
    array = Array([1, 2, 3])
    doc["array"] = array
    array.insert(1, 4)
    assert str(array) == "[1,4,2,3]"

    # slices
    doc = Doc()
    array = Array([i for i in range(10)])
    doc["array"] = array
    with pytest.raises(RuntimeError) as excinfo:
        array[::2] = 1
    assert str(excinfo.value) == "Step not supported"
    with pytest.raises(RuntimeError) as excinfo:
        array[1:2] = 1
    assert str(excinfo.value) == "Start and stop must be equal"
    with pytest.raises(RuntimeError) as excinfo:
        array[-1:-1] = 1
    assert str(excinfo.value) == "Index out of range"
    with pytest.raises(RuntimeError) as excinfo:
        array["a"] = 1
    assert str(excinfo.value) == "Index must be of type integer"
    with pytest.raises(RuntimeError) as excinfo:
        array.pop("a")
    assert str(excinfo.value) == "Index must be of type integer"
    with pytest.raises(IndexError) as excinfo:
        array.pop(len(array))
    assert str(excinfo.value) == "Array index out of range"
    with pytest.raises(RuntimeError) as excinfo:
        del array[::2]
    assert str(excinfo.value) == "Step not supported"
    with pytest.raises(RuntimeError) as excinfo:
        del array[-1:]
    assert str(excinfo.value) == "Negative start not supported"
    with pytest.raises(RuntimeError) as excinfo:
        del array[:-1]
    assert str(excinfo.value) == "Negative stop not supported"
    with pytest.raises(TypeError) as excinfo:
        del array["a"]
    assert str(excinfo.value) == "Array indices must be integers or slices, not str"

    assert [value for value in array] == [value for value in range(10)]
    assert 1 in array

    array = Array([0, 1, 2])
    assert array.to_py() == [0, 1, 2]

    array = Array()
    assert array.to_py() is None


def test_move():
    doc = Doc()
    doc["array"] = array = Array([1, 2, 3, 4])
    array.move(1, 3)
    assert str(array) == "[1,3,2,4]"


def test_to_py():
    doc = Doc()
    submap = Map({"foo": "bar"})
    subarray = Array([1, submap])
    doc["array"] = array = Array([0, subarray])
    assert array.to_py() == [0, [1, {"foo": "bar"}]]
