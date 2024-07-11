import gc
from threading import Thread

import pytest
from pycrdt import Doc, Text


def test_multi_threading():
    doc = Doc()
    doc["text"] = text = Text()
    message = "Hello from thread!"

    def add_text(text, message):
        text += "Hello from thread!"

    thread = Thread(target=add_text, args=(text, message))
    thread.start()
    thread.join()
    assert str(text) == message

    def drop():
        nonlocal text, doc
        del text
        del doc
        gc.collect()

    thread = Thread(target=drop)
    thread.start()
    thread.join()

    with pytest.raises(UnboundLocalError):
        text

    with pytest.raises(UnboundLocalError):
        doc
