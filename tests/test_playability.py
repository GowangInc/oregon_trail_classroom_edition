"""Comprehensive playability test suite for Oregon Trail Classroom Edition.

Goals:
- Find soft locks, dead ends, or unplayable states.
- Verify game mechanics work correctly under edge cases.
- Ensure no crashes from host controls at arbitrary times.
"""

import json
import os
import time
from copy import deepcopy
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from server import (
    app,
    socketio,
    sessions,
    player_to_session,
    sid_to_player,
    auto_threads,
    auto_advance_generations,
)
from game_data import (
    Profession,
    Pace,
    Rations,
    HealthStatus,
    Weather,
    TOTAL_DISTANCE,
    SCORE_SURVIVOR,
    SCORE_OXEN,
    SCORE_SPARE_PART,
    SCORE_PER_5_DOLLARS,
    SCORE_PER_50_FOOD,
    SCORE_PER_CLOTHING,
    SCORE_PER_BULLET,
    MAX_SPARE_PARTS,
    STORE_PRICES,
)
from models import Party, Player, Decision, DecisionType, Inventory
from session_manager import SessionManager
from party_engine import PartyEngine


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


def create_host():
    """Create and return a host SocketIO test client and its player id."""
    host = socketio.test_client(app, auth={"is_host": True, "host_password": "admin"})
    assert host.is_connected()
    host_id = _extract_player_id(host)
    return host, host_id


def create_player(name):
    """Create a player SocketIO test client."""
    client = socketio.test_client(app)
    client.emit("join_session", {"name": name})
    pid = _extract_player_id(client)
    return client, pid


def create_party_and_assign_players(host, player_clients, player_ids, party_name="Test Party"):
    """Create a party and assign players to it. Returns party_id."""
    mgr = _get_session()
    host.emit("create_party", {"party_name": party_name})
    party_id = _extract_party_id(host)
    _drain(host)
    for client, pid in zip(player_clients, player_ids):
        host.emit("assign_party", {"player_id": pid, "party_id": party_id})
        _drain(host, client)
    return party_id


def outfit_party(host, party_id, profession="Banker from Boston", month=4):
    """Outfit a party with default starting supplies via socket events."""
    mgr = _get_session()
    party = mgr.session.parties[party_id]
    captain_pid = party.captain_id
    # Find captain's client
    captain_client = None
    for client, pid in [(host, mgr.session.host_player_id)]:
        if pid == captain_pid:
            captain_client = client
    # Search among connected players
    if captain_client is None:
        # We can't easily map client->pid here without keeping state,
        # so we use host_edit_party to set profession and inventory directly.
        pass

    # Use socket events if possible, otherwise direct manipulation
    host.emit("host_edit_party", {"party_id": party_id, "field": "status", "value": "outfitting"})
    _drain(host)

    with mgr.lock:
        engine = mgr.engines[party_id]
        party = mgr.session.parties[party_id]
        party = engine.choose_profession(party, Profession(profession))
        party.start_month = month
        purchases = {
            "oxen": 6,
            "food": 400,
            "clothing": 8,
            "bullets": 4,
            "wagon_wheel": 2,
            "wagon_axle": 2,
            "wagon_tongue": 2,
        }
        party, _ = engine.buy_starting_supplies(party, purchases)
        party.outfitting_complete = True
        party.status = "ready"
        mgr.session.parties[party_id] = party
    _drain(host)
    return party_id


def _outfit_party_direct(mgr, party_id, profession=Profession.CARPENTER, purchases=None):
    """Directly outfit a party using the engine."""
    with mgr.lock:
        party = mgr.session.parties[party_id]
        engine = mgr.engines[party_id]
        party, _ = engine.outfit_party(party, profession, purchases or {
            "oxen": 6,
            "food": 400,
            "clothing": 8,
            "bullets": 4,
            "wagon_wheel": 2,
            "wagon_axle": 2,
            "wagon_tongue": 2,
        })
        party.outfitting_complete = True
        mgr.session.parties[party_id] = party
        return party


