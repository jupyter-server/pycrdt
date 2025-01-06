import pytest
from pycrdt import Array, Doc, Map, TypedDoc, TypedMap


def test_typed():
    class MyTypedMap0(TypedMap):
        k0: bool

    class MyTypedMap1(TypedMap):
        key0: str
        key1: int
        key2: MyTypedMap0
        key3: Array[int]

    class MySubTypedDoc(TypedDoc):
        my_typed_map: MyTypedMap1

    class MyTypedDoc(MySubTypedDoc):
        my_array: Array[bool]

    doc = Doc()
    assert MyTypedDoc(doc)._ is doc

    my_typed_doc = MyTypedDoc()
    my_typed_doc.my_typed_map.key0 = "foo"

    with pytest.raises(TypeError) as excinfo:
        my_typed_doc.my_typed_map.key0 = 3
    assert str(excinfo.value) == (
        "Incompatible types in assignment (expression has type "
        "\"<class 'str'>\", variable has type \"<class 'int'>\")"
    )

    my_typed_doc.my_typed_map.key1 = 123
    my_typed_doc.my_typed_map.key2 = MyTypedMap0()
    my_typed_doc.my_typed_map.key2.k0 = False
    my_typed_doc.my_typed_map.key3 = Array([1, 2, 3])

    with pytest.raises(AttributeError) as excinfo:
        my_typed_doc.my_typed_map.wrong_key = "foo"
    assert (
        str(excinfo.value)
        == '"<class \'test_typed.test_typed.<locals>.MyTypedMap1\'>" has no attribute "wrong_key"'
    )

    with pytest.raises(AttributeError) as excinfo:
        my_typed_doc.my_typed_map.wrong_key
    assert (
        str(excinfo.value)
        == '"<class \'test_typed.test_typed.<locals>.MyTypedMap1\'>" has no attribute "wrong_key"'
    )

    my_typed_doc.my_array.append(True)

    update = my_typed_doc._.get_update()

    my_other_doc = Doc()
    my_other_doc.apply_update(update)
    my_map = my_other_doc.get("my_typed_map", type=Map)
    assert my_map.to_py() == {
        "key0": "foo",
        "key1": 123.0,
        "key2": {"k0": False},
        "key3": [1.0, 2.0, 3.0],
    }
    my_array = my_other_doc.get("my_array", type=Array[bool])
    assert my_array.to_py() == [True]
