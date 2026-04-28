"""Data models for the Oregon Trail multiplayer game."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid

from game_data import (
    Profession,
    Pace,
    Rations,
    Weather,
    Terrain,
    HealthStatus,
    RiverMethod,
)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
@dataclass
class Player:
    """A single student/player in the game."""
    player_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Unknown"
    socket_id: Optional[str] = None
    party_id: Optional[str] = None
    is_host: bool = False
    is_npc: bool = False
    is_alive: bool = True
    health_status: HealthStatus = HealthStatus.HEALTHY
    profession: Profession = Profession.BANKER
    joined_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "party_id": self.party_id,
            "is_host": self.is_host,
            "is_npc": self.is_npc,
            "is_alive": self.is_alive,
            "health_status": self.health_status.value,
            "profession": self.profession.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Player:
        return cls(
            player_id=data["player_id"],
            name=data["name"],
            party_id=data.get("party_id"),
            is_host=data.get("is_host", False),
            is_npc=data.get("is_npc", False),
            is_alive=data.get("is_alive", True),
            health_status=HealthStatus(data.get("health_status", "Healthy")),
            profession=Profession(data.get("profession", "Banker from Boston")),
        )


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
@dataclass
class Inventory:
    """Shared inventory for a wagon party."""
    oxen: int = 0
    food: int = 0              # pounds
    clothing: int = 0          # sets
    bullets: int = 0           # individual bullets
    wagon_wheels: int = 0
    wagon_axles: int = 0
    wagon_tongues: int = 0
    money: float = 0.0         # dollars

    def to_dict(self) -> Dict[str, Any]:
        return {
            "oxen": self.oxen,
            "food": self.food,
            "clothing": self.clothing,
            "bullets": self.bullets,
            "wagon_wheels": self.wagon_wheels,
            "wagon_axles": self.wagon_axles,
            "wagon_tongues": self.wagon_tongues,
            "money": round(self.money, 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Inventory:
        return cls(**data)


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------
class DecisionType(Enum):
    """Types of decisions that require a party vote."""
    PACE = "pace"
    RATIONS = "rations"
    REST = "rest"
    HUNT = "hunt"
    BUY_SUPPLIES = "buy_supplies"
    RIVER_METHOD = "river_method"
    TRADE_NPC = "trade_npc"
    TRADE_PARTY = "trade_party"
    TAKE_SHORTCUT = "take_shortcut"
    RACE = "race"
    TOMBSTONE_EPITAPH = "tombstone_epitaph"
    VISIT_TOMBSTONE = "visit_tombstone"


@dataclass
class Decision:
    """A pending decision requiring party vote."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    party_id: str = ""
    decision_type: DecisionType = DecisionType.PACE
    prompt: str = ""
    options: List[str] = field(default_factory=list)
    votes: Dict[str, str] = field(default_factory=dict)  # player_id -> choice
    captain_id: str = ""
    captain_default: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 10
    resolved: bool = False
    result: Optional[str] = None

    def tally_votes(self) -> Dict[str, int]:
        """Return vote counts per option."""
        counts: Dict[str, int] = {}
        for choice in self.votes.values():
            counts[choice] = counts.get(choice, 0) + 1
        return counts

    def get_winner(self) -> str:
        """Determine winning option by majority, then captain default, then first option."""
        if self.resolved and self.result:
            return self.result
        counts = self.tally_votes()
        if counts:
            max_votes = max(counts.values())
            winners = [opt for opt, cnt in counts.items() if cnt == max_votes]
            if len(winners) == 1:
                return winners[0]
        # Tie or no votes: use captain default
        if self.captain_default in self.options:
            return self.captain_default
        return self.options[0] if self.options else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "party_id": self.party_id,
            "decision_type": self.decision_type.value,
            "prompt": self.prompt,
            "options": self.options,
            "votes": self.votes,
            "captain_id": self.captain_id,
            "captain_default": self.captain_default,
            "timeout_seconds": self.timeout_seconds,
            "resolved": self.resolved,
            "result": self.result,
        }