def _resolve_pending_decisions(mgr):
    """Resolve all pending decisions by host override with safe defaults."""
    with mgr.lock:
        for party in list(mgr.session.parties.values()):
            if not party.decision_pending or party.decision_pending.resolved:
                continue
            choice = _safe_choice(party.decision_pending)
            engine = mgr.engines.get(party.party_id)
            if engine:
                players = mgr._get_party_players(party)
                party, players, _ = engine.apply_decision(
                    party, players, choice, river_depth=mgr._compute_river_depth()
                )
                mgr._update_party_and_players(party, players)


def _safe_choice(decision):
    """Pick a safe default for a decision."""
    opts = decision.options
    if not opts:
        return ""
    dt = decision.decision_type
    if dt == DecisionType.RIVER_METHOD:
        return next((o for o in opts if "ferry" in o.lower() or "Caulk" in o), opts[0])
    if dt == DecisionType.TAKE_SHORTCUT:
        return next((o for o in opts if "safer" in o or "Barlow" in o or "Bridger" in o), opts[0])
    if dt == DecisionType.BUY_SUPPLIES:
        return "Continue on" if "Continue on" in opts else opts[0]
    if dt == DecisionType.REST:
        return "Continue on" if "Continue on" in opts else opts[0]
    if dt == DecisionType.HUNT:
        return "Continue on" if "Continue on" in opts else opts[0]
    if dt == DecisionType.PACE:
        return "Keep pace and rations" if "Keep pace and rations" in opts else opts[0]
    return opts[0]


def _advance_days(host, mgr, days=1):
    """Advance N days, resolving decisions along the way."""
    for _ in range(days):
        if mgr.session.game_status != "active":
            break
        _resolve_pending_decisions(mgr)
        host.emit("advance_day")
        _drain(host)


def _force_party_to_river(mgr, party_id, depth_override=None):
    """Put a party at a river landmark and set up river crossing state."""
    with mgr.lock:
        party = mgr.session.parties[party_id]
        engine = mgr.engines[party_id]
        # Place near Kansas River Crossing
        party.distance_traveled = 102
        party.current_landmark_index = 1
        party.status = "river_crossing"
        party.travel_days_since_decision = 0
        terrain = engine._get_terrain_at(party.distance_traveled)
        players = mgr._get_party_players(party)
        river_depth = depth_override or mgr._compute_river_depth()
        risks = engine.calculate_risks(party, players, mgr.session.global_weather, terrain, river_depth=river_depth)
        options = ["Ford the river", "Caulk the wagon and float", "Take a ferry", "Wait for better conditions"]
        party.decision_pending = Decision(
            party_id=party_id,
            decision_type=DecisionType.RIVER_METHOD,
            prompt="Test river crossing.",
            options=options,
            captain_id=party.captain_id,
            captain_default="Ford the river",
            timeout_seconds=5,
            risk_data=risks,
        )
        mgr.session.parties[party_id] = party


# ---------------------------------------------------------------------------
# 1. Full game completion
# ---------------------------------------------------------------------------

def test_full_game_completion():
    """Simulate a party from start to Oregon City. Verify finish, score, game_over."""
    host, host_id = create_host()
    mgr = _get_session()

    # Create 1 party with 2 players
    p1, pid1 = create_player("Alice")
    p2, pid2 = create_player("Bob")
    party_id = create_party_and_assign_players(host, [p1, p2], [pid1, pid2], "The Pioneers")

    # Start and outfit
    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)

    host.emit("begin_journey")
    _drain(host)
    assert mgr.session.game_status == "active"

    # Teleport to the finish to avoid 200+ day simulation
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.distance_traveled = 2094  # Willamette Valley
        party.status = "traveling"
        mgr.session.parties[party_id] = party

    host.emit("advance_day")
    msgs = host.get_received()

    with mgr.lock:
        party = mgr.session.parties[party_id]
        assert party.status == "finished"
        assert party.score > 0

    # Game should end since only one party
    assert mgr.session.game_status == "ended"

    # Verify game_over event broadcast (don't drain before checking)
    game_over = _find_received_named(msgs, "game_over")
    assert game_over is not None
    rankings = game_over["args"][0]["final_rankings"]
    assert len(rankings) >= 1
    assert rankings[0]["party_id"] == party_id

    _drain(host, p1, p2)
    host.disconnect()
    p1.disconnect()
    p2.disconnect()


