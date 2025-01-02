from typing import TypedDict

import pytest
from pycrdt import Array, Doc, Map, Text


@pytest.mark.mypy_testing
def mypy_test_array():
    doc: Doc[Array] = Doc()
    array0: Array[int] = doc.get("array0", type=Array)
    array0.append(0)
    array0.append("foo")  # E: Argument 1 to "append" of "Array" has incompatible type "str"; expected "int"  [arg-type]


@pytest.mark.mypy_testing
def mypy_test_uniform_map():
    doc: Doc[Map] = Doc()
    map0: Map[bool] = doc.get("map0", type=Map)
    map0["foo"] = True
    map0["foo"] = "bar"  # E: Incompatible types in assignment (expression has type "str", target has type "bool")
    v0: str = map0.pop("foo")  # E: Incompatible types in assignment (expression has type "bool", variable has type "str")
    v1: bool = map0.pop("foo")


@pytest.mark.mypy_testing
def mypy_test_typed_map():
    doc: Doc[Map] = Doc()

    MyMap = TypedDict(
        "MyMap",
        {
            "name": str,
            "toggle": bool,
            "nested": Array[bool],
        },
    )
    map0: MyMap = doc.get("map0", type=Map)  # type: ignore[assignment]
    map0["name"] = "foo"
    map0["toggle"] = False
    map0["toggle"] = 3  # E: Value of "toggle" has incompatible type "int"; expected "bool"
    array0 = Array([1, 2, 3])
    map0["nested"] = array0  # E: Value of "nested" has incompatible type "Array[int]"; expected "Array[bool]"
    array1 = Array([False, True])
    map0["nested"] = array1
    v0: str = map0["name"]
    v1: str = map0["toggle"]  # E: Incompatible types in assignment (expression has type "bool", variable has type "str")
    v2: bool = map0["toggle"]
    map0["key0"]  # E: TypedDict "MyMap@29" has no key "key0"


@pytest.mark.mypy_testing
def mypy_test_uniform_doc():
    doc: Doc[Text] = Doc()
    doc.get("text0", type=Text)
    doc.get("array0", type=Array)  # E: Argument "type" to "get" of "Doc" has incompatible type "type[pycrdt._array.Array[Any]]"; expected "type[Text]"
    doc.get("Map0", type=Map)  # E:  Argument "type" to "get" of "Doc" has incompatible type "type[pycrdt._map.Map[Any]]"; expected "type[Text]"


@pytest.mark.mypy_testing
def mypy_test_typed_doc():
    MyMap = TypedDict(
        "MyMap",
        {
            "name": str,
            "toggle": bool,
            "nested": Array[bool],
        },
    )

    MyDoc = TypedDict(
        "MyDoc",
        {
            "text0": Text,
            "array0": Array[int],
            "map0": MyMap,
        }
    )
    doc: MyDoc = Doc()  # type: ignore[assignment]
    map0: MyMap = Map()  # type: ignore[assignment]
    doc["map0"] = map0
    doc["map0"] = Array()  # E: Value of "map0" has incompatible type "Array[Never]"; expected "MyMap@61"
    doc["text0"] = Text()
    array0: Array[bool] = Array()
    doc["array0"] = array0  # E: Value of "array0" has incompatible type "Array[bool]"; expected "Array[int]"
    doc["array0"] = Array()
