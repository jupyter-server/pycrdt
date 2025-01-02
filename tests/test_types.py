from typing import TypedDict

import pytest
from pycrdt import Array, Doc, Map


@pytest.mark.mypy_testing
def mypy_test_array():
    doc = Doc()
    array0: Array[int] = doc.get("array0", type=Array)
    array0.append(0)
    array0.append("foo")  # E: Argument 1 to "append" of "Array" has incompatible type "str"; expected "int"  [arg-type]


@pytest.mark.mypy_testing
def mypy_test_uniform_map():
    doc = Doc()
    map0: Map[bool] = doc.get("map0", type=Map)
    map0["foo"] = True
    map0["foo"] = "bar"  # E: Incompatible types in assignment (expression has type "str", target has type "bool")
    v0: str = map0.pop("foo")  # E: Incompatible types in assignment (expression has type "bool", variable has type "str")
    v1: bool = map0.pop("foo")


@pytest.mark.mypy_testing
def mypy_test_typed_map():
    doc = Doc()

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