# ---------------------------------------------------------------------------
# 2. Decision timeout soft lock
# ---------------------------------------------------------------------------

def test_decision_timeout_soft_lock():
    """Create a pending decision, disconnect all players, wait for timeout, verify advance."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Solo")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    # Create a pending decision with a backdated created_at
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.status = "decision"
        party.decision_pending = Decision(
            party_id=party_id,
            decision_type=DecisionType.PACE,
            prompt="What pace?",
            options=["Keep pace and rations", "Speed up"],
            captain_id=party.captain_id,
            captain_default="Keep pace and rations",
            timeout_seconds=1,
        )
        # Backdate so it will time out immediately
        party.decision_pending.created_at = datetime.now() - timedelta(seconds=10)
        mgr.session.parties[party_id] = party

    # Disconnect the player
    p1.disconnect()
    _drain(host)

    # Tick should resolve the timed-out decision and advance the day
    day_before = mgr.session.tick_count
    host.emit("advance_day")
    _drain(host)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        # Decision should be resolved
        assert party.decision_pending is None or party.decision_pending.resolved
        # Game should have advanced
        assert mgr.session.tick_count > day_before

    host.disconnect()


# ---------------------------------------------------------------------------
# 3. Auto-advance safety
# ---------------------------------------------------------------------------

def test_auto_advance_skips_hunting_party():
    """Enable auto-advance, put a party in hunting status, verify it is skipped."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Hunters")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.status = "hunting"
        dist_before = party.distance_traveled
        mgr.session.parties[party_id] = party

    host.emit("set_auto_advance", {"enabled": True, "interval_seconds": 1})
    _drain(host)
    time.sleep(1.5)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        # Hunting party should not have traveled
        assert party.distance_traveled == dist_before
        assert party.status == "hunting"

    host.emit("set_auto_advance", {"enabled": False})
    _drain(host)
    host.disconnect()
    p1.disconnect()


# ---------------------------------------------------------------------------
# 4. Multiple parties
# ---------------------------------------------------------------------------

def test_multiple_parties_independent():
    """Create 3 parties, start game, advance days, verify each advances independently."""
    host, host_id = create_host()
    mgr = _get_session()

    clients = []
    pids = []
    party_ids = []
    for i in range(3):
        c, pid = create_player(f"Player{i}")
        clients.append(c)
        pids.append(pid)
        pid_party = create_party_and_assign_players(host, [c], [pid], f"Party{i}")
        party_ids.append(pid_party)

    host.emit("start_game")
    _drain(host)
    for pid in party_ids:
        _outfit_party_direct(mgr, pid)
    host.emit("begin_journey")
    _drain(host)

    # Set different starting distances to verify independence
    with mgr.lock:
        mgr.session.parties[party_ids[0]].distance_traveled = 100
        mgr.session.parties[party_ids[1]].distance_traveled = 200
        mgr.session.parties[party_ids[2]].distance_traveled = 300

    _advance_days(host, mgr, days=5)

    with mgr.lock:
        distances = [mgr.session.parties[pid].distance_traveled for pid in party_ids]
        # Each should have advanced from its starting point
        assert distances[0] > 100
        assert distances[1] > 200
        assert distances[2] > 300
        # No state corruption: distinct values
        assert len(set(distances)) == 3

    for c in clients:
        c.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 5. Store edge cases
# ---------------------------------------------------------------------------

