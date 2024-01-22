from pycrdt import Array, Doc, Map, Text

hello = "Hello"
world = ", World"
sir = " Sir"
punct = "!"


def test_str():
    doc1 = Doc()
    text1 = Text()
    doc1["text"] = text1
    with doc1.transaction():
        text1 += hello
        with doc1.transaction():
            text1 += world
        text1 += punct

    assert str(text1) == hello + world + punct

    doc2 = Doc()
    array2 = Array()
    doc2["array"] = array2
    text2 = Text("val")
    map2 = Map({"key": text2})
    array2.append(map2)
    assert str(array2) == '[{"key":"val"}]'


def test_api():
    doc = Doc()
    text = Text(hello + punct)
    doc["text"] = text
    assert str(text) == hello + punct
    text.insert(len(hello), world)
    assert str(text) == hello + world + punct
    text.clear()
    assert len(text) == 0
    text[:] = hello + world + punct
    assert str(text) == hello + world + punct
    text[len(hello) : len(hello) + len(world)] = sir
    assert str(text) == hello + sir + punct
    # single character replacement
    text[len(text) - 1] = "?"
    assert str(text) == hello + sir + "?"
    # deletion with only an index
    del text[len(text) - 1]
    assert str(text) == hello + sir
    # deletion of an arbitrary range
    del text[len(hello) : len(hello) + len(sir)]
    assert str(text) == hello
    # deletion with start index == range length
    text += str(text)
    del text[len(hello) : 2 * len(hello)]
    assert str(text) == hello
    # deletion with a range of 0
    del text[len(hello) : len(hello)]
    assert str(text) == hello


def test_to_py():
    doc = Doc()
    doc["text"] = text = Text(hello)
    assert text.to_py() == hello
