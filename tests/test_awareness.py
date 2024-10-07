import json
from copy import deepcopy
from uuid import uuid4

from pycrdt import Awareness, Doc, write_var_uint

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


def test_awareness_get_local_state():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    assert awareness.get_local_state() == {}


def test_awareness_set_local_state_field():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    awareness.set_local_state_field("new_field", "new_value")
    assert awareness.get_local_state() == {"new_field": "new_value"}


def test_awareness_add_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    changes = awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER),
        "custom_origin",
    )
    assert changes == {
        "changes": {
            "added": [REMOTE_CLIENT_ID],
            "updated": [],
            "filtered_updated": [],
            "removed": [],
        },
        "origin": "custom_origin",
    }
    assert awareness.states == {
        REMOTE_CLIENT_ID: REMOTE_USER,
    }


def test_awareness_update_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    # Add a remote user.
    awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER),
        "custom_origin",
    )

    # Update it
    remote_user = deepcopy(REMOTE_USER)
    remote_user["user"]["name"] = "New user name"
    changes = awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, remote_user, 2),
        "custom_origin",
    )

    assert changes == {
        "changes": {
            "added": [],
            "updated": [REMOTE_CLIENT_ID],
            "filtered_updated": [REMOTE_CLIENT_ID],
            "removed": [],
        },
        "origin": "custom_origin",
    }
    assert awareness.states == {
        REMOTE_CLIENT_ID: remote_user,
    }


def test_awareness_remove_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    # Add a remote user.
    awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER),
        "custom_origin",
    )

    # Remove it
    changes = awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, "null", 2),
        "custom_origin",
    )

    assert changes == {
        "changes": {
            "added": [],
            "updated": [],
            "filtered_updated": [],
            "removed": [REMOTE_CLIENT_ID],
        },
        "origin": "custom_origin",
    }
    assert awareness.states == {}


def test_awareness_do_not_increment_clock():
    ydoc = Doc()
    awareness = Awareness(ydoc)
    changes = awareness.apply_awareness_update(
        create_bytes_message(awareness.client_id, "null"),
        "custom_origin",
    )
    assert changes == {
        "changes": {
            "added": [],
            "updated": [],
            "filtered_updated": [],
            "removed": [],
        },
        "origin": "custom_origin",
    }
    assert awareness.meta.get(awareness.client_id, {}).get("clock") == 1


def test_awareness_increment_clock():
    ydoc = Doc()
    awareness = Awareness(ydoc)
    awareness.set_local_state_field("new_field", "new_value")
    awareness.apply_awareness_update(
        create_bytes_message(awareness.client_id, "null"),
        "custom_origin",
    )
    assert awareness.meta.get(awareness.client_id, {}).get("clock") == 2


def test_awareness_observes():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    called_1 = {}
    called_2 = {}

    def callback_1(value):
        called_1.update(value)

    def callback_2(value):
        called_2.update(value)

    awareness.observe(callback_1)
    sub_2 = awareness.observe(callback_2)
    changes = awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER),
        "custom_origin",
    )
    assert called_1 == changes
    assert called_2 == changes

    keys = list(called_1.keys())
    for k in keys:
        del called_1[k]

    keys = list(called_2.keys())
    for k in keys:
        del called_2[k]

    awareness.unobserve(sub_2)
    changes = awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, "null"),
        "custom_origin",
    )
    assert called_1 == changes
    assert called_2 != changes
    assert called_2 == {}


def test_awareness_observes_local_change():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    called_1 = {}

    def callback_1(value):
        called_1.update(value)

    awareness.observe(callback_1)
    changes = awareness.set_local_state_field("new_field", "new_value")
    assert changes["origin"] == "local"
    assert called_1 == changes


def test_awareness_encode():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    changes = awareness.set_local_state_field("new_field", "new_value")
    states_bytes = awareness.encode_awareness_update(changes["changes"]["added"])
    assert states_bytes[1:] == create_bytes_message(
        awareness.client_id, awareness.get_local_state()
    )


def test_awareness_encode_wrong_id():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    states_bytes = awareness.encode_awareness_update([10])
    assert states_bytes is None


def test_awareness_deprecated_add_user():
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
        REMOTE_CLIENT_ID: REMOTE_USER,
    }


def test_awareness_deprecated_update_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    # Add a remote user.
    awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER),
        "custom_origin",
    )

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
        REMOTE_CLIENT_ID: remote_user,
    }


def test_awareness_deprecated_remove_user():
    ydoc = Doc()
    awareness = Awareness(ydoc)

    # Add a remote user.
    awareness.apply_awareness_update(
        create_bytes_message(REMOTE_CLIENT_ID, REMOTE_USER),
        "custom_origin",
    )

    # Remove it
    changes = awareness.get_changes(create_bytes_message(REMOTE_CLIENT_ID, "null", 2))

    assert changes == {
        "added": [],
        "updated": [],
        "filtered_updated": [],
        "removed": [REMOTE_CLIENT_ID],
        "states": [],
    }
    assert awareness.states == {}
