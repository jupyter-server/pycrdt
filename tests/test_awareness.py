import json
from copy import deepcopy
from uuid import uuid4

from dirty_equals import IsStr
from pycrdt import Awareness, Doc, write_var_uint

DEFAULT_USER = {"username": IsStr(), "name": "Jupyter server"}
TEST_USER = {"username": str(uuid4()), "name": "Test user"}
REMOTE_CLIENT_ID = 853790970
REMOTE_USER = {
    "user": {
        "username": "2460ab00fd28415b87e49ec5aa2d482d",
        "name": "Anonymous Ersa",
        "display_name": "Anonymous Ersa",
        "initials": "AE",
        "avatar_url": None,
        "color": "var(--jp-collaborator-color7)",
    }
}


def create_bytes_message(client_id, user, clock=1) -> bytes:
    if type(user) is str:
        new_user_bytes = user.encode("utf-8")
    else:
        new_user_bytes = json.dumps(user, separators=(",", ":")).encode("utf-8")
    msg = write_var_uint(len(new_user_bytes)) + new_user_bytes
    msg = write_var_uint(clock) + msg
    msg = write_var_uint(client_id) + msg
    msg = write_var_uint(1) + msg
    msg = write_var_uint(len(msg)) + msg
    return msg


def test_awareness_default_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    assert awareness.user == DEFAULT_USER


def test_awareness_with_user():
    ydoc = Doc()
    awareness = Awareness(ydoc, user=TEST_USER)

    assert awareness.user == TEST_USER


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


def test_awareness_add_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    changes = awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER))
    assert changes == {
        "added": [REMOTE_CLIENT_ID],
        "updated": [],
        "filtered_updated": [],
        "removed": [],
        "states": [REMOTE_USER],
    }
    assert awareness.states == {
        awareness.client_id: {"user": DEFAULT_USER},
        REMOTE_CLIENT_ID: REMOTE_USER,
    }


def test_awareness_update_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    # Add a remote user.
    awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER))

    # Update it
    remote_user = deepcopy(REMOTE_USER)
    remote_user["user"]["name"] = "New user name"
    changes = awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, remote_user, 2))

    assert changes == {
        "added": [],
        "updated": [REMOTE_CLIENT_ID],
        "filtered_updated": [REMOTE_CLIENT_ID],
        "removed": [],
        "states": [remote_user],
    }
    assert awareness.states == {
        awareness.client_id: {"user": DEFAULT_USER},
        REMOTE_CLIENT_ID: remote_user,
    }


def test_awareness_remove_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    # Add a remote user.
    awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER))

    # Remove it
    changes = awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, "null", 2))

    assert changes == {
        "added": [],
        "updated": [],
        "filtered_updated": [],
        "removed": [REMOTE_CLIENT_ID],
        "states": [],
    }
    assert awareness.states == {awareness.client_id: {"user": DEFAULT_USER}}


def test_awareness_increment_clock():
    ydoc = Doc()
    awareness = Awareness(ydoc)
    changes = awareness.get_changes(create_bytes_message(awareness.client_id, "null"))
    assert changes == {
        "added": [],
        "updated": [],
        "filtered_updated": [],
        "removed": [],
        "states": [],
    }
    assert awareness.meta.get(awareness.client_id, {}).get("clock", 0) == 2


def test_awareness_observes():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    called = {}

    def callback(value):
        called.update(value)

    awareness.observe(callback)
    changes = awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER))
    assert called == changes

    called = {}
    awareness.unobserve()
    changes = awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER))
    assert called != changes
    assert called == {}


def test_awareness_on_change():
    ydoc = Doc()

    changes = []

    def callback(value):
        changes.append(value)

    awareness = Awareness(ydoc, on_change=callback)

    awareness.set_local_state_field("new_field", "new_value")

    assert len(changes) == 1

    assert type(changes[0]) is bytes
