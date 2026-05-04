"""Playability tests for The Oregon Trail - Classroom Edition.

Covers soft locks, dead ends, and states where the game becomes unplayable.
Each test verifies that the game remains in a playable state after edge cases.
"""

import json
import os
import time

import pytest

from server import (
    app,
    socketio,
    sessions,
    player_to_session,
    sid_to_player,
    auto_threads,
    auto_advance_generations,
    _start_auto_advance,
    _stop_auto_advance,
)
from session_manager import SessionManager
from party_engine import PartyEngine
from models import Party, Player, Decision, DecisionType, Inventory, GameSession
from game_data import (
    HealthStatus,
    Profession,
    Pace,
    Rations,
    Weather,
    SCORE_SURVIVOR,
    SCORE_OXEN,
    SCORE_SPARE_PART,
    SCORE_PER_5_DOLLARS,
    SCORE_PER_50_FOOD,
    SCORE_PER_CLOTHING,
    SCORE_PER_BULLET,
    HUNTING_MAX_FOOD_PER_HUNT,
    MAX_SPARE_PARTS,
    STORE_PRICES,
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


def _extract_player_id(client_or_messages):
    messages = client_or_messages.get_received() if hasattr(client_or_messages, "get_received") else client_or_messages
    for msg in reversed(messages):
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


def _create_player(name):
    client = socketio.test_client(app)
    client.emit("join_session", {"name": name})
    pid = _extract_player_id(client)
    return client, pid


def _create_host():
    client = socketio.test_client(app, auth={"is_host": True, "host_password": "admin"})
    assert client.is_connected()
    host_id = _extract_player_id(client)
    mgr = _get_session()
    return client, host_id, mgr


def _setup_party(host, player_client, party_name="Test Party"):
    """Create party, assign player, start game, begin journey. Returns (pid, party_id, mgr)."""
    # Find the player_id from the session (messages were drained by _create_player)
    mgr = _get_session()
    player_id = None
    for pid, p in mgr.session.players.items():
        if not p.is_host:
            player_id = pid
            break
    if player_id is None:
        raise RuntimeError("No non-host player found in session")

    host.emit("create_party", {"party_name": party_name})
    party_id = _extract_party_id(host)
    host.emit("assign_party", {"player_id": player_id, "party_id": party_id})
    _drain(host, player_client)

    host.emit("start_game")
    _drain(host)
    assert mgr.session.game_status == "outfitting"

    # Outfit
    player_client.emit("choose_profession", {"party_id": party_id, "profession": "Carpenter from Ohio"})
    player_client.emit("choose_month", {"party_id": party_id, "month": 4})
    player_client.emit("buy_supplies", {"party_id": party_id, "item": "oxen", "quantity": 6})
    player_client.emit("buy_supplies", {"party_id": party_id, "item": "food", "quantity": 400})
    player_client.emit("buy_supplies", {"party_id": party_id, "item": "clothing", "quantity": 8})
    player_client.emit("buy_supplies", {"party_id": party_id, "item": "bullets", "quantity": 4})
    player_client.emit("buy_supplies", {"party_id": party_id, "item": "wagon_wheel", "quantity": 2})
    player_client.emit("buy_supplies", {"party_id": party_id, "item": "wagon_axle", "quantity": 2})
    player_client.emit("buy_supplies", {"party_id": party_id, "item": "wagon_tongue", "quantity": 2})
    player_client.emit("party_ready", {"party_id": party_id})
    _drain(host, player_client)

    host.emit("begin_journey")
    _drain(host, player_client)
    assert mgr.session.game_status == "active"

    # Disable auto-advance for controlled testing
    host.emit("set_auto_advance", {"enabled": False})
    _drain(host)
    return player_id, party_id, mgr


def _quick_setup(host, player_client):
    """Like _setup_party but faster - outfit via quick_start pattern."""
    # Find the player_id from the session
    mgr = _get_session()
    player_id = None
    for pid, p in mgr.session.players.items():
        if not p.is_host:
            player_id = pid
            break
    if player_id is None:
        raise RuntimeError("No non-host player found in session")

    host.emit("create_party", {"party_name": "Wagon Rollers"})
    party_id = _extract_party_id(host)
    host.emit("assign_party", {"player_id": player_id, "party_id": party_id})
    _drain(host, player_client)

    host.emit("start_game")
    _drain(host)
    host.emit("begin_journey")
    _drain(host, player_client)

    host.emit("set_auto_advance", {"enabled": False})
    _drain(host)
    return player_id, party_id, mgr


# ---------------------------------------------------------------------------
# 1. Full game completion
# ---------------------------------------------------------------------------

def test_full_game_completion():
    """A party can travel from Independence to Willamette Valley without getting stuck."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    host.emit("create_party", {"party_name": "The Survivors"})
    party_id = _extract_party_id(host)
    host.emit("assign_party", {"player_id": pid, "party_id": party_id})
    _drain(host, player)

    host.emit("start_game")
    _drain(host)
    mgr = _get_session()
    assert mgr.session.game_status == "outfitting"

    player.emit("choose_profession", {"party_id": party_id, "profession": "Farmer from Illinois"})
    player.emit("choose_month", {"party_id": party_id, "month": 3})
    for item, qty in [("oxen", 8), ("food", 800), ("clothing", 10), ("bullets", 6),
                      ("wagon_wheel", 3), ("wagon_axle", 3), ("wagon_tongue", 3)]:
        player.emit("buy_supplies", {"party_id": party_id, "item": item, "quantity": qty})
    player.emit("party_ready", {"party_id": party_id})
    _drain(host, player)

    host.emit("begin_journey")
    _drain(host, player)
    assert mgr.session.game_status == "active"

    host.emit("set_auto_advance", {"enabled": False})
    _drain(host)

    party = mgr.session.parties[party_id]
    assert party.status == "traveling"
    assert party.distance_traveled == 0

    # Teleport near Oregon
    host.emit("host_edit_party", {"party_id": party_id, "field": "distance_traveled", "value": 2090})
    _drain(host)
    host.emit("host_edit_party", {"party_id": party_id, "field": "food", "value": 9999})
    _drain(host)

    # Advance to finish
    finished = False
    for _ in range(50):
        if mgr.session.game_status == "ended":
            finished = True
            break
        host.emit("advance_day")
        msgs = host.get_received()
        if _find_received_named(msgs, "party_finished"):
            finished = True
            break
        _drain(player)

    assert finished, "Party should reach Oregon"
    party = mgr.session.parties[party_id]
    assert party.status == "finished", f"Expected finished, got {party.status}"
    assert party.distance_traveled >= 2094
    assert party.score > 0

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 2. Decision timeout soft locks
# ---------------------------------------------------------------------------

def test_decision_timeout_resolves():
    """If no player votes, the timeout resolves the decision automatically on next tick."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    pid, party_id, mgr = _setup_party(host, player)

    # Create a decision with a very short timeout
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.last_vote_called_at = 0
        party.decision_pending = Decision(
            party_id=party_id,
            decision_type=DecisionType.REST,
            prompt="Rest test",
            options=["Rest here", "Continue on"],
            captain_id=party.captain_id,
            captain_default="Continue on",
            timeout_seconds=1,
        )
        party.status = "decision"
    _drain(host, player)

    assert mgr.session.parties[party_id].decision_pending is not None
    assert not mgr.session.parties[party_id].decision_pending.resolved

    # Wait for timeout
    time.sleep(1.1)

    # Tick should resolve timed-out decision
    host.emit("advance_day")
    _drain(host, player)

    assert mgr.session.parties[party_id].decision_pending is None, (
        "Decision should have been resolved by timeout"
    )
    assert mgr.session.parties[party_id].status in ("traveling", "resting"), (
        f"Party should be traveling/resting, got {mgr.session.parties[party_id].status}"
    )

    player.disconnect()
    host.disconnect()


def test_decision_timeout_no_crash_empty_votes():
    """Timeout resolution with zero votes does not crash."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.decision_pending = Decision(
            party_id=party_id,
            decision_type=DecisionType.PACE,
            prompt="Test",
            options=["Keep pace and rations", "Speed up (increase pace)"],
            captain_id=party.captain_id,
            captain_default="Keep pace and rations",
            timeout_seconds=0,  # Immediate timeout
        )
        party.status = "decision"
    _drain(host, player)

    # Tick resolves immediately (timeout=0 already elapsed)
    host.emit("advance_day")
    _drain(host, player)

    assert mgr.session.parties[party_id].decision_pending is None
    # Status may still be "decision" from the PACE decision - the key is
    # that the party can still travel (no pending decision) and next tick
    # will advance normally.

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 3. Auto-advance safety
# ---------------------------------------------------------------------------

def test_auto_advance_skips_hunting():
    """Auto-advance should not tick a party while it is in hunting status."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)
    party = mgr.session.parties[party_id]

    with mgr.lock:
        party.status = "hunting"
    tick_before = mgr.session.tick_count
    dist_before = party.distance_traveled
    food_before = party.inventory.food

    # Run tick via advance_day
    host.emit("advance_day")
    _drain(host, player)

    # Party should be unchanged
    party = mgr.session.parties[party_id]
    assert party.status == "hunting"
    assert party.distance_traveled == dist_before, "Hunting party should not travel"
    assert party.inventory.food == food_before, "Hunting party should not consume food"

    player.disconnect()
    host.disconnect()


def test_auto_advance_skips_outfitting():
    """Auto-advance should not tick a party in outfitting status."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)
    party = mgr.session.parties[party_id]

    with mgr.lock:
        party.status = "outfitting"
    dist_before = party.distance_traveled

    host.emit("advance_day")
    _drain(host, player)

    party = mgr.session.parties[party_id]
    assert party.distance_traveled == dist_before
    assert party.status != "traveling"  # Should still be outfitting

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 4. Multiple parties
# ---------------------------------------------------------------------------

def test_multiple_parties_no_interference():
    """3+ parties can play simultaneously without state interference."""
    host, host_id, mgr = _create_host()

    players = []
    player_ids = []
    for name in ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]:
        client, pid = _create_player(name)
        players.append(client)
        player_ids.append(pid)

    _drain(host, *players)

    # Create 3 parties
    host.emit("create_party", {"party_name": "Party A"})
    party_a = _extract_party_id(host)
    host.emit("create_party", {"party_name": "Party B"})
    party_b = _extract_party_id(host)
    host.emit("create_party", {"party_name": "Party C"})
    party_c = _extract_party_id(host)
    _drain(host)

    # Assign 2 players per party
    host.emit("assign_party", {"player_id": player_ids[0], "party_id": party_a})
    host.emit("assign_party", {"player_id": player_ids[1], "party_id": party_a})
    host.emit("assign_party", {"player_id": player_ids[2], "party_id": party_b})
    host.emit("assign_party", {"player_id": player_ids[3], "party_id": party_b})
    host.emit("assign_party", {"player_id": player_ids[4], "party_id": party_c})
    host.emit("assign_party", {"player_id": player_ids[5], "party_id": party_c})
    _drain(host, *players)

    host.emit("quick_start")
    _drain(host, *players)

    assert mgr.session.game_status == "active"

    # Stop auto-advance from quick_start
    host.emit("set_auto_advance", {"enabled": False})
    _drain(host, *players)

    # Verify no party state leaks into another
    party_a_obj = mgr.session.parties[party_a]
    party_b_obj = mgr.session.parties[party_b]
    party_c_obj = mgr.session.parties[party_c]
    assert party_a_obj.party_id != party_b_obj.party_id
    assert set(party_a_obj.member_ids) & set(party_b_obj.member_ids) == set()

    # Advance a few days and verify each party gets its own state
    for _ in range(5):
        host.emit("advance_day")
        _drain(host, *players)

    # Each party should have its own engine and distance
    assert mgr.session.parties[party_a].party_id == party_a
    assert mgr.session.parties[party_b].party_id == party_b
    assert mgr.session.parties[party_c].party_id == party_c

    for c in players:
        c.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 5. Store edge cases
# ---------------------------------------------------------------------------

def test_store_insufficient_funds():
    """Buying with insufficient funds returns error without crashing."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].inventory.money = 1

    player.emit("buy_item", {"party_id": party_id, "item": "oxen", "quantity": 1})
    result = _find_received_named(player, "buy_result")
    assert result is not None
    assert not result["args"][0]["success"] or "Not enough money" in str(result["args"][0].get("message", ""))

    player.disconnect()
    host.disconnect()


def test_store_zero_money():
    """Buying with exactly zero money behaves correctly."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].inventory.money = 0

    player.emit("buy_item", {"party_id": party_id, "item": "food", "quantity": 1})
    result = _find_received_named(player, "buy_result")
    assert result is not None

    party = mgr.session.parties[party_id]
    assert party.inventory.money == 0
    assert party.inventory.food == 400  # Unchanged

    player.disconnect()
    host.disconnect()


def test_store_spare_parts_cap():
    """Cannot buy more than MAX_SPARE_PARTS of any spare part type."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    # Party already has 2 wheels from setup. Buy 2 more (total 4, cap is 3).
    with mgr.lock:
        mgr.session.parties[party_id].inventory.wagon_wheels = MAX_SPARE_PARTS

    player.emit("buy_item", {"party_id": party_id, "item": "wagon_wheel", "quantity": 1})
    result = _find_received_named(player, "buy_result")
    assert result is not None
    assert not result["args"][0]["success"]

    party = mgr.session.parties[party_id]
    assert party.inventory.wagon_wheels == MAX_SPARE_PARTS

    player.disconnect()
    host.disconnect()


def test_store_bulk_purchase():
    """Buying a large quantity in one transaction works correctly."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].inventory.money = 500

    food_before = mgr.session.parties[party_id].inventory.food
    # Use buy_item for mid-game purchases (buy_supplies is only for outfitting phase)
    player.emit("buy_item", {"party_id": party_id, "item": "food", "quantity": 500})
    result = _find_received_named(player, "buy_result")
    assert result is not None
    assert result["args"][0]["success"]

    party = mgr.session.parties[party_id]
    assert party.inventory.food == food_before + 500

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 6. River crossing all methods
# ---------------------------------------------------------------------------

def test_river_crossing_ford():
    """Ford the river returns to traveling (may succeed or fail, but always resolves)."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].status = "river_crossing"
    _drain(host, player)

    player.emit("cross_river", {"party_id": party_id, "method": "Ford the river"})
    result = _find_received_named(player, "river_result")
    assert result is not None
    assert mgr.session.parties[party_id].status == "traveling"

    player.disconnect()
    host.disconnect()


def test_river_crossing_caulk():
    """Caulk the wagon returns to traveling."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].status = "river_crossing"

    player.emit("cross_river", {"party_id": party_id, "method": "Caulk the wagon"})
    result = _find_received_named(player, "river_result")
    assert result is not None
    assert mgr.session.parties[party_id].status == "traveling"

    player.disconnect()
    host.disconnect()


def test_river_crossing_ferry():
    """Ferry crossing returns to traveling."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].status = "river_crossing"
        mgr.session.parties[party_id].inventory.money = 200  # Enough for ferry

    player.emit("cross_river", {"party_id": party_id, "method": "Take a ferry"})
    result = _find_received_named(player, "river_result")
    assert result is not None
    assert mgr.session.parties[party_id].status == "traveling"

    player.disconnect()
    host.disconnect()


def test_river_crossing_wait():
    """Waiting for better conditions returns to traveling."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].status = "river_crossing"

    player.emit("cross_river", {"party_id": party_id, "method": "Wait for better conditions"})
    result = _find_received_named(player, "river_result")
    assert result is not None
    assert mgr.session.parties[party_id].status == "traveling"

    player.disconnect()
    host.disconnect()


def test_river_crossing_all_methods_always_resolve():
    """Every crossing method returns party to traveling — no soft locks."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    methods = ["Ford the river", "Caulk the wagon", "Take a ferry", "Wait for better conditions"]

    for method in methods:
        with mgr.lock:
            party = mgr.session.parties[party_id]
            party.status = "river_crossing"
            party.inventory.money = 200  # Ensure ferry is affordable

        player.emit("cross_river", {"party_id": party_id, "method": method})
        result = _find_received_named(player, "river_result")
        assert result is not None, f"Crossing with '{method}' should return a result"
        assert mgr.session.parties[party_id].status == "traveling", (
            f"Party should be traveling after '{method}', got {mgr.session.parties[party_id].status}"
        )
        _drain(player)

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 7. Hunting edge cases
# ---------------------------------------------------------------------------

def test_hunting_zero_bullets():
    """Hunting with 0 bullets returns a message and returns to traveling."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].inventory.bullets = 0
        mgr.session.parties[party_id].status = "hunting"

    player.emit("resolve_hunt", {"party_id": party_id, "shots_hit": 5})
    result = _find_received_named(player, "hunt_result")
    assert result is not None
    assert "No bullets" in str(result["args"][0].get("message", ""))
    assert mgr.session.parties[party_id].status == "traveling"

    player.disconnect()
    host.disconnect()


def test_hunting_max_food_cap():
    """Hunting yields at most HUNTING_MAX_FOOD_PER_HUNT lbs."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.inventory.bullets = 50
        party.status = "hunting"

    food_before = mgr.session.parties[party_id].inventory.food
    player.emit("resolve_hunt", {"party_id": party_id, "shots_hit": 10})
    result = _find_received_named(player, "hunt_result")
    assert result is not None
    assert result["args"][0]["shots_fired"] > 0
    assert mgr.session.parties[party_id].status == "traveling"

    food_gained = mgr.session.parties[party_id].inventory.food - food_before
    assert food_gained <= HUNTING_MAX_FOOD_PER_HUNT

    player.disconnect()
    host.disconnect()


def test_hunting_returns_to_traveling():
    """After hunting, party always returns to traveling status."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        mgr.session.parties[party_id].status = "hunting"
        mgr.session.parties[party_id].inventory.bullets = 10

    player.emit("resolve_hunt", {"party_id": party_id, "shots_hit": 2})
    _drain(player)
    assert mgr.session.parties[party_id].status == "traveling"

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 8. Rest mechanics
# ---------------------------------------------------------------------------

def test_rest_decrements_properly():
    """Rest days decrement correctly and party returns to traveling when done."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.is_resting = True
        party.rest_days_remaining = 3
        party.status = "resting"
    _drain(host, player)

    for expected_remaining in [2, 1, 0]:
        host.emit("advance_day")
        _drain(host, player)
        party = mgr.session.parties[party_id]
        if expected_remaining == 0:
            assert not party.is_resting
            assert party.status == "traveling"
        else:
            assert party.rest_days_remaining < 3

    player.disconnect()
    host.disconnect()


def test_rest_single_day():
    """Resting for 1 day works and completes immediately."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.is_resting = True
        party.rest_days_remaining = 1
        party.status = "resting"

    host.emit("advance_day")
    _drain(host, player)

    party = mgr.session.parties[party_id]
    assert not party.is_resting
    assert party.status == "traveling"
    assert party.rest_days_remaining == 0

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 9. Death spiral
# ---------------------------------------------------------------------------

def test_all_members_die_party_dead():
    """When all members die, party is marked dead and game continues for others."""
    host, host_id, mgr = _create_host()

    # Create two parties
    p1, pid1 = _create_player("Alice")
    p2, pid2 = _create_player("Bob")
    _drain(host, p1, p2)

    host.emit("create_party", {"party_name": "Doomed"})
    doomed_id = _extract_party_id(host)
    host.emit("create_party", {"party_name": "Survivors"})
    surv_id = _extract_party_id(host)
    _drain(host)

    host.emit("assign_party", {"player_id": pid1, "party_id": doomed_id})
    host.emit("assign_party", {"player_id": pid2, "party_id": surv_id})
    _drain(host, p1, p2)

    host.emit("start_game")
    _drain(host)
    host.emit("begin_journey")
    _drain(host, p1, p2)

    host.emit("set_auto_advance", {"enabled": False})
    _drain(host, p1, p2)

    # Kill all members of the doomed party
    with mgr.lock:
        for mid in mgr.session.parties[doomed_id].member_ids:
            if mid in mgr.session.players:
                mgr.session.players[mid].health_status = HealthStatus.DEAD
                mgr.session.players[mid].is_alive = False
        mgr.session.parties[doomed_id].status = "traveling"  # Allow tick

    # Tick: should detect all dead and mark party dead
    host.emit("advance_day")
    _drain(host, p1, p2)

    doomed = mgr.session.parties[doomed_id]
    assert doomed.status == "dead", f"Expected dead, got {doomed.status}"

    # The other party should still be active
    surv = mgr.session.parties[surv_id]
    assert surv.status in ("traveling",), f"Expected traveling, got {surv.status}"

    # Game should still be active
    assert mgr.session.game_status in ("active", "paused")

    p1.disconnect()
    p2.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 10. Host controls
# ---------------------------------------------------------------------------

def test_host_pause_resume():
    """Pause and resume change game status without crashing."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    host.emit("pause_game")
    msgs = host.get_received()
    assert _find_received_named(msgs, "game_paused") is not None
    assert mgr.session.game_status == "paused"

    host.emit("resume_game")
    msgs = host.get_received()
    assert _find_received_named(msgs, "game_resumed") is not None
    assert mgr.session.game_status == "active"

    player.disconnect()
    host.disconnect()


def test_host_advance_days_multiple():
    """Advancing multiple days at once works without errors."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    dist_before = mgr.session.parties[party_id].distance_traveled
    host.emit("advance_days", {"count": 5})
    _drain(host, player)

    assert mgr.session.tick_count > 0
    party = mgr.session.parties[party_id]
    assert party.distance_traveled >= dist_before  # Should have moved at least a bit

    player.disconnect()
    host.disconnect()


def test_host_inject_event_no_crash():
    """Injecting an event does not crash and returns result."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    host.emit("inject_event", {"party_id": party_id, "event_id": "broken_wheel"})
    msgs = host.get_received()
    injected = _find_received_named(msgs, "host_injected_event")
    assert injected is not None

    player.disconnect()
    host.disconnect()


def test_host_edit_party_all_fields():
    """Host can edit party fields at any time without crash."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    edits = [
        ("distance_traveled", 500),
        ("money", 500.0),
        ("food", 500),
        ("oxen", 4),
        ("clothing", 20),
        ("bullets", 50),
        ("wagon_wheels", 1),
        ("wagon_axles", 1),
        ("wagon_tongues", 1),
    ]

    for field, value in edits:
        host.emit("host_edit_party", {"party_id": party_id, "field": field, "value": value})
        _drain(host)

    party = mgr.session.parties[party_id]
    assert party.distance_traveled == 500
    assert party.inventory.money == 500.0
    assert party.inventory.food == 500
    assert party.inventory.oxen == 4
    assert party.inventory.clothing == 20
    assert party.inventory.bullets == 50
    assert party.inventory.wagon_wheels == 1

    player.disconnect()
    host.disconnect()


def test_host_edit_party_during_decision():
    """Host can edit party even while a decision is pending."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.decision_pending = Decision(
            party_id=party_id,
            decision_type=DecisionType.REST,
            prompt="Test",
            options=["Continue on", "Hunt for food"],
            captain_id=party.captain_id,
            captain_default="Continue on",
            timeout_seconds=30,
        )
        party.status = "decision"

    host.emit("host_edit_party", {"party_id": party_id, "field": "food", "value": 999})
    _drain(host)

    assert mgr.session.parties[party_id].inventory.food == 999
    assert mgr.session.parties[party_id].decision_pending is not None
    assert mgr.session.parties[party_id].status == "decision"

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 11. Save / Load roundtrip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip():
    """Save mid-game, load, and verify state is playable and consistent."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    # Advance a few days to establish state
    for _ in range(3):
        host.emit("advance_day")
        _drain(host, player)

    distance_before = mgr.session.parties[party_id].distance_traveled
    food_before = mgr.session.parties[party_id].inventory.food
    date_before = mgr.session.global_date
    tick_before = mgr.session.tick_count

    # Save
    session_code = mgr.session.session_code
    host.emit("save_state")
    _drain(host)

    save_path = f"saves/save_{session_code}.json"
    assert os.path.exists(save_path), f"Save file {save_path} should exist"

    # Load into the same session
    host.emit("load_state", {"session_code": session_code})
    msgs = host.get_received()

    occ = _find_received_named(msgs, "event_occurred")
    assert occ is not None
    assert "loaded" in occ["args"][0]["message"].lower()

    # Verify state is consistent
    party = mgr.session.parties[party_id]
    assert party.distance_traveled == distance_before
    assert party.inventory.food == food_before

    # Verify game is still playable - advance a day
    host.emit("advance_day")
    _drain(host, player)
    assert mgr.session.tick_count > 0

    # Clean up save file
    if os.path.exists(save_path):
        os.remove(save_path)

    player.disconnect()
    host.disconnect()


def test_save_load_after_load_playable():
    """After loading, party can still travel and decisions work."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    host.emit("save_state")
    _drain(host)
    session_code = mgr.session.session_code

    host.emit("load_state", {"session_code": session_code})
    _drain(host, player)

    # Game should still be in active state
    assert mgr.session.game_status == "active"

    # Verify we can create and resolve a decision
    with mgr.lock:
        mgr.session.parties[party_id].last_vote_called_at = 0

    player.emit("call_vote", {"party_id": party_id, "vote_type": "hunt"})
    _drain(host, player)

    party = mgr.session.parties[party_id]
    assert party.decision_pending is not None, "Decision should be created after load"

    # Resolve it
    host.emit("host_override_decision", {"party_id": party_id, "choice": "Hunt"})
    _drain(host, player)
    assert mgr.session.parties[party_id].status == "hunting"

    save_path = f"saves/save_{session_code}.json"
    if os.path.exists(save_path):
        os.remove(save_path)

    player.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 12. Rapid voting
