from pycrdt import Doc, Text

hello = "Hello"
world = ", World"
punct = "!"


def test_str():
    doc = Doc()
    text = Text()
    doc["text"] = text
    with doc.transaction():
        text += hello
        with doc.transaction():
            text += world
        text += punct

    assert str(text) == hello + world + punct