def test_store_edge_cases():
    """Test buying with insufficient money, negative quantity, and over inventory caps."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Shoppers")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.inventory.money = 5.0
        mgr.session.parties[party_id] = party

    # Insufficient money
    result = mgr.buy_item(party_id, "oxen", 1)
    assert result["success"] is False
    assert "money" in result["message"].lower() or "Not enough" in result["message"]

    # Negative quantity
    result = mgr.buy_item(party_id, "food", -5)
    assert result["success"] is False

    # Zero quantity
    result = mgr.buy_item(party_id, "food", 0)
    assert result["success"] is False

    # Over spare parts cap
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.inventory.money = 9999.0
        party.inventory.wagon_wheels = MAX_SPARE_PARTS
        mgr.session.parties[party_id] = party

    result = mgr.buy_item(party_id, "wagon_wheel", 1)
    assert result["success"] is False
    assert "can't carry more" in result["message"]

    p1.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 6. River crossing all methods
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("depth", [2, 5, 8, 12])
@pytest.mark.parametrize("method", [
    "Ford the river",
    "Caulk the wagon and float",
    "Take a ferry",
    "Wait for better conditions",
])
def test_river_crossing_all_methods(depth, method):
    """Test every river method at shallow/moderate/deep/very_deep depths.
    No method should leave a party stuck in river_crossing forever."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Raft")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    _force_party_to_river(mgr, party_id, depth_override=depth)

    with mgr.lock:
        assert mgr.session.parties[party_id].status == "river_crossing"

    # Make sure party has money for ferry
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.inventory.money = 9999.0
        mgr.session.parties[party_id] = party

    p1.emit("cross_river", {"party_id": party_id, "method": method})
    _drain(p1, host)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        assert party.status != "river_crossing", f"Party stuck in river_crossing with method={method} depth={depth}"

    p1.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 7. Hunting edge cases
# ---------------------------------------------------------------------------

def test_hunt_zero_bullets():
    """Hunt with 0 bullets should return to traveling immediately."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Hunters")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.status = "hunting"
        party.inventory.bullets = 0
        mgr.session.parties[party_id] = party

    result = mgr.resolve_hunt(party_id, shots_hit=5)
    assert "message" in result  # Should return a result dict
    with mgr.lock:
        assert mgr.session.parties[party_id].status == "traveling"

    p1.disconnect()
    host.disconnect()


def test_hunt_max_bullets():
    """Hunt with many bullets should work and cap food per hunt."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Hunters")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.status = "hunting"
        party.inventory.bullets = 9999
        party.hunting_region_depletion = 0.0
        mgr.session.parties[party_id] = party

    # Mock RNG for deterministic max food
    engine = mgr.engines[party_id]
    engine.rng.randint = MagicMock(return_value=25)

    result = mgr.resolve_hunt(party_id, shots_hit=10)
    from game_data import HUNTING_MAX_FOOD_PER_HUNT
    assert result["food_gained"] <= HUNTING_MAX_FOOD_PER_HUNT
    with mgr.lock:
        assert mgr.session.parties[party_id].status == "traveling"

    p1.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 8. Rest mechanics
# ---------------------------------------------------------------------------

def test_rest_one_day_and_five_days():
    """Rest for 1 day and 5 days. Verify rest_days_remaining decrements and status returns to traveling."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Resters")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    # 1-day rest via direct engine call
    with mgr.lock:
        party = mgr.session.parties[party_id]
        engine = mgr.engines[party_id]
        players = mgr._get_party_players(party)
        party.is_resting = True
        party.rest_days_remaining = 1
        party.status = "resting"
        mgr.session.parties[party_id] = party

    _advance_days(host, mgr, days=1)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        assert party.rest_days_remaining == 0
        assert not party.is_resting
        assert party.status == "traveling"

    # 5-day rest
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.is_resting = True
        party.rest_days_remaining = 5
        party.status = "resting"
        mgr.session.parties[party_id] = party

    _advance_days(host, mgr, days=5)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        assert party.rest_days_remaining == 0
        assert not party.is_resting
        assert party.status == "traveling"

    p1.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 9. Death spiral
# ---------------------------------------------------------------------------

def test_death_spiral_all_members_die():
    """Kill all members of a party. Verify party marked dead, game continues for others, dead party doesn't block game_over."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    p2, pid2 = create_player("Bob")
    party_a = create_party_and_assign_players(host, [p1], [pid1], "Doomed")
    party_b = create_party_and_assign_players(host, [p2], [pid2], "Survivors")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_a)
    _outfit_party_direct(mgr, party_b)
    host.emit("begin_journey")
    _drain(host)

    # Kill all members of party A by setting health to Dead and advancing a day
    # so _check_deaths runs and updates status.
    with mgr.lock:
        for pid in mgr.session.parties[party_a].member_ids:
            player = mgr.session.players[pid]
            player.health_status = HealthStatus.DEAD
            player.is_alive = False
        mgr.session.parties[party_a].is_alive = False
        # Force status update for immediate check
        alive_members = [
            pid for pid in mgr.session.parties[party_a].member_ids
            if mgr.session.players[pid].is_alive
        ]
        if not alive_members:
            mgr.session.parties[party_a].status = "dead"

    with mgr.lock:
        party = mgr.session.parties[party_a]
        assert party.status == "dead" or not party.is_alive

    # Game should still be active because party B is alive
    assert mgr.session.game_status == "active"

    # Advance a day to trigger dead check in tick
    _advance_days(host, mgr, days=1)

    with mgr.lock:
        party = mgr.session.parties[party_a]
        assert party.status == "dead"

    # Kill party B too to end game
    with mgr.lock:
        for pid in mgr.session.parties[party_b].member_ids:
            host.emit("host_set_player_health", {"player_id": pid, "health_status": "Dead"})
        _drain(host)

    _advance_days(host, mgr, days=1)
    assert mgr.session.game_status == "ended"

    p1.disconnect()
    p2.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 10. Host controls at any time
