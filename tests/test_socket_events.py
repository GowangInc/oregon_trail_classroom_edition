"""Comprehensive server-side SocketIO event tests for the Oregon Trail game."""

import pytest
from datetime import date

from server import app, socketio, sessions, player_to_session, sid_to_player


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_globals():
    """Clear global server state before and after every test."""
    sessions.clear()
    player_to_session.clear()
    sid_to_player.clear()
    yield
    sessions.clear()
    player_to_session.clear()
    sid_to_player.clear()


@pytest.fixture
def host_client():
    """Create a connected host client with a fresh session."""
    client = socketio.test_client(app, auth={"is_host": True, "host_password": "admin"})
    assert client.is_connected()
    yield client
    if client.is_connected():
        client.disconnect()


def _get_session():
    """Return the single active SessionManager (tests only ever create one)."""
    assert len(sessions) == 1
    return next(iter(sessions.values()))


def _extract_player_id(client_or_messages):
    """Pull the real player_id from the most recent 'connected' event."""
    messages = client_or_messages.get_received() if hasattr(client_or_messages, "get_received") else client_or_messages
    for msg in reversed(messages):
        if msg["name"] == "connected":
            pid = msg["args"][0].get("player_id")
            if pid is not None:
                return pid
    raise RuntimeError("No connected event with player_id found")


def _extract_party_id(host_client):
    """Pull party_id from the most recent 'party_created' event."""
    for msg in reversed(host_client.get_received()):
        if msg["name"] == "party_created":
            return msg["args"][0]["party_id"]
    raise RuntimeError("No party_created event found")


def _find_received_named(client_or_messages, event_name):
    """Return the most recent message with the given event name."""
    messages = client_or_messages.get_received() if hasattr(client_or_messages, "get_received") else client_or_messages
    for msg in reversed(messages):
        if msg["name"] == event_name:
            return msg
    return None


def _setup_active_party(host_client, player_client):
    """Helper: create party, assign player, start game, begin journey."""
    player_client.emit("join_session", {"name": "Alice"})
    player_id = _extract_player_id(player_client)

    host_client.emit("create_party", {"party_name": "Test Party"})
    party_id = _extract_party_id(host_client)

    host_client.emit("assign_party", {"player_id": player_id, "party_id": party_id})
    host_client.get_received()  # drain
    player_client.get_received()  # drain

    host_client.emit("start_game")
    host_client.get_received()
    host_client.emit("begin_journey")
    host_client.get_received()

    return player_id, party_id


# ---------------------------------------------------------------------------
# 1. join_session
# ---------------------------------------------------------------------------

def test_join_session_valid(host_client):
    """A new player can join the host's active session."""
    player = socketio.test_client(app)
    player.emit("join_session", {"name": "Alice"})

    received = player.get_received()
    names = [m["name"] for m in received]

    assert "connected" in names
    assert "session_state" in names

    player_id = _extract_player_id(received)
    mgr = _get_session()
    assert player_id in mgr.session.players
    assert mgr.session.players[player_id].name == "Alice"
    assert mgr.session.players[player_id].is_host is False

    player.disconnect()


def test_join_session_duplicate_names_allowed(host_client):
    """Multiple players with the same name can join and receive unique IDs."""
    p1 = socketio.test_client(app)
    p1.emit("join_session", {"name": "Bob"})
    id1 = _extract_player_id(p1.get_received())

    p2 = socketio.test_client(app)
    p2.emit("join_session", {"name": "Bob"})
    id2 = _extract_player_id(p2.get_received())

    assert id1 != id2

    mgr = _get_session()
    assert mgr.session.players[id1].name == "Bob"
    assert mgr.session.players[id2].name == "Bob"

    p1.disconnect()
    p2.disconnect()


def test_join_session_no_active_session_error():
    """Joining when there is no active session returns an error."""
    # Ensure no sessions exist
    sessions.clear()
    player = socketio.test_client(app)
    player.emit("join_session", {"name": "Charlie"})

    msg = _find_received_named(player.get_received(), "error")
    assert msg is not None
    assert "No active game session" in msg["args"][0]["message"]
    player.disconnect()


# ---------------------------------------------------------------------------
# 2. submit_vote
# ---------------------------------------------------------------------------

