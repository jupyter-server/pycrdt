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
    array0 = Array(name="array0", doc=doc0)
    map0 = Map(name="map0", doc=doc0)

    doc1 = Doc()
    map1 = Map(name="map1", doc=doc1)

    doc2 = Doc()
    array2 = Array(name="array2", doc=doc2)

    array0.init(["hello", 1, doc1])
    map0.init({"key0": "val0", "key1": doc2})

    # events_array0 = []
    # events_map0 = []
    # array0.observe_deep(partial(callback, events_array0))
    # map0.observe_deep(partial(callback, events_map0))

    with doc0.transaction():
        doc_1 = array0[2]
        doc_2 = map0["key1"]

    map_1 = Map(name="map1", doc=doc_1)
    array_2 = Array(name="array2", doc=doc_2)

    # map_1.observe(partial(callback, events_map_1))
    # array_2.observe(partial(callback, events_array_2))

    with doc1.transaction():
        map1["foo"] = "bar"
        map1_str = str(map1)

    with doc2.transaction():
        array2 += ["baz", 3]
        array2_str = str(array2)

    with doc_1.transaction():
        map_1_str = str(map_1)

    with doc_2.transaction():
        array_2_str = str(array_2)

    assert str(map_1_str) == str(map1_str) == "{foo: bar}"
    assert str(array_2_str) == str(array2_str) == "[baz, 3]"

    # print(f"{events_map_1=}")