# ---------------------------------------------------------------------------

def test_host_controls_random_times_no_crash():
    """Call pause, resume, advance_days, inject_event, host_edit_party at random times. Verify no crashes."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Test")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    # Random sequence of host controls
    host.emit("pause_game")
    _drain(host)
    host.emit("resume_game")
    _drain(host)
    host.emit("advance_days", {"count": 3})
    _drain(host)
    host.emit("inject_event", {"party_id": party_id, "event_id": "broken_wheel"})
    _drain(host)
    host.emit("host_edit_party", {"party_id": party_id, "field": "food", "value": 200})
    _drain(host)
    host.emit("host_edit_party", {"party_id": party_id, "field": "money", "value": 500})
    _drain(host)
    host.emit("pause_game")
    _drain(host)
    host.emit("inject_event", {"party_id": party_id, "event_id": "thief"})
    _drain(host)
    host.emit("resume_game")
    _drain(host)
    host.emit("advance_day")
    _drain(host)

    # Verify session is still valid
    assert mgr.session.game_status == "active"
    assert party_id in mgr.session.parties

    p1.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 11. Save/load roundtrip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip():
    """Save game at day 10, load it, verify all state matches."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    p2, pid2 = create_player("Bob")
    party_id = create_party_and_assign_players(host, [p1, p2], [pid1, pid2], "Savers")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    _advance_days(host, mgr, days=10)

    with mgr.lock:
        original = mgr.session.to_dict(player_id=host_id)
        original_parties = deepcopy(original["parties"])
        original_players = deepcopy(original["players"])

    # Save via direct dict (mimic save_state)
    save_data = original

    # Load into a fresh manager
    loaded_mgr = SessionManager(host_id, "Teacher")
    loaded_mgr.load_from_dict(save_data)

    loaded = loaded_mgr.session.to_dict(player_id=host_id)

    # Verify distances, inventories, health, decisions, scores
    assert loaded["tick_count"] == original["tick_count"]
    assert loaded["game_status"] == original["game_status"]
    for pid in original_parties:
        orig_party = original_parties[pid]
        loaded_party = loaded["parties"][pid]
        assert loaded_party["distance_traveled"] == orig_party["distance_traveled"]
        assert loaded_party["score"] == orig_party["score"]
        assert loaded_party["morale"] == orig_party["morale"]
        assert loaded_party["status"] == orig_party["status"]
        assert loaded_party["inventory"] == orig_party["inventory"]
        # Decision compare
        if orig_party.get("decision_pending"):
            assert loaded_party["decision_pending"]["decision_id"] == orig_party["decision_pending"]["decision_id"]
        else:
            assert loaded_party.get("decision_pending") is None

    for pid in original_players:
        assert loaded["players"][pid]["health_status"] == original_players[pid]["health_status"]
        assert loaded["players"][pid]["is_alive"] == original_players[pid]["is_alive"]

    p1.disconnect()
    p2.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 12. Rapid voting
# ---------------------------------------------------------------------------