def test_submit_vote_valid_and_broadcast(host_client):
    """A player can submit a valid vote and the party receives a tally broadcast."""
    player = socketio.test_client(app)
    player_id, party_id = _setup_active_party(host_client, player)

    # Trigger a vote (player is captain because they are the first member)
    player.emit("call_vote", {"party_id": party_id, "vote_type": "pace"})
    player.get_received()  # drain decision_required etc.

    mgr = _get_session()
    decision = mgr.session.parties[party_id].decision_pending
    assert decision is not None
    decision_id = decision.decision_id

    player.emit("submit_vote", {"decision_id": decision_id, "choice": "Speed up (increase pace)"})

    # Vote should be recorded
    assert player_id in decision.votes
    assert decision.votes[player_id] == "Speed up (increase pace)"

    # Player should receive vote_tally_update broadcast
    tally = _find_received_named(player, "vote_tally_update")
    assert tally is not None
    assert tally["args"][0]["decision_id"] == decision_id
    assert "votes" in tally["args"][0]

    player.disconnect()


def test_submit_vote_invalid_choice(host_client):
    """Submitting a choice not in the decision options fails and emits an error."""
    player = socketio.test_client(app)
    player_id, party_id = _setup_active_party(host_client, player)

    player.emit("call_vote", {"party_id": party_id, "vote_type": "pace"})
    player.get_received()

    mgr = _get_session()
    decision_id = mgr.session.parties[party_id].decision_pending.decision_id

    player.emit("submit_vote", {"decision_id": decision_id, "choice": "Teleport to Oregon"})

    err = _find_received_named(player, "error")
    assert err is not None
    assert "Invalid choice" in err["args"][0]["message"]

    player.disconnect()


# ---------------------------------------------------------------------------
# 3. host_override_decision
# ---------------------------------------------------------------------------

def test_host_can_override_decision(host_client):
    """The host can force-resolve a pending decision for any party."""
    player = socketio.test_client(app)
    player_id, party_id = _setup_active_party(host_client, player)

    player.emit("call_vote", {"party_id": party_id, "vote_type": "pace"})
    player.get_received()
    host_client.get_received()  # drain

    mgr = _get_session()
    assert mgr.session.parties[party_id].decision_pending is not None

    host_client.emit("host_override_decision", {"party_id": party_id, "choice": "Keep pace and rations"})

    # Host should receive updated state
    state_msg = _find_received_named(host_client, "session_state")
    assert state_msg is not None

    # Decision should now be resolved / removed
    assert mgr.session.parties[party_id].decision_pending is None

    player.disconnect()


def test_non_host_cannot_override_decision(host_client):
    """A non-host player cannot call host_override_decision."""
    player = socketio.test_client(app)
    player_id, party_id = _setup_active_party(host_client, player)

    player.emit("call_vote", {"party_id": party_id, "vote_type": "pace"})
    player.get_received()

    mgr = _get_session()
    assert mgr.session.parties[party_id].decision_pending is not None

    player.emit("host_override_decision", {"party_id": party_id, "choice": "Keep pace and rations"})

    err = _find_received_named(player, "error")
    assert err is not None
    assert "Host access required" in err["args"][0]["message"]

    player.disconnect()


# ---------------------------------------------------------------------------
# 4. inject_event
# ---------------------------------------------------------------------------

def test_host_inject_event(host_client):
    """The host can inject a trail event onto a party."""
    player = socketio.test_client(app)
    player_id, party_id = _setup_active_party(host_client, player)

    mgr = _get_session()
    wheels_before = mgr.session.parties[party_id].inventory.wagon_wheels

    host_client.emit("inject_event", {"party_id": party_id, "event_id": "broken_wheel"})

    received = host_client.get_received()

    # Global broadcast of injected event
    injected = _find_received_named(received, "host_injected_event")
    assert injected is not None
    assert injected["args"][0]["party_id"] == party_id

    # State should be broadcast
    state_msg = _find_received_named(received, "session_state")
    assert state_msg is not None

    # Event should have consumed a wheel
    assert mgr.session.parties[party_id].inventory.wagon_wheels < wheels_before

    player.disconnect()


# ---------------------------------------------------------------------------
# 5. advance_day / advance_days
# ---------------------------------------------------------------------------

def test_advance_day_advances_state_and_broadcasts(host_client):
    """advance_day ticks the engine and broadcasts results."""
    player = socketio.test_client(app)
    player_id, party_id = _setup_active_party(host_client, player)

    mgr = _get_session()
    party = mgr.session.parties[party_id]
    dist_before = party.distance_traveled
    session_date_before = mgr.session.global_date

    host_client.get_received()  # drain any prior messages
    host_client.emit("advance_day")

    received = host_client.get_received()
    names = [m["name"] for m in received]

    # Should broadcast session_state at minimum
    assert "session_state" in names

    # Party should have moved forward in space and session date should advance
    party = mgr.session.parties[party_id]
    assert party.distance_traveled > dist_before
    assert mgr.session.global_date != session_date_before

    player.disconnect()