# ---------------------------------------------------------------------------
# Tombstone
# ---------------------------------------------------------------------------
@dataclass
class Tombstone:
    """A memorial left when a player dies."""
    player_name: str
    party_name: str
    mile_marker: int
    cause: str
    date: date
    epitaph: str = ""
    written_by_party_id: str = ""
    visited_by_party_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_name": self.player_name,
            "party_name": self.party_name,
            "mile_marker": self.mile_marker,
            "cause": self.cause,
            "date": self.date.isoformat(),
            "epitaph": self.epitaph,
            "written_by_party_id": self.written_by_party_id,
            "visited_by_party_ids": self.visited_by_party_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Tombstone:
        return cls(
            player_name=data["player_name"],
            party_name=data["party_name"],
            mile_marker=data["mile_marker"],
            cause=data["cause"],
            date=date.fromisoformat(data["date"]) if "date" in data else date.today(),
            epitaph=data.get("epitaph", ""),
            written_by_party_id=data.get("written_by_party_id", ""),
            visited_by_party_ids=data.get("visited_by_party_ids", []),
        )


# ---------------------------------------------------------------------------
# Party
# ---------------------------------------------------------------------------
@dataclass
class Party:
    """A wagon party of 1-4 players traveling the trail."""
    party_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    party_name: str = field(default_factory=lambda: __import__('random').choice(__import__('game_data').HISTORICAL_WAGON_NAMES))
    member_ids: List[str] = field(default_factory=list)
    captain_id: str = ""
    inventory: Inventory = field(default_factory=Inventory)
    profession: Profession = Profession.BANKER
    pace: Pace = Pace.STEADY
    rations: Rations = Rations.FILLING
    distance_traveled: int = 0  # miles
    current_landmark_index: int = 0
    miles_to_next: int = 0
    days_at_current_location: int = 0
    travel_days_since_decision: int = 0
    is_resting: bool = False
    rest_days_remaining: int = 0
    global_date: Optional[date] = None
    status: str = "outfitting"  # outfitting, traveling, decision, hunting, river_crossing, resting, finished, dead
    outfitting_complete: bool = False
    decision_pending: Optional[Decision] = None
    neighbor_party_ids: List[str] = field(default_factory=list)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    tombstones: List[Tombstone] = field(default_factory=list)
    score: int = 0
    hunting_region_depletion: float = 0.0  # 0.0 to 1.0

    @property
    def is_alive(self) -> bool:
        """Party is alive if any member is alive."""
        # Note: This requires external lookup of player health.
        # Set externally by engine when computing.
        return True

    def to_dict(self, include_private: bool = True) -> Dict[str, Any]:
        data = {
            "party_id": self.party_id,
            "party_name": self.party_name,
            "member_ids": self.member_ids,
            "captain_id": self.captain_id,
            "pace": self.pace.value,
            "rations": self.rations.value,
            "distance_traveled": self.distance_traveled,
            "current_landmark_index": self.current_landmark_index,
            "miles_to_next": self.miles_to_next,
            "days_at_current_location": self.days_at_current_location,
            "travel_days_since_decision": self.travel_days_since_decision,
            "is_resting": self.is_resting,
            "rest_days_remaining": self.rest_days_remaining,
            "status": self.status,
            "outfitting_complete": self.outfitting_complete,
            "decision_pending": self.decision_pending.to_dict() if self.decision_pending else None,
            "neighbor_party_ids": self.neighbor_party_ids,
            "event_log": self.event_log[-20:] if self.event_log else [],  # Last 20 events
            "tombstones": [t.to_dict() for t in self.tombstones],
            "score": self.score,
        }
        if include_private:
            data["inventory"] = self.inventory.to_dict()
            data["profession"] = self.profession.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Party:
        party = cls(
            party_id=data["party_id"],
            party_name=data["party_name"],
            member_ids=data.get("member_ids", []),
            captain_id=data.get("captain_id", ""),
            pace=Pace(data.get("pace", "Steady")),
            rations=Rations(data.get("rations", "Meager")),
            distance_traveled=data.get("distance_traveled", 0),
            current_landmark_index=data.get("current_landmark_index", 0),
            miles_to_next=data.get("miles_to_next", 0),
            status=data.get("status", "outfitting"),
            outfitting_complete=data.get("outfitting_complete", False),
            travel_days_since_decision=data.get("travel_days_since_decision", 0),
        )
        if "inventory" in data:
            party.inventory = Inventory.from_dict(data["inventory"])
        if "decision_pending" in data and data["decision_pending"]:
            d = data["decision_pending"]
            party.decision_pending = Decision(
                decision_id=d["decision_id"],
                party_id=d["party_id"],
                decision_type=DecisionType(d["decision_type"]),
                prompt=d["prompt"],
                options=d["options"],
                votes=d.get("votes", {}),
                captain_id=d.get("captain_id", ""),
                captain_default=d.get("captain_default", ""),
                timeout_seconds=d.get("timeout_seconds", 10),
                resolved=d.get("resolved", False),
                result=d.get("result"),
            )
        return party


