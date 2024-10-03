import json

from dirty_equals import IsStr
from pycrdt import Awareness, Doc

DEFAULT_USER = {"username": IsStr(), "name": "Jupyter server"}


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

    new_user = {
        "user": {
            "username": "2460ab00fd28415b87e49ec5aa2d482d",
            "name": "Anonymous Ersa",
            "display_name": "Anonymous Ersa",
            "initials": "AE",
            "avatar_url": None,
            "color": "var(--jp-collaborator-color7)",
        }
    }
    new_user_bytes = json.dumps(new_user, separators=(",", ":")).encode("utf-8")
    new_user_message = b"\xc3\x01\x01\xfa\xa1\x8f\x97\x03\x03\xba\x01" + new_user_bytes
    changes = awareness.get_changes(new_user_message)
    assert changes == {
        "added": [853790970],
        "updated": [],
        "filtered_updated": [],
        "removed": [],
        "states": [new_user],
    }
    assert awareness.states == {awareness.client_id: {"user": DEFAULT_USER}, 853790970: new_user}


def test_awareness_observes():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    called = {}

    def callback(value):
        called.update(value)

    awareness.observe(callback)

    new_user = {
        "user": {
            "username": "2460ab00fd28415b87e49ec5aa2d482d",
            "name": "Anonymous Ersa",
            "display_name": "Anonymous Ersa",
            "initials": "AE",
            "avatar_url": None,
            "color": "var(--jp-collaborator-color7)",
        }
    }
    new_user_bytes = json.dumps(new_user, separators=(",", ":")).encode("utf-8")
    new_user_message = b"\xc3\x01\x01\xfa\xa1\x8f\x97\x03\x03\xba\x01" + new_user_bytes
    changes = awareness.get_changes(new_user_message)

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