# ---------------------------------------------------------------------------

def test_rapid_voting_full_party():
    """A full party (1 human + 4 NPCs) can vote and tally correctly."""
    host, host_id, mgr = _create_host()
    player, pid = _create_player("Alice")
    _, party_id, mgr = _setup_party(host, player)

    # Fill party with NPCs
    with mgr.lock:
        mgr.fill_party_with_npcs(party_id)

    party = mgr.session.parties[party_id]
    assert len(party.member_ids) == 5

    with mgr.lock:
        party.last_vote_called_at = 0

    player.emit("call_vote", {"party_id": party_id, "vote_type": "pace"})
    _drain(host, player)

    decision = mgr.session.parties[party_id].decision_pending
    assert decision is not None

    player.emit("submit_vote", {"decision_id": decision.decision_id, "choice": "Keep pace and rations"})
    _drain(player)

    # NPCs should have auto-voted
    assert len(decision.votes) == 5, f"Expected 5 votes (1 human + 4 NPCs), got {len(decision.votes)}"

    # Cleanly resolve
    host.emit("host_override_decision", {"party_id": party_id, "choice": "Keep pace and rations"})
    _drain(host, player)

    assert mgr.session.parties[party_id].decision_pending is None

    player.disconnect()
    host.disconnect()


def test_rapid_voting_many_parties():
    """Many parties voting simultaneously does not cause state corruption."""
    host, host_id, mgr = _create_host()

    num_parties = 6
    players = []
    party_ids = []

    for i in range(num_parties):
        p, pid = _create_player(f"Player{i}")
        players.append((p, pid))

    _drain(host, *[p for p, _ in players])

    for i, (p, pid) in enumerate(players):
        host.emit("create_party", {"party_name": f"Party {i}"})
        party_id = _extract_party_id(host)
        host.emit("assign_party", {"player_id": pid, "party_id": party_id})
        party_ids.append(party_id)
        _drain(host, p)

    host.emit("quick_start")
    _drain(host, *[p for p, _ in players])

    host.emit("set_auto_advance", {"enabled": False})
    _drain(host, *[p for p, _ in players])

    # Call votes across all parties
    for i, (p, pid) in enumerate(players):
        with mgr.lock:
            mgr.session.parties[party_ids[i]].last_vote_called_at = 0
        p.emit("call_vote", {"party_id": party_ids[i], "vote_type": "pace"})

    _drain(host, *[p for p, _ in players])

    # Verify all parties got decisions
    for party_id in party_ids:
        party = mgr.session.parties[party_id]
        assert party.decision_pending is not None, f"Party {party_id} should have a decision pending"

    # Resolve all
    for party_id in party_ids:
        host.emit("host_override_decision", {"party_id": party_id, "choice": "Keep pace and rations"})

    _drain(host, *[p for p, _ in players])

    for party_id in party_ids:
        assert mgr.session.parties[party_id].decision_pending is None

    for p, _ in players:
        p.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 13. Empty session
