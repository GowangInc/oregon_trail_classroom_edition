"""Comprehensive integration test simulating a complete Oregon Trail game flow."""

import pytest
import time

from server import (
    app,
    socketio,
    sessions,
    player_to_session,
    sid_to_player,
    auto_threads,
    auto_advance_generations,
    _start_auto_advance,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_globals():
    """Clear global server state before and after every test."""
    sessions.clear()
    player_to_session.clear()
    sid_to_player.clear()
    auto_threads.clear()
    auto_advance_generations.clear()
    yield
    sessions.clear()
    player_to_session.clear()
    sid_to_player.clear()
    auto_threads.clear()
    auto_advance_generations.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session():
    assert len(sessions) == 1
    return next(iter(sessions.values()))


def _extract_player_id(client):
    for msg in reversed(client.get_received()):
        if msg["name"] == "connected":
            pid = msg["args"][0].get("player_id")
            if pid is not None:
                return pid
    raise RuntimeError("No connected event with player_id found")


def _extract_party_id(host_client):
    for msg in reversed(host_client.get_received()):
        if msg["name"] == "party_created":
            return msg["args"][0]["party_id"]
    raise RuntimeError("No party_created event found")


def _find_received_named(client_or_messages, event_name):
    messages = client_or_messages.get_received() if hasattr(client_or_messages, "get_received") else client_or_messages
    for msg in reversed(messages):
        if msg["name"] == event_name:
            return msg
    return None


def _drain(*clients):
    for c in clients:
        c.get_received()


def _get_safe_choice(party):
    """Return a safe/default choice for a pending decision."""
    options = party.decision_pending.options
    if party.status == "river_crossing":
        return next((o for o in options if "Caulk" in o or "ferry" in o.lower()), options[0])
    if party.decision_pending.decision_type.value == "rest":
        return "Continue on" if "Continue on" in options else options[0]
    if party.decision_pending.decision_type.value == "hunt":
        return "Hunt" if "Hunt" in options else options[0]
    if party.decision_pending.decision_type.value == "pace":
        return "Keep pace and rations" if "Keep pace and rations" in options else options[0]
    if party.decision_pending.decision_type.value == "take_shortcut":
        return next((o for o in options if "safer" in o or "Bridger" in o or "Barlow" in o), options[0])
    if party.decision_pending.decision_type.value == "buy_supplies":
        return "Continue on" if "Continue on" in options else options[0]
    return options[0]


def _create_player(name):
    client = socketio.test_client(app)
    client.emit("join_session", {"name": name})
    pid = _extract_player_id(client)
    return client, pid


def _resolve_pending_decisions(host, mgr, party_members, active_clients):
    """Vote on and immediately resolve any pending decisions for all parties."""
    for party_id, members in party_members.items():
        party = mgr.session.parties.get(party_id)
        if not party or not party.decision_pending or party.decision_pending.resolved:
            continue

        dec = party.decision_pending
        choice = _get_safe_choice(party)

        # Have all connected human players in the party vote
        for client, pid in members:
            if not client.is_connected():
                continue
            if pid in mgr.session.players and mgr.session.players[pid].is_alive:
                client.emit("submit_vote", {"decision_id": dec.decision_id, "choice": choice})

        # Verify votes were recorded
        assert len(dec.votes) > 0

        # Host override to resolve immediately
        host.emit("host_override_decision", {"party_id": party_id, "choice": choice})

    _drain(host, *active_clients)


def _advance_day_and_check(host, mgr, active_clients, party_members):
    """Advance one day, resolving decisions first, and capture finish/game-over events."""
    _resolve_pending_decisions(host, mgr, party_members, active_clients)

    host.emit("advance_day")
    msgs = host.get_received()

    finished_events = []
    game_over_event = None
    for msg in msgs:
        if msg["name"] == "party_finished":
            finished_events.append(msg)
        elif msg["name"] == "game_over":
            game_over_event = msg

    _drain(*active_clients)
    return finished_events, game_over_event


# ---------------------------------------------------------------------------
# Integration Test
# ---------------------------------------------------------------------------

def test_complete_game_flow():
    # ========================================================================
    # 1. Host setup
    # ========================================================================
    host = socketio.test_client(app, auth={"is_host": True, "host_password": "admin"})
    assert host.is_connected()
    host_id = _extract_player_id(host)
    mgr = _get_session()
    assert mgr.session.host_player_id == host_id
    _drain(host)

    # ========================================================================
    # 2. Players join (4 players)
    # ========================================================================
    players = []
    player_ids = []
    for name in ["Alice", "Bob", "Charlie", "Diana"]:
        client, pid = _create_player(name)
        players.append(client)
        player_ids.append(pid)
        assert pid in mgr.session.players
        assert mgr.session.players[pid].name == name

    p1, p2, p3, p4 = players
    pid1, pid2, pid3, pid4 = player_ids
    active_clients = [host, p1, p2, p3, p4]
    _drain(*active_clients)

    # ========================================================================
    # 3. Party creation and assignment
    # ========================================================================
    host.emit("create_party", {"party_name": "The Pioneers"})
    party_a_id = _extract_party_id(host)
    _drain(host)

    host.emit("create_party", {"party_name": "The Settlers"})
    party_b_id = _extract_party_id(host)
    _drain(host)

    host.emit("assign_party", {"player_id": pid1, "party_id": party_a_id})
    host.emit("assign_party", {"player_id": pid2, "party_id": party_a_id})
    host.emit("assign_party", {"player_id": pid3, "party_id": party_b_id})
    host.emit("assign_party", {"player_id": pid4, "party_id": party_b_id})
    _drain(*active_clients)

    assert pid1 in mgr.session.parties[party_a_id].member_ids
    assert pid2 in mgr.session.parties[party_a_id].member_ids
    assert pid3 in mgr.session.parties[party_b_id].member_ids
    assert pid4 in mgr.session.parties[party_b_id].member_ids

    party_members = {
        party_a_id: [(p1, pid1), (p2, pid2)],
        party_b_id: [(p3, pid3), (p4, pid4)],
    }

    # ========================================================================
    # 4. Game start → outfitting phase
    # ========================================================================
    host.emit("start_game")
    _drain(*active_clients)
    assert mgr.session.game_status == "outfitting"

    # ========================================================================
    # 5. Outfitting: profession, month, supplies, mark ready
    # ========================================================================
    # Party A outfitted by p1 (first member = captain)
    p1.emit("choose_profession", {"party_id": party_a_id, "profession": "Banker from Boston"})
    p1.emit("choose_month", {"party_id": party_a_id, "month": 4})
    p1.emit("buy_supplies", {"party_id": party_a_id, "item": "oxen", "quantity": 6})
    p1.emit("buy_supplies", {"party_id": party_a_id, "item": "food", "quantity": 400})
    p1.emit("buy_supplies", {"party_id": party_a_id, "item": "clothing", "quantity": 8})
    p1.emit("buy_supplies", {"party_id": party_a_id, "item": "bullets", "quantity": 4})
    p1.emit("buy_supplies", {"party_id": party_a_id, "item": "wagon_wheel", "quantity": 2})
    p1.emit("buy_supplies", {"party_id": party_a_id, "item": "wagon_axle", "quantity": 2})
    p1.emit("buy_supplies", {"party_id": party_a_id, "item": "wagon_tongue", "quantity": 2})
    p1.emit("party_ready", {"party_id": party_a_id})

    # Party B outfitted by p3
    p3.emit("choose_profession", {"party_id": party_b_id, "profession": "Carpenter from Ohio"})
    p3.emit("choose_month", {"party_id": party_b_id, "month": 5})
    p3.emit("buy_supplies", {"party_id": party_b_id, "item": "oxen", "quantity": 6})
    p3.emit("buy_supplies", {"party_id": party_b_id, "item": "food", "quantity": 500})
    p3.emit("buy_supplies", {"party_id": party_b_id, "item": "clothing", "quantity": 10})
    p3.emit("buy_supplies", {"party_id": party_b_id, "item": "bullets", "quantity": 5})
    p3.emit("buy_supplies", {"party_id": party_b_id, "item": "wagon_wheel", "quantity": 2})
    p3.emit("buy_supplies", {"party_id": party_b_id, "item": "wagon_axle", "quantity": 2})
    p3.emit("buy_supplies", {"party_id": party_b_id, "item": "wagon_tongue", "quantity": 2})
    p3.emit("party_ready", {"party_id": party_b_id})

    _drain(*active_clients)

    assert mgr.session.parties[party_a_id].outfitting_complete
    assert mgr.session.parties[party_b_id].outfitting_complete
    assert mgr.session.parties[party_a_id].inventory.oxen > 0
    assert mgr.session.parties[party_b_id].inventory.oxen > 0

    # ========================================================================
    # 6. Begin journey
    # ========================================================================
    host.emit("begin_journey")
    _drain(*active_clients)
    assert mgr.session.game_status == "active"

    # Disable auto-advance so we can control ticks manually for testing
    host.emit("set_auto_advance", {"enabled": False})
    _drain(*active_clients)
    assert not mgr.session.auto_advance_enabled

    # ========================================================================
    # 7. Travel loop: simulate 15 days of travel
    # ========================================================================
    for day in range(15):
        if mgr.session.game_status != "active":
            break
        _advance_day_and_check(host, mgr, active_clients, party_members)

    assert mgr.session.game_status == "active"
    assert mgr.session.tick_count >= 15
    assert mgr.session.parties[party_a_id].distance_traveled > 0
    assert mgr.session.parties[party_b_id].distance_traveled > 0

    # Resolve any decision created on the final travel day
    _resolve_pending_decisions(host, mgr, party_members, active_clients)

    # ========================================================================
    # 8. Hunt: trigger a hunt decision, resolve it with shots_hit
    # ========================================================================
    with mgr.lock:
        mgr.session.parties[party_a_id].last_vote_called_at = 0

    p1.emit("call_vote", {"party_id": party_a_id, "vote_type": "hunt"})
    _drain(*active_clients)

    party_a = mgr.session.parties[party_a_id]
    assert party_a.decision_pending is not None
    assert party_a.decision_pending.decision_type.value == "hunt"
    dec_id = party_a.decision_pending.decision_id

    # Players vote
    p1.emit("submit_vote", {"decision_id": dec_id, "choice": "Hunt"})
    p2.emit("submit_vote", {"decision_id": dec_id, "choice": "Hunt"})

    # Verify votes were tallied correctly
    assert party_a.decision_pending.votes[pid1] == "Hunt"
    assert party_a.decision_pending.votes[pid2] == "Hunt"

    # Resolve via host override so the party enters hunting status
    bullets_before = mgr.session.parties[party_a_id].inventory.bullets
    food_before = mgr.session.parties[party_a_id].inventory.food
    host.emit("host_override_decision", {"party_id": party_a_id, "choice": "Hunt"})
    _drain(*active_clients)
    assert mgr.session.parties[party_a_id].status == "hunting"

    # Resolve the hunt itself
    p1.emit("resolve_hunt", {"party_id": party_a_id, "shots_hit": 3})
    _drain(*active_clients)

    # Verify bullets deducted and food gained
    assert mgr.session.parties[party_a_id].inventory.bullets < bullets_before
    assert mgr.session.parties[party_a_id].inventory.food > food_before
    assert mgr.session.parties[party_a_id].status == "traveling"

    # ========================================================================
    # 9. Rest: trigger a rest decision, resolve it, verify recovery
    # ========================================================================
    # Make a player unhealthy so we can observe health improvement
    host.emit("host_set_player_health", {"player_id": pid1, "health_status": "Poor"})
    _drain(*active_clients)
    assert mgr.session.players[pid1].health_status.value == "Poor"

    _resolve_pending_decisions(host, mgr, party_members, active_clients)

    with mgr.lock:
        mgr.session.parties[party_a_id].last_vote_called_at = 0

    p1.emit("call_vote", {"party_id": party_a_id, "vote_type": "rest"})
    _drain(*active_clients)

    party_a = mgr.session.parties[party_a_id]
    assert party_a.decision_pending is not None
    assert party_a.decision_pending.decision_type.value == "rest"

    host.emit("host_override_decision", {"party_id": party_a_id, "choice": "Rest here"})
    _drain(*active_clients)

    party_a = mgr.session.parties[party_a_id]
    assert party_a.is_resting
    rest_before = party_a.rest_days_remaining
    assert rest_before > 0

    # Advance at least one rest day
    host.emit("advance_day")
    _drain(*active_clients)

    party_a = mgr.session.parties[party_a_id]
    assert party_a.rest_days_remaining < rest_before
    # Health should have improved during rest
    assert mgr.session.players[pid1].health_status.value != "Poor"

    # Let rest complete
    for _ in range(5):
        party_a = mgr.session.parties[party_a_id]
        if not party_a.is_resting:
            break
        host.emit("advance_day")
        _drain(*active_clients)
    assert not mgr.session.parties[party_a_id].is_resting

    # ========================================================================
    # 10. River crossing: manually trigger and resolve a crossing
    # ========================================================================
    # Because the engine can overshoot landmarks, we directly set up a river
    # crossing state and test the cross_river event.
    with mgr.lock:
        party = mgr.session.parties[party_a_id]
        party.status = "river_crossing"

    p1.emit("cross_river", {"party_id": party_a_id, "method": "Caulk the wagon and float"})
    river_msgs = p1.get_received()
    river_result = _find_received_named(river_msgs, "river_result")
    assert river_result is not None
    assert "message" in river_result["args"][0]
    assert mgr.session.parties[party_a_id].status == "traveling"

    # ========================================================================
    # 11. Inject event: host injects broken_wheel
    # ========================================================================
    wheels_before = mgr.session.parties[party_a_id].inventory.wagon_wheels
    host.emit("inject_event", {"party_id": party_a_id, "event_id": "broken_wheel"})
    received = host.get_received()

    injected = _find_received_named(received, "host_injected_event")
    assert injected is not None
    assert injected["args"][0]["party_id"] == party_a_id

    _drain(*active_clients)
    assert mgr.session.parties[party_a_id].inventory.wagon_wheels < wheels_before

    # ========================================================================
    # 12. Auto-advance: enable, verify ticks, verify no duplicate threads
    # ========================================================================
    tick_before = mgr.session.tick_count

    # Stop any existing auto-advance thread first
    host.emit("set_auto_advance", {"enabled": False})
    _drain(*active_clients)
    assert not mgr.session.auto_advance_enabled

    # Bypass the 5-second server clamp by setting interval directly and
    # starting the worker manually so the test can run quickly.
    with mgr.lock:
        mgr.session.auto_advance_enabled = True
        mgr.session.auto_advance_interval = 1
    _start_auto_advance(mgr)

    # Let the background thread tick a couple of times
    time.sleep(2.5)

    tick_after = mgr.session.tick_count
    assert tick_after > tick_before, "Auto-advance should have ticked at least once"

    # Verify only one thread is tracked
    assert len(auto_threads) == 1, f"Expected 1 auto-advance thread, got {len(auto_threads)}"

    # Re-enabling via the socket event should NOT create a duplicate thread
    host.emit("set_auto_advance", {"enabled": True, "interval_seconds": 5})
    assert len(auto_threads) == 1

    # Disable auto-advance for the controlled finish
    host.emit("set_auto_advance", {"enabled": False})
    _drain(*active_clients)
    assert not mgr.session.auto_advance_enabled

    # ========================================================================
    # 13. Disconnect / reconnect during travel
    # ========================================================================
    # Disconnect p1
    p1.disconnect()
    active_clients = [host, p2, p3, p4]
    assert mgr.session.players[pid1].socket_id is None

    # Create a pending decision while p1 is offline
    _resolve_pending_decisions(host, mgr, party_members, active_clients)

    with mgr.lock:
        mgr.session.parties[party_a_id].last_vote_called_at = 0
    p2.emit("call_vote", {"party_id": party_a_id, "vote_type": "pace"})
    _drain(*active_clients)

    party_a = mgr.session.parties[party_a_id]
    assert party_a.decision_pending is not None
    assert not party_a.decision_pending.resolved

    # Reconnect p1
    p1_reconnect = socketio.test_client(app, auth={"player_id": pid1})
    assert p1_reconnect.is_connected()
    active_clients.append(p1_reconnect)
    party_members[party_a_id] = [(p1_reconnect, pid1), (p2, pid2)]

    reconnect_msgs = p1_reconnect.get_received()
    names = [m["name"] for m in reconnect_msgs]
    assert "connected" in names
    assert "session_state" in names
    assert "decision_required" in names, f"Expected decision_required on reconnect, got {names}"

    # State restored
    assert mgr.session.players[pid1].socket_id is not None

    # ========================================================================
    # 14. Finish game: advance until Oregon or all die
    # ========================================================================
    party_finished_events = []
    game_over_event = None
    max_days = 300

    for day in range(max_days):
        if mgr.session.game_status != "active":
            break
        finished, game_over = _advance_day_and_check(host, mgr, active_clients, party_members)
        party_finished_events.extend(finished)
        if game_over_event is None and game_over is not None:
            game_over_event = game_over

    # If still active, teleport closer to Oregon to force a finish
    if mgr.session.game_status == "active":
        _resolve_pending_decisions(host, mgr, party_members, active_clients)
        for party_id in [party_a_id, party_b_id]:
            host.emit("host_edit_party", {"party_id": party_id, "field": "distance_traveled", "value": 2000})
        _drain(*active_clients)

        for day in range(50):
            if mgr.session.game_status != "active":
                break
            finished, game_over = _advance_day_and_check(host, mgr, active_clients, party_members)
            party_finished_events.extend(finished)
            if game_over_event is None and game_over is not None:
                game_over_event = game_over

    # Verify game ended
    assert mgr.session.game_status == "ended", f"Expected game to end, status={mgr.session.game_status}"

    # Verify party_finished events were broadcast
    assert len(party_finished_events) > 0, "Expected at least one party_finished event"
    for ev in party_finished_events:
        args = ev["args"][0]
        assert "party_id" in args
        assert "party_name" in args
        assert "score" in args
        assert "survivors" in args
        assert "status" in args

    # Verify game_over event with rankings
    assert game_over_event is not None, "Expected game_over event"
    rankings = game_over_event["args"][0]["final_rankings"]
    assert len(rankings) >= 1
    for r in rankings:
        assert "party_id" in r
        assert "party_name" in r
        assert "score" in r
        assert "status" in r

    # ========================================================================
    # Cleanup
    # ========================================================================
    p1_reconnect.disconnect()
    p2.disconnect()
    p3.disconnect()
    p4.disconnect()
    host.disconnect()
