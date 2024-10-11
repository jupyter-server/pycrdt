import pytest
from pycrdt import Doc, XmlFragment, XmlText, XmlElement

def test_plain_text():
    doc1 = Doc()
    frag = XmlFragment()
    doc1["test"] = frag
    with doc1.transaction():
        frag.children.append("Hello")
        with doc1.transaction():
            frag.children.append(", World")
        frag.children.append("!")

    assert str(frag) == "Hello, World!"

def test_api():
    doc = Doc()
    frag = XmlFragment([
        XmlText("Hello "),
        XmlElement("em", {"class": "bold"}, [XmlText("World")]),
        XmlText("!"),
    ])

    with pytest.raises(RuntimeError) as excinfo:
        frag.integrated
    assert str(excinfo.value) == "Not integrated in a document yet"

    with pytest.raises(RuntimeError) as excinfo:
        frag.doc
    assert str(excinfo.value) == "Not integrated in a document yet"

    doc["test"] = frag
    assert str(frag) == "Hello <em class=\"bold\">World</em>!"
    assert len(frag.children) == 3
    assert str(frag.children[0]) == "Hello "
    assert str(frag.children[1]) == "<em class=\"bold\">World</em>"
    assert str(frag.children[2]) == "!"
    assert list(frag.children) == [frag.children[0], frag.children[1], frag.children[2]]

    frag.children.insert(1, XmlElement("strong", None, ["wonderful"]))
    frag.children.insert(2, " ")
    assert str(frag) == "Hello <strong>wonderful</strong> <em class=\"bold\">World</em>!"
    assert len(frag.children) == 5

    el = frag.children[3]
    assert el.tag == "em"
    assert len(el.attributes) == 1
    assert el.attributes.get("class") == "bold"
    assert el.attributes["class"] == "bold"
    assert "class" in el.attributes
    assert el.attributes.get("non-existent") is None
    assert "non-existent" not in el.attributes
    with pytest.raises(KeyError):
        el.attributes["non-existent"]
    assert list(el.attributes) == [("class", "bold")]

    del frag.children[2]
    del frag.children[1]
    assert str(frag) == "Hello <em class=\"bold\">World</em>!"


def test_observe():
    doc = Doc()
    doc["test"] = fragment = XmlFragment(["Hello world!"])
    events = []

    def callback(event):
        nonlocal fragment
        with pytest.raises(RuntimeError) as excinfo:
            fragment.children.append("text")
        assert (
            str(excinfo.value)
            == "Read-only transaction cannot be used to modify document structure"
        )
        events.append(event)

    sub = fragment.observe_deep(callback) # noqa: F841

    fragment.children.append(XmlElement("em", None, ["This is a test"]))
    assert len(events) == 1
    assert len(events[0]) == 1
    assert events[0][0].children_changed == True
    assert str(events[0][0].target) == "Hello world!<em>This is a test</em>"
    assert events[0][0].path == []
    assert len(events[0][0].delta) == 2
    assert events[0][0].delta[0]["retain"] == 1
    assert str(events[0][0].delta[1]["insert"][0]) == "<em>This is a test</em>"

    events.clear()
    fragment.children[0].format(1, 3, {"bold": True})

    assert len(events) == 1
    assert len(events[0]) == 1
    assert str(events[0][0].target) == "H<bold>el</bold>lo world!"
    assert events[0][0].delta[0] == {"retain": 1}
    assert events[0][0].delta[1] == {"retain": 2, "attributes": {"bold": True}}