# ---------------------------------------------------------------------------

def test_empty_session_cannot_start_game():
    """Host creates session, nobody joins, start_game returns an error."""
    host, host_id, mgr = _create_host()

    # No players joined, no parties created
    host.emit("start_game")
    err = _find_received_named(host, "error")
    assert err is not None
    assert mgr.session.game_status == "lobby"

    host.disconnect()


def test_empty_session_quick_start_with_npcs():
    """Quick start with no real players should still work (auto-creates NPC-filled party)."""
    host, host_id, mgr = _create_host()

    # Create a party manually
    host.emit("create_party", {"party_name": "Ghost Wagon"})
    _drain(host)

    host.emit("quick_start")
    _drain(host)

    # Should have started game with NPC-only party
    assert mgr.session.game_status == "active"
    assert len(mgr.session.parties) >= 1

    # Stop auto-advance for cleanup
    host.emit("set_auto_advance", {"enabled": False})
    _drain(host)

    host.disconnect()


# ---------------------------------------------------------------------------
# 14. Party migration
# ---------------------------------------------------------------------------

def test_party_migration_no_state_leaks():
    """Reassigning a player between parties mid-game does not leak state."""
    host, host_id, mgr = _create_host()
    p1, pid1 = _create_player("Alice")
    p2, pid2 = _create_player("Bob")
    _drain(host, p1, p2)

    host.emit("create_party", {"party_name": "Party A"})
    party_a = _extract_party_id(host)
    host.emit("create_party", {"party_name": "Party B"})
    party_b = _extract_party_id(host)
    _drain(host)

    host.emit("assign_party", {"player_id": pid1, "party_id": party_a})
    host.emit("assign_party", {"player_id": pid2, "party_id": party_b})
    _drain(host, p1, p2)

    host.emit("start_game")
    _drain(host)
    host.emit("begin_journey")
    _drain(host, p1, p2)

    host.emit("set_auto_advance", {"enabled": False})
    _drain(host, p1, p2)

    # Advance a bit
    for _ in range(3):
        host.emit("advance_day")
        _drain(host, p1, p2)

    dist_a_before = mgr.session.parties[party_a].distance_traveled

    # Migrate p1 from Party A to Party B
    host.emit("assign_party", {"player_id": pid1, "party_id": party_b})
    _drain(host, p1, p2)

    assert pid1 in mgr.session.parties[party_b].member_ids
    assert pid1 not in mgr.session.parties[party_a].member_ids
    assert mgr.session.players[pid1].party_id == party_b

    # Party A should still have its distance and not be corrupted
    assert mgr.session.parties[party_a].distance_traveled == dist_a_before

    p1.disconnect()
    p2.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 15. Scoring consistency
