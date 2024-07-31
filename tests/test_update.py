from pycrdt import Doc, Text, Update


def test_alternative_update():
    data1 = Text("hello")
    doc1 = Doc()
    doc1["data"] = data1

    data2 = Text("world")
    doc2 = Doc()
    doc2["data"] = data2

    current_state1 = doc1.get_update()
    current_state2 = doc2.get_update()

    del doc1
    del doc2
    state_vector1 = Update.encode_state_vector_from_update(current_state1)
    state_vector2 = Update.encode_state_vector_from_update(current_state2)

    diff1 = Update.diff_update(current_state1, state_vector2)
    diff2 = Update.diff_update(current_state2, state_vector1)

    # sync clients
    current_state1 = Update.merge_update([current_state1, diff2])
    current_state2 = Update.merge_update([current_state2, diff1])
    assert current_state1 == current_state2

    doc1 = Doc()
    data1 = doc1.get("data", type=Text)
    doc1.apply_update(current_state1)
    doc2 = Doc()
    data2 = doc2.get("data", type=Text)
    doc2.apply_update(current_state2)

    assert str(doc1["data"]) == str(doc2["data"])
