"""Session orchestrator — manages game state, auto-advance, and host commands."""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any

from game_data import (
    MONTHLY_WEATHER_WEIGHTS,
    DEFAULT_AUTO_ADVANCE_INTERVAL,
    DEFAULT_DECISION_TIMEOUT_AUTO,
    DEFAULT_DECISION_TIMEOUT_PAUSED,
    TRAIL_EVENTS,
    STORE_PRICES,
    FORT_PRICE_MULTIPLIERS,
    Weather,
    Terrain,
    Profession,
    Pace,
    Rations,
    Landmark,
    LANDMARKS,
    NPC_MALE_NAMES,
    NPC_FEMALE_NAMES,
)
from models import GameSession, Party, Player, Decision, Inventory, Tombstone, DecisionType
from party_engine import PartyEngine


class SessionManager:
    """Thread-safe manager for a single game session."""

    def __init__(self, host_player_id: str, host_name: str = "Host"):
        self.lock = threading.RLock()
        self.session = GameSession(host_player_id=host_player_id)
        self.engines: Dict[str, PartyEngine] = {}
        self._host_sid: Optional[str] = None

        # Add host as a player
        host = Player(
            player_id=host_player_id,
            name=host_name,
            is_host=True,
        )
        self.session.players[host_player_id] = host

        # Load persistent tombstones
        self._load_persistent_tombstones()

    # ------------------------------------------------------------------
    # Player & Party Management
    # ------------------------------------------------------------------
    def add_player(self, name: str, socket_id: str) -> Player:
        """Add a new non-host player to the lobby."""
        with self.lock:
            player = Player(name=name, socket_id=socket_id)
            self.session.players[player.player_id] = player
            return player

    def remove_player(self, player_id: str):
        """Mark a player as disconnected (keep them for reconnection)."""
        with self.lock:
            if player_id in self.session.players:
                self.session.players[player_id].socket_id = None

    def reconnect_player(self, player_id: str, socket_id: str) -> Optional[Player]:
        """Reconnect a previously connected player."""
        with self.lock:
            if player_id in self.session.players:
                self.session.players[player_id].socket_id = socket_id
                self.session.players[player_id].last_seen = __import__('datetime').datetime.now()
                return self.session.players[player_id]
            return None

    def create_party(self, party_name: str) -> Party:
        """Create a new empty party."""
        with self.lock:
            party = Party(party_name=party_name)
            self.session.parties[party.party_id] = party
            self.engines[party.party_id] = PartyEngine()
            return party

    def assign_player_to_party(self, player_id: str, party_id: str) -> bool:
        """Assign a player to a party. Returns False if party is full."""
        with self.lock:
            if party_id not in self.session.parties:
                return False
            party = self.session.parties[party_id]
            if len(party.member_ids) >= 5:
                return False
            if player_id not in self.session.players:
                return False

            # Remove from old party if any
            old_party_id = self.session.players[player_id].party_id
            if old_party_id and old_party_id in self.session.parties:
                old_party = self.session.parties[old_party_id]
                if player_id in old_party.member_ids:
                    old_party.member_ids.remove(player_id)
                if old_party.captain_id == player_id:
                    old_party.captain_id = old_party.member_ids[0] if old_party.member_ids else ""

            # Add to new party
            party.member_ids.append(player_id)
            self.session.players[player_id].party_id = party_id
            if not party.captain_id:
                party.captain_id = player_id
            return True

    def shuffle_parties(self) -> bool:
        """Randomly assign all unassigned players to parties evenly."""
        with self.lock:
            import random
            unassigned = [
                pid for pid, p in self.session.players.items()
                if not p.is_host and not p.party_id and not p.is_npc
            ]
            if not unassigned:
                return False

            # Create parties if needed (target ~5 per party)
            needed_parties = max(1, (len(unassigned) + 4) // 5)
            while len(self.session.parties) < needed_parties:
                self.create_party(f"Wagon Party {len(self.session.parties) + 1}")

            party_ids = list(self.session.parties.keys())
            random.shuffle(unassigned)
            for i, player_id in enumerate(unassigned):
                self.assign_player_to_party(player_id, party_ids[i % len(party_ids)])
            return True

    def fill_party_with_npcs(self, party_id: str) -> bool:
        """Fill a party up to 5 members with NPCs."""
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return False
            real_members = [pid for pid in party.member_ids if not self.session.players[pid].is_npc]
            npcs_needed = 5 - len(real_members)
            existing_npcs = [pid for pid in party.member_ids if self.session.players[pid].is_npc]
            # Remove excess NPCs
            while len(existing_npcs) > max(0, npcs_needed):
                pid = existing_npcs.pop()
                if pid in party.member_ids:
                    party.member_ids.remove(pid)
                self.session.players.pop(pid, None)
            # Add needed NPCs
            import random
            for i in range(max(0, npcs_needed)):
                name = random.choice(NPC_MALE_NAMES + NPC_FEMALE_NAMES)
                npc = Player(name=name, is_npc=True)
                self.session.players[npc.player_id] = npc
                party.member_ids.append(npc.player_id)
                self.session.players[npc.player_id].party_id = party_id
                if not party.captain_id:
                    party.captain_id = npc.player_id
            return True

    def set_party_name(self, party_id: str, name: str) -> bool:
        with self.lock:
            if party_id in self.session.parties:
                self.session.parties[party_id].party_name = name
                return True
            return False

    # ------------------------------------------------------------------
    # Game Lifecycle
    # ------------------------------------------------------------------
    def start_game(self, start_date: Optional[date] = None) -> bool:
        """Move from lobby to outfitting phase. Parties must outfit before journey begins."""
        with self.lock:
            if self.session.game_status not in ("lobby", "outfitting"):
                return False

            if not self.session.parties:
                return False

            self.session.start_date = start_date or date(1848, 3, 1)
            self.session.global_date = self.session.start_date
            self.session.global_weather = self._compute_weather(self.session.global_date)
            self.session.game_status = "outfitting"

            for party in self.session.parties.values():
                party.status = "outfitting"
                if not party.global_date:
                    party.global_date = self.session.global_date
                # Initialize engines for outfitting
                if party.party_id not in self.engines:
                    self.engines[party.party_id] = PartyEngine()

            return True

    def begin_journey(self) -> bool:
        """Transition from outfitting to active travel. Auto-outfit any non-ready parties."""
        with self.lock:
            if self.session.game_status != "outfitting":
                return False

            self.session.game_status = "active"

            for party in self.session.parties.values():
                # Set starting date based on selected month
                start_month = getattr(party, 'start_month', 3)  # Default to March
                party.global_date = date(1848, start_month, 1)
                
                if party.outfitting_complete:
                    party.status = "traveling"
                    continue

                # Auto-outfit with defaults for parties that didn't manually outfit
                engine = self.engines.get(party.party_id)
                if engine:
                    purchases = {
                        'oxen': 6,
                        'food': 600,
                        'clothing': 8,
                        'bullets': 20,
                        'wagon_wheel': 2,
                        'wagon_axle': 2,
                        'wagon_tongue': 2,
                    }
                    profession = party.profession or Profession.CARPENTER
                    party, _ = engine.outfit_party(party, profession, purchases)
                    self.session.parties[party.party_id] = party

            return True

    def end_game(self) -> bool:
        with self.lock:
            self.session.game_status = "ended"
            self.session.auto_advance_enabled = False
            return True

    # ------------------------------------------------------------------
    # Auto-Advance Controls
    # ------------------------------------------------------------------
    def pause(self) -> bool:
        with self.lock:
            if self.session.game_status == "active":
                self.session.game_status = "paused"
                return True
            return False

    def resume(self) -> bool:
        with self.lock:
            if self.session.game_status == "paused":
                self.session.game_status = "active"
                return True
            return False

    def set_auto_advance(self, enabled: bool, interval_seconds: int = DEFAULT_AUTO_ADVANCE_INTERVAL):
        with self.lock:
            self.session.auto_advance_enabled = enabled
            self.session.auto_advance_interval = max(5, min(60, interval_seconds))

    # ------------------------------------------------------------------
    # Daily Tick
    # ------------------------------------------------------------------
    def tick(self) -> Dict[str, Any]:
        """Advance one global day. Returns snapshot for broadcasting."""
        with self.lock:
            if self.session.game_status not in ("active",):
                return {"session_state": self.get_host_state(), "events": []}

            self.session.tick_count += 1

            # 1. Resolve pending decisions with defaults
            for party in self.session.parties.values():
                if party.decision_pending and not party.decision_pending.resolved:
                    timeout = (
                        DEFAULT_DECISION_TIMEOUT_PAUSED
                        if self.session.game_status == "paused"
                        else party.decision_pending.timeout_seconds
                    )
                    # Check if decision has timed out
                    from datetime import datetime
                    elapsed = (datetime.now() - party.decision_pending.created_at).total_seconds()
                    if elapsed >= timeout:
                        winner = party.decision_pending.get_winner()
                        engine = self.engines.get(party.party_id)
                        if engine:
                            players = self._get_party_players(party)
                            party, players, _ = engine.apply_decision(party, players, winner, river_depth=self._compute_river_depth())
                            self._update_party_and_players(party, players)

            # 2. Tick each active party
            all_events = []
            for party in self.session.parties.values():
                if party.status in ("finished", "dead", "hunting", "outfitting"):
                    continue

                engine = self.engines.get(party.party_id)
                if not engine:
                    continue

                players = self._get_party_players(party)
                # Inject global tombstones for proximity checking
                party._global_tombstones = self.session.tombstones
                party, players, events = engine.tick(
                    party, players, self.session.global_date, self.session.global_weather
                )
                del party._global_tombstones
                self._update_party_and_players(party, players)

                # Auto-vote NPCs on any new decision
                if party.decision_pending and not party.decision_pending.resolved:
                    self._apply_npc_votes(party, party.decision_pending)

                for ev in events:
                    ev["party_id"] = party.party_id
                    ev["party_name"] = party.party_name
                    all_events.append(ev)

                    # Handle tombstones from deaths
                    if ev["type"] == "death":
                        ts_idx = ev.get("tombstone_index", -1)
                        party_ts = party.tombstones[ts_idx] if 0 <= ts_idx < len(party.tombstones) else None
                        tombstone = Tombstone(
                            player_name=ev["player_name"],
                            party_name=party.party_name,
                            mile_marker=party.distance_traveled,
                            cause=ev["cause"],
                            date=self.session.global_date,
                            epitaph=party_ts.epitaph if party_ts else f"Here lies {ev['player_name']}, who died of {ev['cause']}.",
                            written_by_party_id=party.party_id,
                        )
                        self.session.tombstones.append(tombstone)
                        self._save_persistent_tombstones()

            # 3. Compute proximity
            self._update_proximity()

            # 4. Advance global date & weather
            self.session.global_date += timedelta(days=1)
            self.session.global_weather = self._compute_weather(self.session.global_date)

            # 5. Check game end
            active_parties = [
                p for p in self.session.parties.values()
                if p.status not in ("finished", "dead")
            ]
            if not active_parties:
                self.session.game_status = "ended"
                self.session.auto_advance_enabled = False

            return {
                "session_state": self.get_host_state(),
                "events": all_events,
            }

    def advance_days(self, count: int) -> Dict[str, Any]:
        """Manually advance multiple days. Returns final snapshot."""
        with self.lock:
            result = {}
            for _ in range(count):
                if self.session.game_status not in ("active",):
                    break
                result = self.tick()
            return result

    # ------------------------------------------------------------------
    # Player Actions
    # ------------------------------------------------------------------
    def submit_vote(self, player_id: str, decision_id: str, choice: str) -> Optional[Tuple[str, Decision]]:
        with self.lock:
            player = self.session.players.get(player_id)
            if not player or not player.party_id:
                return None

            party = self.session.parties.get(player.party_id)
            if not party or not party.decision_pending:
                return None

            dec = party.decision_pending
            if dec.decision_id != decision_id:
                return None
            if not player.is_alive:
                return None
            if choice not in dec.options:
                return None

            dec.votes[player_id] = choice

            # Auto-vote for NPCs in this party
            self._apply_npc_votes(party, dec)
            return (player.party_id, dec)

    def _apply_npc_votes(self, party: Party, dec: Decision):
        """Have all NPCs in the party vote with the majority or captain default."""
        npc_ids = [pid for pid in party.member_ids if self.session.players[pid].is_npc]
        for npc_id in npc_ids:
            if npc_id in dec.votes:
                continue
            npc = self.session.players[npc_id]
            if not npc.is_alive:
                continue
            # Count current votes
            counts = {}
            for v in dec.votes.values():
                counts[v] = counts.get(v, 0) + 1
            if counts:
                max_count = max(counts.values())
                winners = [opt for opt, cnt in counts.items() if cnt == max_count]
                if len(winners) == 1:
                    dec.votes[npc_id] = winners[0]
                else:
                    dec.votes[npc_id] = dec.captain_default if dec.captain_default in dec.options else dec.options[0]
            else:
                dec.votes[npc_id] = dec.captain_default if dec.captain_default in dec.options else dec.options[0]

    def captain_override(self, player_id: str, decision_id: str, choice: str) -> bool:
        with self.lock:
            player = self.session.players.get(player_id)
            if not player or not player.party_id:
                return False

            party = self.session.parties.get(player.party_id)
            if not party or not party.decision_pending:
                return False

            if party.captain_id != player_id:
                return False

            dec = party.decision_pending
            if dec.decision_id != decision_id:
                return False
            if choice not in dec.options:
                return False

            dec.captain_default = choice
            return True

    def resolve_hunt(self, party_id: str, shots_hit: int) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}

            engine = self.engines.get(party_id)
            if not engine:
                return {"success": False, "message": "No engine"}

            party, result = engine.resolve_hunt(party, shots_hit)
            self.session.parties[party_id] = party
            return result

    def buy_item(self, party_id: str, item: str, quantity: int) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}

            # Determine price multiplier based on nearest fort
            multiplier = 1.0
            for fort_name, mult in sorted(FORT_PRICE_MULTIPLIERS.items(), key=lambda x: x[1]):
                fort_lm = next((lm for lm in LANDMARKS if lm.name == fort_name), None)
                if fort_lm and abs(party.distance_traveled - fort_lm.miles_from_start) < 50:
                    multiplier = mult
                    break

            engine = self.engines.get(party_id)
            if not engine:
                return {"success": False, "message": "No engine"}

            party, result = engine.buy_item(party, item, quantity, price_multiplier=multiplier)
            self.session.parties[party_id] = party
            return result

    def cross_river(self, party_id: str, method: str) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}

            engine = self.engines.get(party_id)
            if not engine:
                return {"success": False, "message": "No engine"}

            # Compute river depth based on weather
            river_depth = self._compute_river_depth()
            players = self._get_party_players(party)
            party, players, result = engine.resolve_river_crossing(party, players, method, river_depth)
            self._update_party_and_players(party, players)
            return result

    # ------------------------------------------------------------------
    # Host Overrides
    # ------------------------------------------------------------------
    def host_override_decision(self, party_id: str, choice: str) -> bool:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party or not party.decision_pending:
                return False

            engine = self.engines.get(party_id)
            if not engine:
                return False

            players = self._get_party_players(party)
            party, players, _ = engine.apply_decision(party, players, choice, river_depth=self._compute_river_depth())
            self._update_party_and_players(party, players)
            return True

    def host_edit_party(self, party_id: str, field: str, value: Any) -> bool:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return False

            # Allow editing common fields
            if field == "party_name":
                party.party_name = str(value)
            elif field == "distance_traveled":
                party.distance_traveled = max(0, int(value))
            elif field == "money":
                party.inventory.money = float(value)
            elif field == "food":
                party.inventory.food = max(0, int(value))
            elif field == "oxen":
                party.inventory.oxen = max(0, int(value))
            elif field == "clothing":
                party.inventory.clothing = max(0, int(value))
            elif field == "bullets":
                party.inventory.bullets = max(0, int(value))
            elif field == "wagon_wheels":
                party.inventory.wagon_wheels = max(0, int(value))
            elif field == "wagon_axles":
                party.inventory.wagon_axles = max(0, int(value))
            elif field == "wagon_tongues":
                party.inventory.wagon_tongues = max(0, int(value))
            elif field == "pace":
                party.pace = Pace(value) if value in [p.value for p in Pace] else party.pace
            elif field == "rations":
                party.rations = Rations(value) if value in [r.value for r in Rations] else party.rations
            elif field == "status":
                party.status = str(value)
            else:
                return False
            return True

    def host_inject_event(self, party_id: str, event_id: str) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}

            event_def = next((e for e in TRAIL_EVENTS if e.id == event_id), None)
            if not event_def:
                return {"success": False, "message": "Unknown event"}

            engine = self.engines.get(party_id)
            if not engine:
                return {"success": False, "message": "No engine"}

            players = self._get_party_players(party)
            party, players, msg = engine._apply_trail_event(
                party, players, {"id": event_id, "description": event_def.description, "requires_supplies": event_def.requires_supplies}
            )
            self._update_party_and_players(party, players)

            return {"success": True, "message": msg}

    def call_vote(self, party_id: str, vote_type: str) -> bool:
        """Captain-initiated vote for pace, rations, or hunt."""
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return False
            if party.decision_pending and not party.decision_pending.resolved:
                return False  # Already have a pending decision
            if party.status in ("finished", "dead", "outfitting"):
                return False

            engine = self.engines.get(party_id)
            if not engine:
                return False

            import time
            current_time = time.time()
            if current_time - getattr(party, 'last_vote_called_at', 0.0) < 120:
                return False
            party.last_vote_called_at = current_time

            if vote_type == "pace":
                party.status = "decision"
                party.decision_pending = Decision(
                    party_id=party_id,
                    decision_type=DecisionType.PACE,
                    prompt=f"Current pace: {party.pace.value}. Current rations: {party.rations.value}. What would you like to change?",
                    options=[
                        "Keep pace and rations",
                        "Speed up (increase pace)",
                        "Slow down (decrease pace)",
                        "Increase rations",
                        "Decrease rations",
                    ],
                    captain_id=party.captain_id,
                    captain_default="Keep pace and rations",
                    timeout_seconds=5,
                )
            elif vote_type == "hunt":
                party.status = "decision"
                party.decision_pending = Decision(
                    party_id=party_id,
                    decision_type=DecisionType.HUNT,
                    prompt="The captain has called for a hunt. Does the party agree?",
                    options=["Hunt", "Continue on"],
                    captain_id=party.captain_id,
                    captain_default="Continue on",
                    timeout_seconds=5,
                )
            elif vote_type == "rest":
                party.status = "decision"
                party.decision_pending = Decision(
                    party_id=party_id,
                    decision_type=DecisionType.REST,
                    prompt="The captain has called for a rest day. Does the party agree?",
                    options=["Rest here", "Continue on"],
                    captain_id=party.captain_id,
                    captain_default="Continue on",
                    timeout_seconds=5,
                )
            else:
                return False

            self._apply_npc_votes(party, party.decision_pending)
            return True

    def new_session(self) -> bool:
        """Reset the session to a fresh lobby state, keeping the host."""
        with self.lock:
            host_id = self.session.host_player_id
            host_name = self.session.players.get(host_id, Player()).name
            self.session = GameSession(host_player_id=host_id)
            self.engines.clear()
            # Re-add host
            host = Player(
                player_id=host_id,
                name=host_name,
                is_host=True,
            )
            self.session.players[host_id] = host
            return True

    def host_set_player_health(self, player_id: str, health_status: str) -> bool:
        with self.lock:
            from game_data import HealthStatus
            player = self.session.players.get(player_id)
            if not player:
                return False
            try:
                player.health_status = HealthStatus(health_status)
                if health_status == "Dead":
                    player.is_alive = False
                else:
                    player.is_alive = True
                return True
            except ValueError:
                return False

    # ------------------------------------------------------------------
    # Outfitting Phase
    # ------------------------------------------------------------------
    def choose_profession(self, party_id: str, profession_value: str) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}
            if self.session.game_status != "outfitting":
                return {"success": False, "message": "Not in outfitting phase"}

            try:
                profession = Profession(profession_value)
            except ValueError:
                return {"success": False, "message": "Invalid profession"}

            engine = self.engines.get(party_id)
            if not engine:
                return {"success": False, "message": "No engine"}

            party = engine.choose_profession(party, profession)
            self.session.parties[party_id] = party
            return {"success": True, "message": f"Profession set to {profession.value}.", "money": party.inventory.money}

    def choose_month(self, party_id: str, start_month: int) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}
            if self.session.game_status != "outfitting":
                return {"success": False, "message": "Not in outfitting phase"}
            
            if start_month < 1 or start_month > 12:
                return {"success": False, "message": "Invalid month"}
                
            party.start_month = start_month
            self.session.parties[party_id] = party
            return {"success": True, "message": f"Departure month set to {start_month}."}

    def buy_starting_supplies(self, party_id: str, item: str, quantity: int) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}
            
            # Allow buying if in initial outfitting phase OR if party is currently at a fort store
            if self.session.game_status != "outfitting" and party.status != "outfitting":
                return {"success": False, "message": "Not in outfitting phase"}

            engine = self.engines.get(party_id)
            if not engine:
                return {"success": False, "message": "No engine"}

            # Calculate price multiplier based on distance if in active game (forts are more expensive)
            price_multiplier = 1.0
            if self.session.game_status == "active":
                from game_data import FORT_PRICE_MULTIPLIERS, LANDMARKS
                # Find current landmark by name if possible, or index
                current_lm_name = LANDMARKS[party.current_landmark_index].name
                price_multiplier = FORT_PRICE_MULTIPLIERS.get(current_lm_name, 1.0)

            party, result = engine.buy_item(party, item, quantity, price_multiplier)
            self.session.parties[party_id] = party
            result["inventory"] = party.inventory.to_dict()
            return result

    def party_outfit_complete(self, party_id: str) -> Dict[str, Any]:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return {"success": False, "message": "Party not found"}
            
            # If at a fort during active game, return to traveling
            if self.session.game_status == "active":
                party.status = "traveling"
                return {"success": True, "message": "You leave the store and return to the trail."}

            if self.session.game_status != "outfitting":
                return {"success": False, "message": "Not in outfitting phase"}

            # Validate minimum supplies for initial departure
            if party.inventory.oxen < 1:
                return {"success": False, "message": "You need at least 1 yoke of oxen."}
            if party.inventory.food < 1:
                return {"success": False, "message": "You need at least some food."}

            party.outfitting_complete = True
            party.status = "ready"
            return {"success": True, "message": "Party is ready to depart!"}

    # ------------------------------------------------------------------
    # Tombstones
    # ------------------------------------------------------------------
    def submit_epitaph(self, party_id: str, tombstone_index: int, epitaph: str) -> bool:
        with self.lock:
            party = self.session.parties.get(party_id)
            if not party:
                return False
            if tombstone_index < 0 or tombstone_index >= len(party.tombstones):
                return False
            party.tombstones[tombstone_index].epitaph = epitaph[:200]  # limit length
            # Also update the matching global tombstone
            for ts in self.session.tombstones:
                if ts.player_name == party.tombstones[tombstone_index].player_name and ts.written_by_party_id == party_id:
                    ts.epitaph = epitaph[:200]
                    break
            self._save_persistent_tombstones()
            return True

    def host_edit_tombstone(self, tombstone_index: int, epitaph: str) -> bool:
        with self.lock:
            if tombstone_index < 0 or tombstone_index >= len(self.session.tombstones):
                return False
            self.session.tombstones[tombstone_index].epitaph = epitaph[:200]
            self._save_persistent_tombstones()
            return True

    def _load_persistent_tombstones(self):
        """Load tombstones from disk into this session."""
        try:
            if os.path.exists("tombstones.json"):
                with open("tombstones.json", "r") as f:
                    data = json.load(f)
                self.session.tombstones = [Tombstone.from_dict(ts) for ts in data]
        except Exception as e:
            print(f"[Tombstones] Failed to load: {e}")
            self.session.tombstones = []

    def _save_persistent_tombstones(self):
        """Save all tombstones to disk."""
        try:
            with open("tombstones.json", "w") as f:
                json.dump([ts.to_dict() for ts in self.session.tombstones], f, indent=2)
        except Exception as e:
            print(f"[Tombstones] Failed to save: {e}")

    # ------------------------------------------------------------------
    # State Access
    # ------------------------------------------------------------------
    def get_player_state(self, player_id: str) -> Dict[str, Any]:
        """Get trimmed state for a specific player."""
        with self.lock:
            return self.session.to_dict(player_id=player_id)

    def get_host_state(self) -> Dict[str, Any]:
        """Get full state for host dashboard."""
        with self.lock:
            return self.session.get_host_dict()

    def get_party_state(self, party_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            party = self.session.parties.get(party_id)
            return party.to_dict(include_private=True) if party else None

    def load_from_dict(self, data: Dict[str, Any]) -> bool:
        """Replace the current session state from a dictionary."""
        with self.lock:
            try:
                from models import GameSession
                self.session = GameSession.from_dict(data)
                # Re-initialize engines for all restored parties
                self.engines.clear()
                for party_id in self.session.parties:
                    self.engines[party_id] = PartyEngine()
                return True
            except Exception as e:
                print(f"Error loading session: {e}")
                return False

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    def _get_party_players(self, party: Party) -> Dict[str, Player]:
        """Get a dict of player objects for a party's members."""
        return {
            pid: self.session.players[pid]
            for pid in party.member_ids
            if pid in self.session.players
        }

    def _update_party_and_players(self, party: Party, players: Dict[str, Player]):
        """Update session state with modified party and player objects."""
        self.session.parties[party.party_id] = party
        for pid, player in players.items():
            if pid in self.session.players:
                self.session.players[pid] = player

    def _compute_weather(self, dt: date) -> Weather:
        """Compute weather for a given date based on month."""
        weights = MONTHLY_WEATHER_WEIGHTS.get(dt.month, [(Weather.COOL, 1)])
        return self._weighted_choice(weights)

    def _compute_river_depth(self) -> int:
        """Compute river depth in feet based on current weather."""
        import random
        base = 2
        if self.session.global_weather == Weather.RAIN:
            base += random.randint(2, 6)
        elif self.session.global_weather == Weather.SNOW:
            base += random.randint(1, 3)
        elif self.session.global_weather in (Weather.VERY_HOT, Weather.HOT):
            base = max(1, base - 1)
        return base + random.randint(0, 3)

    def _weighted_choice(self, choices):
        total = sum(w for _, w in choices)
        r = __import__('random').randint(1, total)
        for item, weight in choices:
            r -= weight
            if r <= 0:
                return item
        return choices[-1][0]

    def _update_proximity(self):
        """Compute neighbor relationships between all parties."""
        party_list = list(self.session.parties.values())
        for party in party_list:
            party.neighbor_party_ids = []

        for i, p1 in enumerate(party_list):
            for p2 in party_list[i + 1:]:
                distance = abs(p1.distance_traveled - p2.distance_traveled)
                if distance <= 5:
                    p1.neighbor_party_ids.append(p2.party_id)
                    p2.neighbor_party_ids.append(p1.party_id)
