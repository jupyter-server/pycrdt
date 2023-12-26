from pycrdt import Array, Doc, Map, Text


def test_callback_transaction():
    text = Text()
    array = Array()
    map_ = Map()
    Doc(
        {
            "text": text,
            "array": array,
            "map": map_,
        }
    )
    events = []

    def callback(event):
        events.append(str(event.target))

    text.observe(callback)
    array.observe(callback)
    map_.observe(callback)
    with text.doc.transaction():
        text += "hello"
        text += " world"
    array.append(1)
    map_["foo"] = "bar"
    assert events == ["hello world", "[1.0]", '{"foo":"bar"}']