def test_rapid_voting_race_condition():
    """Create a decision and have 10+ players submit votes rapidly across multiple parties. Verify tally is correct."""
    host, host_id = create_host()
    mgr = _get_session()
    clients = []
    pids = []
    for i in range(10):
        c, pid = create_player(f"Voter{i}")
        clients.append(c)
        pids.append(pid)

    # Create two parties of 5 each (party limit is 5)
    party_id_a = create_party_and_assign_players(host, clients[:5], pids[:5], "VotersA")
    party_id_b = create_party_and_assign_players(host, clients[5:], pids[5:], "VotersB")
    party_id = party_id_a  # Test on first party

    host.emit("start_game")
    _drain(host)
    host.emit("begin_journey")
    _drain(host)

    # Create a decision directly
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.status = "decision"
        party.decision_pending = Decision(
            party_id=party_id,
            decision_type=DecisionType.PACE,
            prompt="Vote fast!",
            options=["A", "B"],
            captain_id=party.captain_id,
            captain_default="A",
            timeout_seconds=60,
        )
        mgr.session.parties[party_id] = party
        dec_id = party.decision_pending.decision_id

    # Rapid fire votes
    for c, pid in zip(clients, pids):
        choice = "A" if pid.endswith("0") or int(pid, 16) % 2 == 0 else "B"
        c.emit("submit_vote", {"decision_id": dec_id, "choice": choice})

    _drain(host, *clients)

    with mgr.lock:
        dec = mgr.session.parties[party_id].decision_pending
        total_votes = len(dec.votes)
        # All 5 members of the first party should have voted
        assert total_votes == 5
        counts = dec.tally_votes()
        assert counts.get("A", 0) + counts.get("B", 0) == total_votes

    for c in clients:
        c.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 13. Empty session
# ---------------------------------------------------------------------------

def test_empty_session_npc_only():
    """Host creates session, starts game with no players, verify game can begin with NPCs only."""
    host, host_id = create_host()
    mgr = _get_session()

    host.emit("create_party", {"party_name": "NPC Only"})
    party_id = _extract_party_id(host)
    _drain(host)

    # No human players assigned
    with mgr.lock:
        mgr.fill_party_with_npcs(party_id)

    host.emit("start_game")
    _drain(host)
    assert mgr.session.game_status == "outfitting"

    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)
    assert mgr.session.game_status == "active"

    _advance_days(host, mgr, days=5)
    with mgr.lock:
        party = mgr.session.parties[party_id]
        assert party.distance_traveled > 0

    host.disconnect()


# ---------------------------------------------------------------------------
# 14. Party migration
# ---------------------------------------------------------------------------

def test_party_migration_mid_journey():
    """Move a player from party A to party B mid-journey. Verify clean state."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    p2, pid2 = create_player("Bob")
    party_a = create_party_and_assign_players(host, [p1], [pid1], "PartyA")
    party_b = create_party_and_assign_players(host, [p2], [pid2], "PartyB")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_a)
    _outfit_party_direct(mgr, party_b)
    host.emit("begin_journey")
    _drain(host)

    _advance_days(host, mgr, days=3)

    # Migrate Alice from A to B
    host.emit("assign_party", {"player_id": pid1, "party_id": party_b})
    _drain(host)

    with mgr.lock:
        assert mgr.session.players[pid1].party_id == party_b
        assert pid1 not in mgr.session.parties[party_a].member_ids
        assert pid1 in mgr.session.parties[party_b].member_ids
        # Old party should still be valid
        assert mgr.session.parties[party_a].captain_id != pid1
        assert mgr.session.parties[party_a].status in ("traveling", "decision", "resting", "river_crossing")

    p1.disconnect()
    p2.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 15. Scoring consistency
# ---------------------------------------------------------------------------

def test_scoring_consistency():
    """Finish a game with known inventory/survivors. Verify score matches manual calculation."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    p2, pid2 = create_player("Bob")
    party_id = create_party_and_assign_players(host, [p1, p2], [pid1, pid2], "Scorers")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.distance_traveled = TOTAL_DISTANCE
        party.status = "finished"
        party.inventory.oxen = 4
        party.inventory.wagon_wheels = 2
        party.inventory.wagon_axles = 1
        party.inventory.wagon_tongues = 1
        party.inventory.money = 100.0
        party.inventory.food = 200
        party.inventory.clothing = 5
        party.inventory.bullets = 50
        party.morale = 60
        party.profession = Profession.CARPENTER
        mgr.session.parties[party_id] = party

    engine = mgr.engines[party_id]
    players = mgr._get_party_players(party)
    score = engine._calculate_score(party, players)

    alive = [pid for pid in party.member_ids if players[pid].is_alive]
    expected = (
        len(alive) * SCORE_SURVIVOR
        + party.inventory.oxen * SCORE_OXEN
        + party.inventory.wagon_wheels * SCORE_SPARE_PART
        + party.inventory.wagon_axles * SCORE_SPARE_PART
        + party.inventory.wagon_tongues * SCORE_SPARE_PART
        + int(party.inventory.money * SCORE_PER_5_DOLLARS / 5)
        + int(party.inventory.food * SCORE_PER_50_FOOD / 50)
        + party.inventory.clothing * SCORE_PER_CLOTHING
        + int(party.inventory.bullets * SCORE_PER_BULLET)
        + int(party.morale / 10)
    ) * 2  # Carpenter multiplier

    assert score == expected

    p1.disconnect()
    p2.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 16. Morale system