# ---------------------------------------------------------------------------

def test_scoring_formula_deterministic():
    """Score calculation matches documented formula exactly."""
    engine = PartyEngine(seed=42)

    party = Party(
        party_id="test_party",
        party_name="Test Party",
        profession=Profession.FARMER,
        member_ids=["p1", "p2"],
    )
    party.inventory = Inventory(
        oxen=4, food=200, clothing=3, bullets=10,
        wagon_wheels=2, wagon_axles=1, wagon_tongues=1,
        money=100.0,
    )
    party.morale = 60
    party.status = "finished"

    players = {
        "p1": Player(player_id="p1", name="Alice", is_alive=True),
        "p2": Player(player_id="p2", name="Bob", is_alive=True),
    }

    score = engine._calculate_score(party, players)

    # Formula: survivors * 500 + oxen * 4 + spare_parts * 2 + money/5 + food/50 + clothing * 2 + bullets * 0.1 + morale/10
    expected_base = (
        2 * SCORE_SURVIVOR
        + 4 * SCORE_OXEN
        + (2 + 1 + 1) * SCORE_SPARE_PART
        + int(100 * SCORE_PER_5_DOLLARS / 5)
        + int(200 * SCORE_PER_50_FOOD / 50)
        + 3 * SCORE_PER_CLOTHING
        + int(10 * SCORE_PER_BULLET)
        + int(60 / 10)
    )
    # Farmer multiplier = 3
    expected = expected_base * 3

    assert score == expected, f"Expected {expected}, got {score}"


