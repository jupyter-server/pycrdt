import json

from dirty_equals import IsStr
from pycrdt import Awareness, Doc, write_var_uint

DEFAULT_USER = {"username": IsStr(), "name": "Jupyter server"}

TEST_CLIENT_ID = 853790970
TEST_USER = {
    "user": {
        "username": "2460ab00fd28415b87e49ec5aa2d482d",
        "name": "Anonymous Ersa",
        "display_name": "Anonymous Ersa",
        "initials": "AE",
        "avatar_url": None,
        "color": "var(--jp-collaborator-color7)",
    }
}


def create_bytes_message(client_id: int, user: dict[str, dict[str, str | None]]) -> bytes:
    new_user_bytes = json.dumps(user, separators=(",", ":")).encode("utf-8")
    msg = write_var_uint(len(new_user_bytes)) + new_user_bytes
    msg = write_var_uint(1) + msg
    msg = write_var_uint(client_id) + msg
    msg = write_var_uint(1) + msg
    msg = write_var_uint(len(msg)) + msg
    return msg


def test_awareness_default_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    assert awareness.user == DEFAULT_USER


def test_awareness_set_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)
    user = {"username": "test_username", "name": "test_name"}
    awareness.user = user
    assert awareness.user == user


def test_awareness_get_local_state():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    assert awareness.get_local_state() == {"user": DEFAULT_USER}


def test_awareness_set_local_state_field():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    awareness.set_local_state_field("new_field", "new_value")
    assert awareness.get_local_state() == {"user": DEFAULT_USER, "new_field": "new_value"}


def test_awareness_get_changes():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    changes = awareness.get_changes(create_bytes_message(TEST_CLIENT_ID, TEST_USER))
    assert changes == {
        "added": [TEST_CLIENT_ID],
        "updated": [],
        "filtered_updated": [],
        "removed": [],
        "states": [TEST_USER],
    }
    assert awareness.states == {
        awareness.client_id: {"user": DEFAULT_USER},
        TEST_CLIENT_ID: TEST_USER,
    }


def test_awareness_observes():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    called = {}

    def callback(value):
        called.update(value)

    awareness.observe(callback)

    changes = awareness.get_changes(create_bytes_message(TEST_CLIENT_ID, TEST_USER))

    assert called == changes


def test_awareness_on_change():
    ydoc = Doc()

    changes = []

    def callback(value):
        changes.append(value)

    awareness = Awareness(ydoc, on_change=callback)

    awareness.set_local_state_field("new_field", "new_value")

    assert len(changes) == 1

    assert type(changes[0]) is bytes