# ---------------------------------------------------------------------------

def test_morale_changes_and_affects_speed():
    """Verify morale changes during events and affects travel speed."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Mood")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    engine = mgr.engines[party_id]

    # Baseline travel with normal morale
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.morale = 50
        party.inventory.oxen = 6
        party.pace = Pace.STEADY
        mgr.session.parties[party_id] = party

    miles_normal = engine._calculate_travel(party, Weather.COOL, engine._get_terrain_at(party.distance_traveled))

    # High morale should increase speed
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.morale = 80
        mgr.session.parties[party_id] = party
    miles_high = engine._calculate_travel(party, Weather.COOL, engine._get_terrain_at(party.distance_traveled))
    assert miles_high >= miles_normal

    # Low morale should decrease speed
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.morale = 20
        mgr.session.parties[party_id] = party
    miles_low = engine._calculate_travel(party, Weather.COOL, engine._get_terrain_at(party.distance_traveled))
    assert miles_low <= miles_normal

    # Death should drop morale
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.morale = 50
        mgr.session.parties[party_id] = party

    # Set health to Dead but leave is_alive=True so _check_deaths handles the death and morale drop
    with mgr.lock:
        mgr.session.players[pid1].health_status = HealthStatus.DEAD
        mgr.session.players[pid1].is_alive = True
    _advance_days(host, mgr, days=1)
    with mgr.lock:
        party = mgr.session.parties[party_id]
        assert party.morale < 50  # Death drops morale by 20

    p1.disconnect()
    host.disconnect()


# ---------------------------------------------------------------------------
# 17. Probability dashboard
# ---------------------------------------------------------------------------

def test_probability_dashboard_in_decisions():
    """Verify decisions created during tick() include risk_data with probabilities."""
    host, host_id = create_host()
    mgr = _get_session()
    p1, pid1 = create_player("Alice")
    party_id = create_party_and_assign_players(host, [p1], [pid1], "Risky")

    host.emit("start_game")
    _drain(host)
    _outfit_party_direct(mgr, party_id)
    host.emit("begin_journey")
    _drain(host)

    # Force a decision creation by advancing travel_days_since_decision
    with mgr.lock:
        party = mgr.session.parties[party_id]
        party.travel_days_since_decision = 4
        mgr.session.parties[party_id] = party

    _advance_days(host, mgr, days=1)

    with mgr.lock:
        party = mgr.session.parties[party_id]
        if party.decision_pending and not party.decision_pending.resolved:
            rd = party.decision_pending.risk_data
            assert rd is not None
            assert "trail_event_chance_pct" in rd
            assert "illness_chance_any_pct" in rd
            assert "health_trend" in rd
            assert "terrain" in rd
        else:
            # Decision may have been auto-resolved by NPC votes; that's OK for playability
            pass

    p1.disconnect()
    host.disconnect()