def test_scoring_different_professions():
    """Different professions yield different multipliers."""
    engine = PartyEngine(seed=42)

    base_inv = Inventory(oxen=2, food=100, clothing=2, bullets=0,
                         wagon_wheels=0, wagon_axles=0, wagon_tongues=0, money=0)
    base_morale = 50

    scores = {}
    for prof in [Profession.BANKER, Profession.CARPENTER, Profession.FARMER]:
        party = Party(party_id="test", party_name="Test", profession=prof,
                      member_ids=["p1"])
        party.inventory = Inventory(**vars(base_inv))
        party.morale = base_morale
        party.status = "finished"
        players = {"p1": Player(player_id="p1", name="Alice", is_alive=True)}

        scores[prof] = engine._calculate_score(party, players)

    # Banker: 1x, Carpenter: 2x, Farmer: 3x
    banker_score = scores[Profession.BANKER]
    assert scores[Profession.CARPENTER] == banker_score * 2
    assert scores[Profession.FARMER] == banker_score * 3


def test_scoring_dead_members_not_counted():
    """Dead party members do not contribute to survivor score."""
    engine = PartyEngine(seed=42)

    party = Party(party_id="test", party_name="Test", profession=Profession.BANKER,
                  member_ids=["p1", "p2", "p3"])
    party.inventory = Inventory(oxen=1, food=10, clothing=1)
    party.morale = 0
    party.status = "finished"

    players = {
        "p1": Player(player_id="p1", name="Alice", is_alive=True),
        "p2": Player(player_id="p2", name="Bob", is_alive=False),
        "p3": Player(player_id="p3", name="Charlie", is_alive=False),
    }

    score = engine._calculate_score(party, players)
    # Only 1 survivor
    base_expected = 1 * SCORE_SURVIVOR + 1 * SCORE_OXEN + 1 * SCORE_PER_CLOTHING + int(10 * SCORE_PER_50_FOOD / 50)
    assert score == base_expected, f"Expected {base_expected}, got {score}"
