from functools import partial

import y_py as Y
from pycrdt import Doc, Text

hello = "Hello"
world = ", World"
punct = "!"


def callback(events, event):
    events.append(
        dict(
            delta=event.delta,
            path=event.path,
        )
    )


def test_text():
    doc = Doc()
    ypy_doc = Y.YDoc()

    # add text
    state = doc.get_state()
    text = Text()
    doc["text"] = text
    with doc.transaction():
        text += hello
        with doc.transaction():
            text += world
        text += punct
    update = doc.get_update(state)
    Y.apply_update(ypy_doc, update)
    remote_text = ypy_doc.get_text("text")
    assert str(remote_text) == hello + world + punct

    # del text
    state = doc.get_state()
    with doc.transaction():
        del text[len(hello) :]
    update = doc.get_update(state)
    Y.apply_update(ypy_doc, update)
    assert str(remote_text) == hello


def test_observe():
    # pycrdt
    doc = Doc()
    text = Text()
    doc["text"] = text
    events = []

    subscription_id = text.observe(partial(callback, events))
    text += hello
    text += world
    text += punct
    del text[len(hello) : len(hello) + len(world)]
    text[len(hello) : len(hello)] = hello
    text.unobserve(subscription_id)
    text += punct

    # ypy
    ypy_doc = Y.YDoc()
    ypy_text = ypy_doc.get_text("text")
    ypy_events = []

    def ypy_callback(event):
        ypy_events.append(
            dict(
                delta=event.delta,
                path=event.path(),
            )
        )

    ypy_text.observe(ypy_callback)
    with ypy_doc.begin_transaction() as txn:
        ypy_text.extend(txn, hello)
    with ypy_doc.begin_transaction() as txn:
        ypy_text.extend(txn, world)
    with ypy_doc.begin_transaction() as txn:
        ypy_text.extend(txn, punct)
    with ypy_doc.begin_transaction() as txn:
        ypy_text.delete_range(txn, len(hello), len(world))
    with ypy_doc.begin_transaction() as txn:
        ypy_text.insert(txn, len(hello), hello)

    ref = [
        {"delta": [{"insert": hello}], "path": []},
        {"delta": [{"retain": len(hello)}, {"insert": world}], "path": []},
        {"delta": [{"retain": len(hello) + len(world)}, {"insert": punct}], "path": []},
        {"delta": [{"retain": len(hello)}, {"delete": len(world)}], "path": []},
        {"delta": [{"retain": len(hello)}, {"insert": hello}], "path": []},
    ]
    assert events == ypy_events == ref