# ---------------------------------------------------------------------------
# Global Session / Game State
# ---------------------------------------------------------------------------
@dataclass
class GameSession:
    """Top-level session containing all parties and global state."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_code: str = field(default_factory=lambda: str(uuid.uuid4())[:4].upper())
    game_status: str = "lobby"  # lobby, outfitting, active, paused, ended
    global_date: Optional[date] = None
    global_weather: Weather = Weather.COOL
    global_season: str = "spring"
    start_date: Optional[date] = None
    parties: Dict[str, Party] = field(default_factory=dict)
    players: Dict[str, Player] = field(default_factory=dict)
    host_player_id: Optional[str] = None
    auto_advance_enabled: bool = False
    auto_advance_interval: int = 15  # seconds
    tick_count: int = 0
    tombstones: List[Tombstone] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self, player_id: Optional[str] = None) -> Dict[str, Any]:
        """Serialize session. If player_id given, includes their party's full state."""
        data = {
            "session_id": self.session_id,
            "session_code": self.session_code,
            "game_status": self.game_status,
            "global_date": self.global_date.isoformat() if self.global_date else None,
            "global_weather": self.global_weather.value,
            "global_season": self.global_season,
            "auto_advance_enabled": self.auto_advance_enabled,
            "auto_advance_interval": self.auto_advance_interval,
            "tick_count": self.tick_count,
            "parties": {},
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "host_player_id": self.host_player_id,
            "tombstones": [t.to_dict() for t in self.tombstones],
        }
        for pid, party in self.parties.items():
            # Include full private state for host or party members
            is_member = player_id in party.member_ids if player_id else False
            is_host = player_id == self.host_player_id if player_id else False
            data["parties"][pid] = party.to_dict(include_private=is_member or is_host)
        return data

    def get_host_dict(self) -> Dict[str, Any]:
        """Full state dump for host dashboard."""
        data = self.to_dict()
        data["parties"] = {pid: p.to_dict(include_private=True) for pid, p in self.parties.items()}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GameSession:
        session = cls(
            session_id=data.get("session_id", str(uuid.uuid4())[:8]),
            session_code=data.get("session_code", str(uuid.uuid4())[:4].upper()),
            game_status=data.get("game_status", "lobby"),
            global_date=date.fromisoformat(data["global_date"]) if data.get("global_date") else None,
            global_weather=Weather(data.get("global_weather", "Cool")),
            global_season=data.get("global_season", "spring"),
            start_date=date.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            host_player_id=data.get("host_player_id"),
            auto_advance_enabled=data.get("auto_advance_enabled", False),
            auto_advance_interval=data.get("auto_advance_interval", 15),
            tick_count=data.get("tick_count", 0),
        )
        if "parties" in data:
            session.parties = {pid: Party.from_dict(p_data) for pid, p_data in data["parties"].items()}
        if "players" in data:
            session.players = {pid: Player.from_dict(p_data) for pid, p_data in data["players"].items()}
        if "tombstones" in data:
            session.tombstones = [Tombstone.from_dict(t) for t in data["tombstones"]]
        if "created_at" in data:
            try:
                session.created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                pass
        return session