def test_advance_days_multiple(host_client):
    """advance_days can tick multiple days at once."""
    player = socketio.test_client(app)
    player_id, party_id = _setup_active_party(host_client, player)

    mgr = _get_session()
    party = mgr.session.parties[party_id]
    dist_before = party.distance_traveled
    session_date_before = mgr.session.global_date

    host_client.get_received()  # drain
    host_client.emit("advance_days", {"count": 3})

    received = host_client.get_received()
    names = [m["name"] for m in received]
    assert "session_state" in names

    party = mgr.session.parties[party_id]
    # After multiple ticks the session global date should have advanced by 3 days
    assert (mgr.session.global_date - session_date_before).days == 3
    assert party.distance_traveled > dist_before

    player.disconnect()


# ---------------------------------------------------------------------------
# 6. disconnect / reconnect
# ---------------------------------------------------------------------------

def test_disconnect_marks_player_offline(host_client):
    """When a player disconnects, their socket_id is cleared but they remain in session."""
    player = socketio.test_client(app)
    player.emit("join_session", {"name": "Alice"})
    player_id = _extract_player_id(player.get_received())

    mgr = _get_session()
    assert mgr.session.players[player_id].socket_id is not None

    player.disconnect()

    assert mgr.session.players[player_id].socket_id is None


def test_reconnect_restores_player_state(host_client):
    """A disconnected player can reconnect with their player_id and regain state."""
    player = socketio.test_client(app)
    player.emit("join_session", {"name": "Alice"})
    player_id = _extract_player_id(player.get_received())
    player.disconnect()

    mgr = _get_session()
    assert mgr.session.players[player_id].socket_id is None

    # Reconnect
    player2 = socketio.test_client(app, auth={"player_id": player_id})
    assert player2.is_connected()

    # Should receive connected + session_state
    received = player2.get_received()
    names = [m["name"] for m in received]
    assert "connected" in names
    assert "session_state" in names

    # Socket ID should be restored
    assert mgr.session.players[player_id].socket_id is not None

    player2.disconnect()


# ---------------------------------------------------------------------------
# 7. create_party / assign_party / start_game
# ---------------------------------------------------------------------------

def test_create_party_host_only(host_client):
    """Only the host can create a party; non-hosts are rejected."""
    player = socketio.test_client(app)
    player.emit("join_session", {"name": "Alice"})
    player.get_received()

    # Non-host attempt
    player.emit("create_party", {"party_name": "Rogue Party"})
    err = _find_received_named(player.get_received(), "error")
    assert err is not None
    assert "Host access required" in err["args"][0]["message"]

    # Host attempt
    host_client.emit("create_party", {"party_name": "Legit Party"})
    created = _find_received_named(host_client.get_received(), "party_created")
    assert created is not None
    assert created["args"][0]["party_name"] == "Legit Party"

    player.disconnect()


def test_assign_party_flow(host_client):
    """Host can assign a player to a party; player receives assignment events."""
    player = socketio.test_client(app)
    player.emit("join_session", {"name": "Alice"})
    player_id = _extract_player_id(player.get_received())
    player.get_received()  # drain

    host_client.emit("create_party", {"party_name": "Wagon Rollers"})
    party_id = _extract_party_id(host_client)
    host_client.get_received()  # drain

    host_client.emit("assign_party", {"player_id": player_id, "party_id": party_id})

    # Player should receive an assignment notification
    assigned = _find_received_named(player.get_received(), "assigned_to_party")
    assert assigned is not None
    assert assigned["args"][0]["party_id"] == party_id

    mgr = _get_session()
    assert mgr.session.players[player_id].party_id == party_id
    assert player_id in mgr.session.parties[party_id].member_ids
    assert mgr.session.parties[party_id].captain_id == player_id  # first member becomes captain

    player.disconnect()


def test_start_game_validation(host_client):
    """Game cannot start without at least one party containing a player."""
    # Attempt to start with no parties / no players
    host_client.emit("start_game")
    err = _find_received_named(host_client.get_received(), "error")
    assert err is not None
    assert "Cannot start game" in err["args"][0]["message"]

    # Add a player and party
    player = socketio.test_client(app)
    player.emit("join_session", {"name": "Alice"})
    player_id = _extract_player_id(player.get_received())
    player.get_received()

    host_client.emit("create_party", {"party_name": "Wagon Rollers"})
    party_id = _extract_party_id(host_client)
    host_client.get_received()

    host_client.emit("assign_party", {"player_id": player_id, "party_id": party_id})
    host_client.get_received()

    # Now start should succeed
    host_client.emit("start_game")
    state = _find_received_named(host_client.get_received(), "session_state")
    assert state is not None
    mgr = _get_session()
    assert mgr.session.game_status == "outfitting"

    player.disconnect()
