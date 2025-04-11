import gc

import pytest
from anyio import CapacityLimiter, to_thread
from pycrdt import Doc, Text

pytestmark = pytest.mark.anyio


async def test_multi_threading():
    doc = Doc()
    doc["text"] = text = Text()
    gc.collect()  # drop (write) transaction in this thread

    def add_text(text, message):
        text += message
        gc.collect()  # drop (write) transaction in the other thread

    message = "Hello from thread!"
    limiter = CapacityLimiter(1)
    await to_thread.run_sync(add_text, text, message, limiter=limiter)
    assert str(text) == message
    gc.collect()  # drop (read) transaction in this thread

    def drop():
        nonlocal text, doc
        del text
        del doc
        gc.collect()

    await to_thread.run_sync(drop, limiter=limiter)

    with pytest.raises(UnboundLocalError):
        text

    with pytest.raises(UnboundLocalError):
        doc
