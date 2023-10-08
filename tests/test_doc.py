from functools import partial

from pycrdt import Array, Doc, Map, Text


def callback(events, event):
    events.append(event)


def test_subdoc():
    doc0 = Doc()
    state0 = doc0.get_state()
    map0 = Map()
    doc0["map0"] = map0

    doc1 = Doc()
    state1 = doc1.get_state()
    map1 = Map()
    doc1["map1"] = map1

    doc2 = Doc()
    state2 = doc2.get_state()
    array2 = Array()
    doc2["array2"] = array2

    doc0["array0"] = Array(["hello", 1, doc1])
    map0.update({"key0": "val0", "key1": doc2})

    update0 = doc0.get_update(state0)

    remote_doc = Doc()
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

    update1 = doc1.get_update(state1)

    array2 += ["baz", 3]

    update2 = doc2.get_update(state2)

    remote_doc1.apply_update(update1)
    remote_doc2.apply_update(update2)

    assert str(map1) == str(remote_map1)
    assert str(array2) == str(remote_array2)


def test_transaction_event():
    doc = Doc()
    events = []
    doc.observe(partial(callback, events))
    text = Text("Hello, World!")
    doc["text"] = text

    remote_doc = Doc()
    for event in events:
        update = event.get_update()
        remote_doc.apply_update(update)

    remote_text = Text()
    remote_doc["text"] = remote_text
    assert str(remote_text) == "Hello, World!"
