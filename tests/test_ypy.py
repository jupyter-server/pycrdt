import y_py as Y
from pycrdt import Doc


def test_text():
    doc = Doc()
    ypy_doc = Y.YDoc()

    # add text
    hello = "Hello"
    world = ", World"
    punct = "!"
    prev_state = doc.get_state()
    text = doc.get_text("text")
    with doc.transaction():
        text += hello
        with doc.transaction():
            text += world
        text += punct
    update = doc.get_update(prev_state)
    Y.apply_update(ypy_doc, update)
    remote_text = ypy_doc.get_text("text")
    assert str(remote_text) == hello + world + punct

    # del text
    prev_state = doc.get_state()
    with doc.transaction():
        del text[len(hello) :]
    update = doc.get_update(prev_state)
    Y.apply_update(ypy_doc, update)
    assert str(remote_text) == hello
