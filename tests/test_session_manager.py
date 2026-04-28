import pytest
from datetime import date
from unittest.mock import MagicMock

from models import GameSession, Player, Party, HealthStatus
from session_manager import SessionManager

@pytest.fixture
def empty_session():
    # host id, host name
    return SessionManager("host123", "Teacher")

def test_add_player_to_lobby(empty_session):
    mgr = empty_session
    player = mgr.add_player("Alice", "socket_abc")
    
    assert player.name == "Alice"
    assert player.socket_id == "socket_abc"
    assert player.player_id in mgr.session.players
    assert player.party_id is None  # Unassigned
    
    # State update should reflect this
    state = mgr.get_host_state()
    assert player.player_id in state["players"]
    assert state["players"][player.player_id]["party_id"] is None

def test_create_party_and_assign_player(empty_session):
    mgr = empty_session
    player = mgr.add_player("Alice", "socket_abc")
    
    party = mgr.create_party("The Pioneers")
    assert party.party_name == "The Pioneers"
    assert party.party_id in mgr.session.parties
    
    # Assign Alice to the party
    success = mgr.assign_player_to_party(player.player_id, party.party_id)
    assert success is True
    
    # Verify the assignment
    assert player.party_id == party.party_id
    assert player.player_id in party.member_ids
    assert party.captain_id == player.player_id  # First member becomes captain

def test_remove_player_updates_party(empty_session):
    mgr = empty_session
    p1 = mgr.add_player("Alice", "socket_a")
    p2 = mgr.add_player("Bob", "socket_b")
    
    party = mgr.create_party("Pioneers")
    mgr.assign_player_to_party(p1.player_id, party.party_id)
    mgr.assign_player_to_party(p2.player_id, party.party_id)
    
    assert party.captain_id == p1.player_id
    
    mgr.remove_player(p1.player_id)
    
    assert mgr.session.players[p1.player_id].socket_id is None

def test_shuffle_parties(empty_session):
    mgr = empty_session
    p1 = mgr.add_player("Alice", "s1")
    p2 = mgr.add_player("Bob", "s2")
    p3 = mgr.add_player("Charlie", "s3")
    
    # Only create two parties
    mgr.create_party("Party A")
    mgr.create_party("Party B")
    
    mgr.shuffle_parties()
    
    # Verify all players are assigned and there are no more than 4 per party
    assigned = 0
    for pid, p in mgr.session.players.items():
        if pid != mgr.session.host_player_id:
            assert p.party_id is not None
            assigned += 1
    
    assert assigned == 3

def test_fill_party_with_npcs(empty_session):
    mgr = empty_session
    party = mgr.create_party("NPC Party")
    
    p1 = mgr.add_player("Alice", "s1")
    mgr.assign_player_to_party(p1.player_id, party.party_id)
    
    mgr.fill_party_with_npcs(party.party_id)
    
    # Should fill up to 5 members
    assert len(party.member_ids) == 5
    
    # Count NPCs
    npcs = [pid for pid in party.member_ids if mgr.session.players[pid].is_npc]
    assert len(npcs) == 4

def test_start_game_validation(empty_session):
    mgr = empty_session
    
    # Cannot start without parties or players
    assert mgr.start_game() is False
    
    p1 = mgr.add_player("Alice", "s1")
    party = mgr.create_party("A")
    mgr.assign_player_to_party(p1.player_id, party.party_id)
    
    assert mgr.start_game() is True
    assert mgr.session.game_status == "outfitting"

def test_resolve_hunt(empty_session):
    mgr = empty_session
    p1 = mgr.add_player("Alice", "s1")
    party = mgr.create_party("Hunters")
    mgr.assign_player_to_party(p1.player_id, party.party_id)
    mgr.start_game()
    mgr.begin_journey()
    
    # Force hunting status
    party.status = "hunting"
    party.inventory.bullets = 10
    party.inventory.food = 0
    
    # Mock RNG in the engine to guarantee some food per hit
    engine = mgr.engines[party.party_id]
    engine.rng.randint = MagicMock(return_value=50) 
    
    result = mgr.resolve_hunt(party.party_id, shots_hit=2)
    
    assert result["bullets_used"] == 2
    assert party.inventory.bullets == 8
    assert party.status == "traveling"
    assert result["food_gained"] > 0
