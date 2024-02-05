from functools import partial

import pytest
from pycrdt import Array, Doc, Map, Text


def callback(events, event):
    events.append(event)


def encode_client_id(client_id_bytes):
    client_id_len = len(client_id_bytes)
    b = []
    for i, n in enumerate(client_id_bytes[::-1]):
        j = n << i
        if i != client_id_len - 1:
            j |= 0x80
        b.append(j)
    return bytes(b)


def test_api():
    doc = Doc()

    with pytest.raises(RuntimeError) as excinfo:
        doc[0] = Array()
    assert str(excinfo.value) == "Key must be of type string"

    doc["a0"] = a0 = Array()
    doc["m0"] = m0 = Map()
    doc["t0"] = t0 = Text()
    assert set((key for key in doc)) == set(("a0", "m0", "t0"))
    assert set([type(value) for value in doc.values()]) == set(
        [type(value) for value in (a0, m0, t0)]
    )
    assert set([(key, type(value)) for key, value in doc.items()]) == set(
        [(key, type(value)) for key, value in (("a0", a0), ("m0", m0), ("t0", t0))]
    )


def test_subdoc():
    doc0 = Doc()
    map0 = Map()
    doc0["map0"] = map0

    doc1 = Doc()
    map1 = Map()
    doc1["map1"] = map1

    doc2 = Doc()
    array2 = Array()
    doc2["array2"] = array2

    doc0["array0"] = Array(["hello", 1, doc1])
    map0.update({"key0": "val0", "key1": doc2})

    update0 = doc0.get_update()

    remote_doc = Doc()
    events = []
    remote_doc.observe_subdocs(partial(callback, events))
    remote_doc.apply_update(update0)
    remote_array0 = Array()
    remote_map0 = Map()
    remote_doc["array0"] = remote_array0
    remote_doc["map0"] = remote_map0

    remote_doc1 = remote_array0[2]
    remote_doc2 = remote_map0["key1"]

    remote_map1 = Map()
    remote_array2 = Array()
    remote_doc1["map1"] = remote_map1
    remote_doc2["array2"] = remote_array2

    map1["foo"] = "bar"

    update1 = doc1.get_update()

    array2 += ["baz", 3]

    update2 = doc2.get_update()

    remote_doc1.apply_update(update1)
    remote_doc2.apply_update(update2)

    assert str(map1) == str(remote_map1)
    assert str(array2) == str(remote_array2)

    assert len(events) == 1
    event = events[0]
    assert len(event.added) == 2
    assert event.added[0] in (doc1.guid, doc2.guid)
    assert event.added[1] in (doc1.guid, doc2.guid)
    assert doc1.guid != doc2.guid
    assert event.removed == []
    assert event.loaded == []


def test_doc_in_event():
    doc = Doc()
    doc["array"] = array = Array()
    events = []
    array.observe(partial(callback, events))
    array.append(Doc())
    assert isinstance(events[0].delta[0]["insert"][0], Doc)


def test_transaction_event():
    doc = Doc()
    events = []
    doc.observe(partial(callback, events))
    text = Text("Hello, World!")
    doc["text"] = text

    remote_doc = Doc()
    for event in events:
        remote_doc.apply_update(event.update)

    remote_text = Text()
    remote_doc["text"] = remote_text
    assert str(remote_text) == "Hello, World!"


def test_client_id():
    doc0 = Doc()
    doc1 = Doc()
    assert doc0.client_id != doc1.client_id

    client_id_bytes = b"\x01\x02\x03\x04"
    client_id = int.from_bytes(client_id_bytes, byteorder="big")
    doc2 = Doc(client_id=client_id)
    assert doc2.client_id == client_id
    text = Text("Hello, World!")
    doc2["text"] = text
    update = doc2.get_update()

    b = encode_client_id(client_id_bytes)

    assert update[2 : 2 + len(b)] == b


def test_roots():
    remote_doc = Doc(
        {
            "a": Text("foo"),
            "b": Array([5, 2, 8]),
            "c": Map({"k1": 1, "k2": 2}),
        }
    )
    roots = dict(remote_doc)
    assert str(roots["a"]) == "foo"
    assert list(roots["b"]) == [5, 2, 8]
    assert dict(roots["c"]) == {"k1": 1, "k2": 2}

    local_doc = Doc()
    update = remote_doc.get_update()
    local_doc.apply_update(update)
    roots = dict(local_doc)
    assert roots["a"] is None
    assert roots["b"] is None
    assert roots["c"] is None
    # assert str(roots["a"]) == "foo"
    # assert list(roots["b"]) == [5, 2, 8]
    # assert dict(roots["c"]) == None  # {"k1": 1, "k2": 2}
