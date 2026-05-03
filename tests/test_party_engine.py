import pytest
from datetime import date
from unittest.mock import MagicMock

from models import Party, Player, Decision, DecisionType, Inventory, Tombstone
from game_data import Pace, Rations, Weather, Terrain, HealthStatus
from party_engine import PartyEngine

@pytest.fixture
def base_party():
    party = Party(party_name="Test Party", pace=Pace.STEADY, rations=Rations.FILLING)
    party.inventory = Inventory(oxen=4, food=200, bullets=100, money=500, wagon_wheels=1)
    party.member_ids = ["p1", "p2"]
    return party

@pytest.fixture
def base_players():
    return {
        "p1": Player(player_id="p1", name="Alice", is_alive=True, health_status=HealthStatus.HEALTHY),
        "p2": Player(player_id="p2", name="Bob", is_alive=True, health_status=HealthStatus.HEALTHY),
    }

def test_calculate_travel(base_party):
    engine = PartyEngine(seed=42)
    # STEADY pace (12), WARM weather (1.0), PRAIRIE terrain (1.0 default)
    # Oxen factor is min(1.0, 4/4) = 1.0
    miles = engine._calculate_travel(base_party, Weather.WARM, Terrain.PRAIRIE)
    assert miles == 12

    # Change pace and terrain
    base_party.pace = Pace.GRUELING # 20 base
    miles_grueling = engine._calculate_travel(base_party, Weather.WARM, Terrain.MOUNTAINS)
    # 20 * 1.0 (weather) * 0.7 (mountains) * 1.0 (oxen) = 14
    assert miles_grueling == 14

def test_consume_food(base_party):
    engine = PartyEngine(seed=42)
    # FILLING rations = 3 lbs/person/day. 2 alive players = 6 lbs.
    consumed = engine._consume_food(base_party, alive_count=2)
    assert consumed == 6
    assert base_party.inventory.food == 194

def test_apply_decision(base_party, base_players):
    engine = PartyEngine(seed=42)
    
    decision = Decision(party_id=base_party.party_id, decision_type=DecisionType.PACE)
    base_party.decision_pending = decision
    
    party, players, events = engine.apply_decision(base_party, base_players, "Strenuous")
    assert party.pace == Pace.STRENUOUS
    assert party.decision_pending is None
    assert events[0]["message"] == "Pace set to Strenuous."

def test_resolve_hunt(base_party):
    engine = PartyEngine(seed=42)
    
    # Simulate a hunt where they hit 2 animals
    # 2 shots hit -> uses 2 bullets.
    # engine.rng is used for food per hit. Since we don't mock it, we just check bounds.
    party, result = engine.resolve_hunt(base_party, shots_hit=2)
    
    assert party.inventory.bullets == 98
    assert result["bullets_used"] == 2
    assert result["shots_fired"] == 2
    assert party.status == "traveling"
    assert party.inventory.food > 200  # Started with 200, should have gained some
    assert party.hunting_region_depletion > 0.0

def test_apply_trail_event_broken_wheel(base_party, base_players):
    engine = PartyEngine(seed=42)
    event = {"id": "broken_wheel", "description": "A wagon wheel has broken!", "requires_supplies": True}
    
    assert base_party.inventory.wagon_wheels == 1
    
    party, players, msg = engine._apply_trail_event(base_party, base_players, event)
    
    assert party.inventory.wagon_wheels == 0
    assert "used a spare wheel" in msg
    assert party.status != "decision"  # Did not stop

def test_apply_trail_event_thief(base_party, base_players):
    engine = PartyEngine(seed=42)
    # Mocking RNG to ensure theft triggers
    engine.rng.random = MagicMock(return_value=0.1)
    
    event = {"id": "thief", "description": "A thief came in the night and stole supplies!", "requires_supplies": False}
    
    party, players, msg = engine._apply_trail_event(base_party, base_players, event)
    
    # 200 food -> stolen 50
    # 500 money -> stolen 50
    # 4 oxen -> stolen 1 (30% chance, mocked 0.1)
    assert party.inventory.food == 150
    assert party.inventory.money == 450
    assert party.inventory.oxen == 3
    assert "Stolen" in msg
    
def test_tick_advances_day(base_party, base_players):
    engine = PartyEngine(seed=42)
    
    base_party.status = "traveling"
    
    # Just verify that a tick moves distance
    party, players, events = engine.tick(base_party, base_players, date(1848, 5, 1), Weather.WARM)
    
    assert party.distance_traveled > 0
    assert party.inventory.food < 200
    assert party.global_date == date(1848, 5, 1)
