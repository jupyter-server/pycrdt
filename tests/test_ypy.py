import y_py as Y
from pycrdt import Doc


def test_text():
    doc = Doc()
    text = doc.get_text("text")
    with doc.transaction():
        text.concat("Hello, World!")
    v = doc.get_state()
    doc2 = Doc()
    update = doc.get_update(doc2.get_state())

    remote_doc = Y.YDoc()
    Y.apply_update(remote_doc, update)
    remote_text = remote_doc.get_text("text")
    assert str(remote_text) == "Hello, World!"