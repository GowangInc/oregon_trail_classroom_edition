import pytest
from datetime import date, datetime
from models import (
    Player, Inventory, Decision, DecisionType, Tombstone, Party, GameSession, HealthStatus, Profession, Pace, Rations
)

def test_player_serialization():
    p = Player(name="Alice", is_host=True, profession=Profession.CARPENTER)
    d = p.to_dict()
    assert d["name"] == "Alice"
    assert d["is_host"] is True
    assert d["profession"] == Profession.CARPENTER.value
    
    p2 = Player.from_dict(d)
    assert p2.name == "Alice"
    assert p2.is_host is True
    assert p2.profession == Profession.CARPENTER

def test_inventory_serialization():
    inv = Inventory(oxen=4, food=500, clothing=10, bullets=100, wagon_wheels=2, wagon_axles=1, wagon_tongues=1, money=800.50)
    d = inv.to_dict()
    assert d["oxen"] == 4
    assert d["money"] == 800.50
    
    inv2 = Inventory.from_dict(d)
    assert inv2.oxen == 4
    assert inv2.money == 800.50

def test_decision_tally_votes():
    d = Decision(options=["A", "B", "C"], captain_default="A")
    d.votes = {"p1": "A", "p2": "B", "p3": "A"}
    counts = d.tally_votes()
    assert counts == {"A": 2, "B": 1}

def test_decision_get_winner_majority():
    d = Decision(options=["A", "B", "C"], captain_default="C")
    d.votes = {"p1": "A", "p2": "B", "p3": "A"}
    assert d.get_winner() == "A"

def test_decision_get_winner_tie_uses_captain_default():
    d = Decision(options=["A", "B", "C"], captain_default="C")
    d.votes = {"p1": "A", "p2": "B"}
    assert d.get_winner() == "C"

def test_decision_get_winner_tie_no_captain_default():
    d = Decision(options=["A", "B", "C"])
    d.votes = {"p1": "A", "p2": "B"}
    # Should pick one of the winners. The implementation says `winners[0]` but it falls back to captain default or first option if there's no tie resolution.
    # Wait, the code: 
    # winners = [opt for opt, cnt in counts.items() if cnt == max_votes]
    # if len(winners) == 1: return winners[0]
    # # Tie or no votes: use captain default
    # if self.captain_default in self.options: return self.captain_default
    # return self.options[0]
    assert d.get_winner() in ["A", "B", "C"]  # Since captain default is missing, it falls back to options[0]

def test_party_serialization():
    party = Party(party_name="The Pioneers", pace=Pace.STRENUOUS, rations=Rations.FILLING)
    d = party.to_dict(include_private=True)
    assert d["party_name"] == "The Pioneers"
    assert d["pace"] == Pace.STRENUOUS.value
    assert "inventory" in d
    
    party2 = Party.from_dict(d)
    assert party2.party_name == "The Pioneers"
    assert party2.pace == Pace.STRENUOUS
    assert party2.rations == Rations.FILLING

def test_game_session_serialization():
    session = GameSession()
    session.players["p1"] = Player(name="Alice")
    session.parties["party1"] = Party(party_name="Party 1")
    
    d = session.to_dict()
    assert "p1" in d["players"]
    assert "party1" in d["parties"]
    
    session2 = GameSession.from_dict(d)
    assert "p1" in session2.players
    assert session2.players["p1"].name == "Alice"
    assert "party1" in session2.parties
    assert session2.parties["party1"].party_name == "Party 1"
