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
        target = event.target
        doc = target.doc
        with doc.transaction():
            events.append(target.to_py())
            with doc.transaction():
                events.append(str(target))

    text.observe(callback)
    array.observe(callback)
    map_.observe(callback)
    with text.doc.transaction():
        text += "hello"
        text += " world"
    array.append(1)
    map_["foo"] = "bar"
    assert events == [
        "hello world",
        "hello world",
        [1.0],
        "[1.0]",
        {"foo": "bar"},
        '{"foo":"bar"}',
    ]
