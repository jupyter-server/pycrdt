from pycrdt import Array, Doc, Map


def callback(events, event):
    events.append(
        dict(
            delta=event.delta,
            path=event.path,
        )
    )


def test_subdoc():
    doc0 = Doc()
    state0 = doc0.get_state()
    array0 = Array(name="array0", doc=doc0)
    map0 = Map(name="map0", doc=doc0)

    doc1 = Doc()
    state1 = doc1.get_state()
    map1 = Map(name="map1", doc=doc1)

    doc2 = Doc()
    state2 = doc2.get_state()
    array2 = Array(name="array2", doc=doc2)

    array0 += ["hello", 1, doc1]
    map0.update({"key0": "val0", "key1": doc2})

    update0 = doc0.get_update(state0)

    remote_doc = Doc()
    remote_doc.apply_update(update0)
    remote_array0 = Array(name="array0", doc=remote_doc)
    remote_map0 = Map(name="map0", doc=remote_doc)

    remote_doc1 = remote_array0[2]
    remote_doc2 = remote_map0["key1"]

    remote_map1 = Map(name="map1", doc=remote_doc1)
    remote_array2 = Array(name="array2", doc=remote_doc2)

    with doc1.transaction():
        map1["foo"] = "bar"

    update1 = doc1.get_update(state1)

    with doc2.transaction():
        array2 += ["baz", 3]

    update2 = doc2.get_update(state2)

    remote_doc1.apply_update(update1)
    remote_doc2.apply_update(update2)

    assert str(map1) == str(remote_map1)
    assert str(array2) == str(remote_array2)
