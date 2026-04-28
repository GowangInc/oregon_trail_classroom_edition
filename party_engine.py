"""Oregon Trail party engine — pure game logic, no Flask."""

from __future__ import annotations

import random
from copy import deepcopy
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any

from game_data import (
    HealthStatus,
    ILLNESS_BASE_PROBABILITY,
    ILLNESS_HEALTH_MULTIPLIERS,
    ILLNESS_TYPES,
    ILLNESS_WEATHER_MULTIPLIERS,
    LANDMARKS,
    PACE_HEALTH_IMPACT,
    PACE_MILES_PER_DAY,
    PACE_OXEN_WEAR,
    RATIONS_FOOD_PER_PERSON_PER_DAY,
    RATIONS_HEALTH_IMPACT,
    RIVER_MISHAP_CHANCES,
    TERRAIN_SEGMENTS,
    TOTAL_DISTANCE,
    TRAIL_EVENTS,
    WEATHER_HEALTH_IMPACT,
    WEATHER_SPEED_MODIFIER,
    FERRY_COST_PER_PERSON,
    FERRY_COST_PER_OXEN,
    SCORE_SURVIVOR,
    SCORE_OXEN,
    SCORE_SPARE_PART,
    SCORE_PER_5_DOLLARS,
    SCORE_PER_50_FOOD,
    SCORE_PER_CLOTHING,
    SCORE_PER_BULLET,
    HUNTING_MAX_FOOD_PER_HUNT,
    HUNTING_BULLETS_PER_SHOT,
    Weather,
    Terrain,
    Pace,
    Rations,
    Profession,
    Landmark,
)
from models import DecisionType
from models import Party, Player, Decision, Inventory, Tombstone


class PartyEngine:
    """Handles all game logic for a single wagon party."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_terrain_at(mile: int) -> Terrain:
        for start, end, terrain in TERRAIN_SEGMENTS:
            if start <= mile < end:
                return terrain
        return Terrain.MOUNTAINS

    @staticmethod
    def _get_current_landmark(mile: int) -> Tuple[int, Landmark]:
        """Return (index, landmark) for the landmark just passed or at."""
        for i, lm in enumerate(LANDMARKS):
            if mile < lm.miles_from_start:
                return i - 1, LANDMARKS[i - 1] if i > 0 else LANDMARKS[0]
        return len(LANDMARKS) - 1, LANDMARKS[-1]

    @staticmethod
    def _get_next_landmark(mile: int) -> Tuple[int, Landmark]:
        """Return (index, landmark) for the next landmark ahead."""
        for i, lm in enumerate(LANDMARKS):
            if mile < lm.miles_from_start:
                return i, lm
        return len(LANDMARKS) - 1, LANDMARKS[-1]

    def _roll_probability(self, probability: float) -> bool:
        return self.rng.random() < probability

    def _weighted_choice(self, choices: List[Tuple[Any, int]]) -> Any:
        """Choose from a list of (item, weight) tuples."""
        total = sum(w for _, w in choices)
        r = self.rng.randint(1, total)
        for item, weight in choices:
            r -= weight
            if r <= 0:
                return item
        return choices[-1][0]

    # ------------------------------------------------------------------
    # Public: daily tick
    # ------------------------------------------------------------------
    def tick(
        self,
        party: Party,
        players: Dict[str, Player],
        global_date: date,
        global_weather: Weather,
    ) -> Tuple[Party, Dict[str, Player], List[Dict[str, Any]]]:
        """Advance one day for this party. Returns (party, players, events)."""
        events: List[Dict[str, Any]] = []
        party = deepcopy(party)
        players = {pid: deepcopy(p) for pid, p in players.items()}
        party.global_date = global_date

        # If party is finished or dead, nothing happens
        if party.status in ("finished", "dead"):
            return party, players, events

        # If resting, consume rest day and skip travel
        if party.is_resting and party.rest_days_remaining > 0:
            party.rest_days_remaining -= 1
            if party.rest_days_remaining <= 0:
                party.is_resting = False
                party.status = "traveling"
            # Health recovery during rest
            self._apply_rest_recovery(party, players)
            events.append({
                "type": "rest",
                "message": f"{party.party_name} is resting. {party.rest_days_remaining} days remaining."
            })
            return party, players, events

        # If a decision is still pending, resolve it with default and stop
        if party.decision_pending and not party.decision_pending.resolved:
            winner = party.decision_pending.get_winner()
            party, players, ev = self.apply_decision(party, players, winner)
            events.extend(ev)
            # If the decision was about resting, don't travel today
            if party.is_resting:
                return party, players, events

        # Clear any stale decision
        party.decision_pending = None

        # 1. Travel
        terrain = self._get_terrain_at(party.distance_traveled)
        miles_today = self._calculate_travel(party, global_weather, terrain)
        if miles_today > 0:
            party.distance_traveled = min(party.distance_traveled + miles_today, TOTAL_DISTANCE)
            party.days_at_current_location = 0
        else:
            party.days_at_current_location += 1

        # 2. Consume food
        alive_members = [pid for pid in party.member_ids if players[pid].is_alive]
        food_consumed = self._consume_food(party, len(alive_members))

        # 3. Random trail events
        event_results = self._roll_trail_events(party, global_weather, terrain)
        for ev in event_results:
            party, players, msg = self._apply_trail_event(party, players, ev)
            if msg:
                events.append({"type": "trail_event", "event_id": ev["id"], "message": msg})

        # 4. Health & illness
        party, players, health_events = self._update_health(party, players, global_weather)
        events.extend(health_events)

        # 5. Check for deaths
        death_events = self._check_deaths(party, players, global_date)
        events.extend(death_events)

        # 6. Check for nearby tombstones from other parties
        tombstone_events = self._check_tombstone_proximity(party)
        events.extend(tombstone_events)

        # 7. Periodic travel decisions (every 5 days of travel)
        if miles_today > 0 and not party.decision_pending:
            party.travel_days_since_decision += 1
            if party.travel_days_since_decision >= 5:
                party.travel_days_since_decision = 0
                party.status = "decision"

                # Alternate between travel actions and pace/rations review
                decision_cycle = getattr(party, '_decision_cycle', 0)
                party._decision_cycle = (decision_cycle + 1) % 3

                if party._decision_cycle == 0:
                    # Pace/rations review every 3rd decision (~10-15 days)
                    party.decision_pending = Decision(
                        party_id=party.party_id,
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
                else:
                    # Regular travel decision: hunt, rest, or continue
                    party.decision_pending = Decision(
                        party_id=party.party_id,
                        decision_type=DecisionType.REST,
                        prompt="The trail stretches ahead. What would the party like to do?",
                        options=["Continue on", "Hunt for food", "Rest for a day"],
                        captain_id=party.captain_id,
                        captain_default="Continue on",
                        timeout_seconds=5,
                    )

        # 9. Check landmark arrival
        next_idx, next_lm = self._get_next_landmark(party.distance_traveled)
        party.miles_to_next = next_lm.miles_from_start - party.distance_traveled
        party.current_landmark_index = next_idx - 1 if next_idx > 0 else 0

        if party.miles_to_next <= 0:
            # Reached a landmark
            party.days_at_current_location = 0
            events.append({
                "type": "landmark",
                "message": f"{party.party_name} has reached {next_lm.name}!",
                "landmark": next_lm.name,
                "is_fort": next_lm.is_fort,
                "is_river": next_lm.is_river,
            })
            if next_lm.name == "Willamette Valley, Oregon":
                party.status = "finished"
                events.append({
                    "type": "finished",
                    "message": f"{party.party_name} has reached Oregon!",
                })
            elif next_lm.is_river:
                party.status = "river_crossing"
                party.travel_days_since_decision = 0
                party.decision_pending = Decision(
                    party_id=party.party_id,
                    decision_type=DecisionType.RIVER_METHOD,
                    prompt=f"You must cross the {next_lm.name}. How will you proceed?",
                    options=["Ford the river", "Caulk the wagon", "Take a ferry", "Wait for better conditions"],
                    captain_id=party.captain_id,
                    captain_default="Ford the river",
                    timeout_seconds=5,
                )
            elif next_lm.is_fort:
                party.status = "decision"
                party.travel_days_since_decision = 0
                party.decision_pending = Decision(
                    party_id=party.party_id,
                    decision_type=DecisionType.BUY_SUPPLIES,
                    prompt=f"You have reached {next_lm.name}. Would you like to buy supplies?",
                    options=["Buy supplies", "Continue on"],
                    captain_id=party.captain_id,
                    captain_default="Continue on",
                    timeout_seconds=5,
                )
            else:
                party.status = "decision"
                party.travel_days_since_decision = 0
                party.decision_pending = Decision(
                    party_id=party.party_id,
                    decision_type=DecisionType.REST,
                    prompt=f"You have reached {next_lm.name}. What would you like to do?",
                    options=["Rest here", "Hunt for food", "Continue on"],
                    captain_id=party.captain_id,
                    captain_default="Continue on",
                    timeout_seconds=5,
                )

        # Check if all dead
        alive_members = [pid for pid in party.member_ids if players[pid].is_alive]
        if not alive_members and party.status != "finished":
            party.status = "dead"
            events.append({
                "type": "dead",
                "message": f"{party.party_name} has perished on the trail.",
            })

        # Calculate score if finished
        if party.status == "finished":
            party.score = self._calculate_score(party, players)

        return party, players, events

    def _check_tombstone_proximity(self, party: Party) -> List[Dict[str, Any]]:
        """Check if party is near tombstones from other parties. Returns visit events."""
        events = []
        # This is populated by session_manager before calling tick
        global_tombstones = getattr(party, '_global_tombstones', [])
        for ts in global_tombstones:
            if ts.written_by_party_id == party.party_id:
                continue
            if party.party_id in ts.visited_by_party_ids:
                continue
            distance = abs(party.distance_traveled - ts.mile_marker)
            if distance <= 5:
                ts.visited_by_party_ids.append(party.party_id)
                events.append({
                    "type": "tombstone",
                    "message": f"You pass a tombstone for {ts.player_name} of {ts.party_name}: \"{ts.epitaph}\" — died of {ts.cause} at mile {ts.mile_marker}.",
                    "player_name": ts.player_name,
                    "party_name": ts.party_name,
                    "epitaph": ts.epitaph,
                })
        return events

    # ------------------------------------------------------------------
    # Travel
    # ------------------------------------------------------------------
    def _calculate_travel(self, party: Party, weather: Weather, terrain: Terrain) -> int:
        """Calculate miles traveled today."""
        if party.inventory.oxen <= 0:
            return 0

        base_miles = PACE_MILES_PER_DAY[party.pace]
        weather_mod = WEATHER_SPEED_MODIFIER[weather]
        terrain_mod = 1.0
        if terrain == Terrain.MOUNTAINS:
            terrain_mod = 0.7
        elif terrain == Terrain.DESERT:
            terrain_mod = 0.9
        elif terrain == Terrain.FOREST:
            terrain_mod = 0.85

        # Oxen health factor
        oxen_factor = min(1.0, party.inventory.oxen / 4)

        miles = int(base_miles * weather_mod * terrain_mod * oxen_factor)
        return max(0, miles)

    # ------------------------------------------------------------------
    # Food
    # ------------------------------------------------------------------
    def _consume_food(self, party: Party, alive_count: int) -> int:
        """Consume daily food. Returns amount consumed."""
        if alive_count <= 0:
            return 0
        needed = RATIONS_FOOD_PER_PERSON_PER_DAY[party.rations] * alive_count
        consumed = min(needed, party.inventory.food)
        party.inventory.food -= consumed
        return consumed

    # ------------------------------------------------------------------
    # Trail Events
    # ------------------------------------------------------------------
    def _roll_trail_events(self, party: Party, weather: Weather, terrain: Terrain) -> List[Dict[str, Any]]:
        """Roll for random trail events today."""
        results = []
        for event in TRAIL_EVENTS:
            prob = event.base_probability
            prob *= event.terrain_multipliers.get(terrain, 1.0)
            prob *= event.weather_multipliers.get(weather, 1.0)
            if self._roll_probability(prob):
                results.append({"id": event.id, "description": event.description, "requires_supplies": event.requires_supplies})
        return results

    def _apply_trail_event(
        self, party: Party, players: Dict[str, Player], event: Dict[str, Any]
    ) -> Tuple[Party, Dict[str, Player], str]:
        """Apply the effects of a trail event. Returns (party, players, message)."""
        event_id = event["id"]
        msg = event["description"]

        if event_id == "broken_wheel":
            if party.inventory.wagon_wheels > 0:
                party.inventory.wagon_wheels -= 1
                msg += " You used a spare wheel."
            else:
                party.status = "decision"
                party.decision_pending = Decision(
                    party_id=party.party_id,
                    decision_type=DecisionType.REST,
                    prompt="Your wagon wheel is broken and you have no spare!",
                    options=["Wait for help", "Try to repair"],
                    captain_id=party.captain_id,
                    captain_default="Wait for help",
                )
                msg += " You have no spare wheel! The wagon is stopped."

        elif event_id == "broken_axle":
            if party.inventory.wagon_axles > 0:
                party.inventory.wagon_axles -= 1
                msg += " You used a spare axle."
            else:
                party.status = "decision"
                party.decision_pending = Decision(
                    party_id=party.party_id,
                    decision_type=DecisionType.REST,
                    prompt="Your wagon axle is broken and you have no spare!",
                    options=["Wait for help", "Try to repair"],
                    captain_id=party.captain_id,
                    captain_default="Wait for help",
                )
                msg += " You have no spare axle! The wagon is stopped."

        elif event_id == "broken_tongue":
            if party.inventory.wagon_tongues > 0:
                party.inventory.wagon_tongues -= 1
                msg += " You used a spare tongue."
            else:
                party.status = "decision"
                party.decision_pending = Decision(
                    party_id=party.party_id,
                    decision_type=DecisionType.REST,
                    prompt="Your wagon tongue is broken and you have no spare!",
                    options=["Wait for help", "Try to repair"],
                    captain_id=party.captain_id,
                    captain_default="Wait for help",
                )
                msg += " You have no spare tongue! The wagon is stopped."

        elif event_id == "oxen_injured":
            # Reduce oxen effectiveness (represented by losing 0.5 oxen, rounded)
            if party.inventory.oxen > 0:
                party.inventory.oxen = max(0, party.inventory.oxen - 1)
                msg += " Travel speed reduced."

        elif event_id == "oxen_died":
            if party.inventory.oxen > 0:
                party.inventory.oxen = max(0, party.inventory.oxen - 1)
                msg += " You may need to buy more oxen."

        elif event_id == "thief":
            stolen_items = []
            if party.inventory.food > 20:
                stolen = min(party.inventory.food // 4, 50)
                party.inventory.food -= stolen
                stolen_items.append(f"{stolen} lbs of food")
            if party.inventory.oxen > 0 and self._roll_probability(0.3):
                party.inventory.oxen -= 1
                stolen_items.append("1 ox")
            if party.inventory.money > 10:
                stolen = min(party.inventory.money * 0.1, 50)
                party.inventory.money -= stolen
                stolen_items.append(f"${stolen:.0f}")
            if stolen_items:
                msg += " Stolen: " + ", ".join(stolen_items) + "."
            else:
                msg += " Luckily, there was nothing to steal."

        elif event_id == "bad_water":
            # 50% chance per member to lose health
            for pid in party.member_ids:
                if players[pid].is_alive and self._roll_probability(0.5):
                    self._worsen_health(players[pid])
            msg += " Some of the party feels sick."

        elif event_id == "lost_trail":
            # No travel today - handled by returning 0 miles, but we already traveled.
            # So instead, we consume extra food and take health penalty.
            party.inventory.food = max(0, party.inventory.food - 10)
            # One random member takes a health hit from the stress
            alive_pids = [pid for pid in party.member_ids if players[pid].is_alive]
            if alive_pids:
                victim = self.rng.choice(alive_pids)
                self._worsen_health(players[victim])
            msg += " You wasted a day searching."

        elif event_id == "find_wild_fruit":
            found = self.rng.randint(10, 30)
            party.inventory.food += found
            msg += f" You gathered {found} lbs of food."

        elif event_id == "wrong_path":
            party.distance_traveled = max(0, party.distance_traveled - self.rng.randint(5, 15))
            party.inventory.food = max(0, party.inventory.food - 10)
            msg += " You lost time and supplies backtracking."

        elif event_id == "grave_site":
            # No mechanical effect, just flavor
            pass

        elif event_id == "rough_trail":
            party.inventory.food = max(0, party.inventory.food - 5)
            # 50% chance per member to be affected
            for pid in party.member_ids:
                if players[pid].is_alive and self._roll_probability(0.5):
                    self._worsen_health(players[pid])
            msg += " The rough going has exhausted the party."

        return party, players, msg

    # ------------------------------------------------------------------
    # Health & Illness
    # ------------------------------------------------------------------
    def _update_health(
        self, party: Party, players: Dict[str, Player], weather: Weather
    ) -> Tuple[Party, Dict[str, Player], List[Dict[str, Any]]]:
        """Update health for all party members."""
        events = []
        alive_members = [pid for pid in party.member_ids if players[pid].is_alive]
        if not alive_members:
            return party, players, events

        # Base health modifiers from pace, rations, weather
        pace_impact = PACE_HEALTH_IMPACT[party.pace]
        rations_impact = RATIONS_HEALTH_IMPACT[party.rations]
        weather_impact = WEATHER_HEALTH_IMPACT[weather]

        # Food shortage penalty
        food_penalty = 0
        if party.inventory.food <= 0:
            food_penalty = -2

        for pid in alive_members:
            player = players[pid]
            # Apply daily health drift
            total_impact = pace_impact + rations_impact + weather_impact + food_penalty

            # Random variance
            total_impact += self.rng.randint(-1, 1)

            if total_impact < 0:
                steps = min(abs(total_impact), 1)  # Cap daily health loss to max 1 step per day
                for _ in range(steps):
                    self._worsen_health(player)
            elif total_impact > 0:
                self._improve_health(player)

            # Passive recovery: if conditions are decent, small chance to improve
            if total_impact == 0 and player.health_status != HealthStatus.HEALTHY:
                if self._roll_probability(0.3):
                    self._improve_health(player)

            # Illness check
            if self._roll_illness(player, weather):
                illness = self.rng.choice(ILLNESS_TYPES)
                # Illness worsens health by 2 steps instead of instantly dropping to VERY_POOR
                self._worsen_health(player)
                self._worsen_health(player)
                events.append({
                    "type": "illness",
                    "player_id": pid,
                    "player_name": player.name,
                    "message": f"{player.name} has fallen ill with {illness}.",
                    "illness": illness,
                })

        return party, players, events

    def _roll_illness(self, player: Player, weather: Weather) -> bool:
        """Roll to see if a player gets ill today."""
        prob = ILLNESS_BASE_PROBABILITY
        prob *= ILLNESS_HEALTH_MULTIPLIERS.get(player.health_status, 1.0)
        prob *= ILLNESS_WEATHER_MULTIPLIERS.get(weather, 1.0)
        return self._roll_probability(prob)

    def _worsen_health(self, player: Player):
        """Move health status one step worse."""
        order = [
            HealthStatus.HEALTHY,
            HealthStatus.FAIR,
            HealthStatus.POOR,
            HealthStatus.VERY_POOR,
            HealthStatus.DEAD,
        ]
        idx = order.index(player.health_status)
        if idx < len(order) - 1:
            player.health_status = order[idx + 1]

    def _improve_health(self, player: Player):
        """Move health status one step better."""
        order = [
            HealthStatus.HEALTHY,
            HealthStatus.FAIR,
            HealthStatus.POOR,
            HealthStatus.VERY_POOR,
            HealthStatus.DEAD,
        ]
        idx = order.index(player.health_status)
        if idx > 0 and player.health_status != HealthStatus.DEAD:
            player.health_status = order[idx - 1]

    def _apply_rest_recovery(self, party: Party, players: Dict[str, Player]):
        """Improve health during rest days."""
        for pid in party.member_ids:
            if players[pid].is_alive:
                self._improve_health(players[pid])
                # Second improvement if very poor
                if players[pid].health_status == HealthStatus.VERY_POOR and self._roll_probability(0.5):
                    self._improve_health(players[pid])

    def _check_deaths(
        self, party: Party, players: Dict[str, Player], current_date: date
    ) -> List[Dict[str, Any]]:
        """Check if any players have died today."""
        events = []
        for pid in party.member_ids:
            player = players[pid]
            if player.is_alive and player.health_status == HealthStatus.DEAD:
                player.is_alive = False
                cause = self.rng.choice([
                    "dysentery", "exhaustion", "cholera", "measles",
                    "typhoid fever", "a snakebite", "starvation", "hypothermia"
                ])
                default_epitaph = f"Here lies {player.name}, who died of {cause}."
                tombstone = Tombstone(
                    player_name=player.name,
                    party_name=party.party_name,
                    mile_marker=party.distance_traveled,
                    cause=cause,
                    date=current_date,
                    epitaph=default_epitaph,
                    written_by_party_id=party.party_id,
                )
                party.tombstones.append(tombstone)
                events.append({
                    "type": "death",
                    "player_id": pid,
                    "player_name": player.name,
                    "message": f"{player.name} has died of {cause}.",
                    "cause": cause,
                    "tombstone_index": len(party.tombstones) - 1,
                })
        return events

    # ------------------------------------------------------------------
    # Decision Application
    # ------------------------------------------------------------------
    def apply_decision(
        self, party: Party, players: Dict[str, Player], choice: str
    ) -> Tuple[Party, Dict[str, Player], List[Dict[str, Any]]]:
        """Apply a resolved decision to the party."""
        events = []
        if not party.decision_pending:
            return party, players, events

        decision = party.decision_pending
        decision.resolved = True
        decision.result = choice

        if decision.decision_type == DecisionType.PACE:
            pace_map = {"Steady": Pace.STEADY, "Strenuous": Pace.STRENUOUS, "Grueling": Pace.GRUELING}
            if choice in pace_map:
                party.pace = pace_map[choice]
                events.append({"type": "decision", "message": f"Pace set to {choice}."})
            elif choice == "Speed up (increase pace)":
                if party.pace == Pace.STEADY:
                    party.pace = Pace.STRENUOUS
                elif party.pace == Pace.STRENUOUS:
                    party.pace = Pace.GRUELING
                events.append({"type": "decision", "message": f"Pace increased to {party.pace.value}."})
            elif choice == "Slow down (decrease pace)":
                if party.pace == Pace.GRUELING:
                    party.pace = Pace.STRENUOUS
                elif party.pace == Pace.STRENUOUS:
                    party.pace = Pace.STEADY
                events.append({"type": "decision", "message": f"Pace decreased to {party.pace.value}."})
            elif choice == "Increase rations":
                if party.rations == Rations.BARE_BONES:
                    party.rations = Rations.MEAGER
                elif party.rations == Rations.MEAGER:
                    party.rations = Rations.FILLING
                events.append({"type": "decision", "message": f"Rations increased to {party.rations.value}."})
            elif choice == "Decrease rations":
                if party.rations == Rations.FILLING:
                    party.rations = Rations.MEAGER
                elif party.rations == Rations.MEAGER:
                    party.rations = Rations.BARE_BONES
                events.append({"type": "decision", "message": f"Rations decreased to {party.rations.value}."})
            elif choice == "Keep pace and rations":
                events.append({"type": "decision", "message": "Pace and rations unchanged."})

        elif decision.decision_type == DecisionType.RATIONS:
            rations_map = {"Filling": Rations.FILLING, "Meager": Rations.MEAGER, "Bare Bones": Rations.BARE_BONES}
            if choice in rations_map:
                party.rations = rations_map[choice]
                events.append({"type": "decision", "message": f"Rations set to {choice}."})

        elif decision.decision_type == DecisionType.REST:
            if choice == "Rest here":
                party.is_resting = True
                party.rest_days_remaining = self.rng.randint(1, 3)
                party.status = "resting"
                events.append({"type": "decision", "message": f"Resting for {party.rest_days_remaining} days."})
            elif choice == "Hunt for food":
                party.status = "hunting"
                events.append({"type": "decision", "message": "Preparing to hunt."})
            else:
                party.status = "traveling"
                events.append({"type": "decision", "message": "Continuing on."})

        elif decision.decision_type == DecisionType.HUNT:
            if choice == "Hunt":
                party.status = "hunting"
            else:
                party.status = "traveling"

        elif decision.decision_type == DecisionType.RIVER_METHOD:
            party.status = "traveling"  # Will be processed by river crossing handler
            events.append({"type": "decision", "message": f"River crossing method: {choice}."})

        elif decision.decision_type == DecisionType.BUY_SUPPLIES:
            if choice == "Buy supplies":
                party.status = "decision"
                # Would trigger store UI; for now just continue
                party.status = "traveling"
            else:
                party.status = "traveling"

        elif decision.decision_type == DecisionType.VISIT_TOMBSTONE:
            if choice == "Stop and pay respects":
                events.append({"type": "tombstone", "message": "You stopped to pay your respects."})
            else:
                events.append({"type": "tombstone", "message": "You continued past the tombstone."})
            party.status = "traveling"

        elif decision.decision_type == DecisionType.TAKE_SHORTCUT:
            if choice == "Take shortcut":
                # Risk/reward shortcut
                if self._roll_probability(0.4):
                    party.distance_traveled += 20
                    events.append({"type": "decision", "message": "Shortcut saved time!"})
                else:
                    party.distance_traveled = max(0, party.distance_traveled - 10)
                    # 50% chance per member to be affected by the bad shortcut
                    for pid in party.member_ids:
                        if players[pid].is_alive and self._roll_probability(0.5):
                            self._worsen_health(players[pid])
                    events.append({"type": "decision", "message": "Shortcut was a dead end! Lost time and health."})
            else:
                events.append({"type": "decision", "message": "Stayed on the main trail."})
            party.status = "traveling"

        party.decision_pending = None
        return party, players, events

    # ------------------------------------------------------------------
    # Hunting
    # ------------------------------------------------------------------
    def resolve_hunt(self, party: Party, shots_hit: int) -> Tuple[Party, Dict[str, Any]]:
        """Resolve a hunting expedition. shots_hit is number of successful shots (0-N)."""
        result = {"shots_fired": 0, "food_gained": 0, "bullets_used": 0, "message": ""}
        bullets_needed = shots_hit * HUNTING_BULLETS_PER_SHOT

        if party.inventory.bullets < bullets_needed:
            shots_hit = party.inventory.bullets  # Fire whatever is left
            bullets_needed = shots_hit

        if bullets_needed <= 0:
            result["message"] = "No bullets to hunt with!"
            party.status = "traveling"
            return party, result

        party.inventory.bullets -= bullets_needed
        result["bullets_used"] = bullets_needed

        # Each hit yields some food, with depletion factor
        base_per_hit = self.rng.randint(10, 25)
        depletion = 1.0 - party.hunting_region_depletion
        food_gained = int(shots_hit * base_per_hit * depletion)
        food_gained = min(food_gained, HUNTING_MAX_FOOD_PER_HUNT)

        party.inventory.food += food_gained
        party.hunting_region_depletion = min(1.0, party.hunting_region_depletion + 0.15)
        party.status = "traveling"

        result["shots_fired"] = shots_hit
        result["food_gained"] = food_gained
        result["message"] = f"Hunting successful! Gained {food_gained} lbs of food using {bullets_needed} bullets."
        return party, result

    # ------------------------------------------------------------------
    # River Crossing
    # ------------------------------------------------------------------
    def resolve_river_crossing(
        self, party: Party, players: Dict[str, Player], method: str, river_depth: int
    ) -> Tuple[Party, Dict[str, Player], Dict[str, Any]]:
        """Resolve a river crossing. Returns (party, players, result)."""
        result = {"success": True, "message": "", "losses": []}
        players = {pid: deepcopy(p) for pid, p in players.items()}

        # Determine depth category
        depth_cat = "shallow"
        if river_depth >= 11:
            depth_cat = "very_deep"
        elif river_depth >= 7:
            depth_cat = "deep"
        elif river_depth >= 4:
            depth_cat = "moderate"

        method_key = method.lower().replace(" ", "_")
        if method_key == "ford_the_river":
            method_key = "ford"
        elif method_key == "caulk_the_wagon":
            method_key = "caulk"
        elif method_key == "take_a_ferry":
            method_key = "ferry"
        elif method_key == "wait_for_better_conditions":
            method_key = "wait"

        if method_key == "wait":
            party.status = "traveling"
            result["message"] = "You waited a day for better conditions."
            return party, players, result

        if method_key == "ferry":
            alive_count = len([pid for pid in party.member_ids if players[pid].is_alive])
            ferry_cost = (alive_count * FERRY_COST_PER_PERSON) + (party.inventory.oxen * FERRY_COST_PER_OXEN)
            if party.inventory.money >= ferry_cost:
                party.inventory.money -= ferry_cost
                party.status = "traveling"
                result["message"] = f"Ferry crossing successful. Paid ${ferry_cost}."
                return party, players, result
            else:
                method_key = "ford"  # Can't afford ferry, try fording
                result["message"] = "Couldn't afford the ferry! Attempting to ford... "

        mishap_chance = RIVER_MISHAP_CHANCES.get(depth_cat, {}).get(method_key, 0.0)

        if self._roll_probability(mishap_chance):
            # Mishap occurred
            result["success"] = False
            mishap_type = self.rng.choice(["supplies", "oxen", "injury"])

            if mishap_type == "supplies":
                lost_food = min(party.inventory.food, self.rng.randint(50, 150))
                lost_clothes = min(party.inventory.clothing, self.rng.randint(0, 3))
                party.inventory.food -= lost_food
                party.inventory.clothing -= lost_clothes
                result["message"] += f"Disaster! Lost {lost_food} lbs of food and {lost_clothes} sets of clothing."
                result["losses"].append(f"{lost_food} food")

            elif mishap_type == "oxen":
                if party.inventory.oxen > 0:
                    lost = self.rng.randint(1, min(2, party.inventory.oxen))
                    party.inventory.oxen -= lost
                    result["message"] += f"Disaster! {lost} oxen drowned."
                    result["losses"].append(f"{lost} oxen")

            elif mishap_type == "injury":
                alive = [pid for pid in party.member_ids if players[pid].is_alive]
                if alive:
                    victim = self.rng.choice(alive)
                    self._worsen_health(players[victim])
                    result["message"] += f"Disaster! {players[victim].name} was injured."
                    result["losses"].append(f"{players[victim].name} injured")

            # If ford was chosen and very deep, chance of death
            if method_key == "ford" and depth_cat in ("deep", "very_deep"):
                alive = [pid for pid in party.member_ids if players[pid].is_alive]
                if alive and self._roll_probability(0.3):
                    victim = self.rng.choice(alive)
                    players[victim].health_status = HealthStatus.DEAD
                    result["message"] += f" Tragically, {players[victim].name} drowned."
                    result["losses"].append(f"{players[victim].name} drowned")
        else:
            result["message"] += "Crossing successful!"

        party.status = "traveling"
        return party, players, result

    # ------------------------------------------------------------------
    # Store / Trading
    # ------------------------------------------------------------------
    def buy_item(self, party: Party, item: str, quantity: int, price_multiplier: float = 1.0) -> Tuple[Party, Dict[str, Any]]:
        """Buy items at a store. Returns (party, result)."""
        result = {"success": False, "message": ""}
        from game_data import STORE_PRICES

        base_price = STORE_PRICES.get(item, 0)
        if base_price <= 0:
            result["message"] = f"Unknown item: {item}"
            return party, result

        total_price = base_price * quantity * price_multiplier
        if party.inventory.money < total_price:
            result["message"] = "Not enough money!"
            return party, result

        party.inventory.money -= total_price

        if item == "oxen":
            party.inventory.oxen += quantity
        elif item == "food":
            party.inventory.food += quantity
        elif item == "clothing":
            party.inventory.clothing += quantity
        elif item == "bullets":
            party.inventory.bullets += quantity * 20  # boxes of 20
        elif item == "wagon_wheel":
            party.inventory.wagon_wheels += quantity
        elif item == "wagon_axle":
            party.inventory.wagon_axles += quantity
        elif item == "wagon_tongue":
            party.inventory.wagon_tongues += quantity

        result["success"] = True
        result["message"] = f"Bought {quantity} {item}(s) for ${total_price:.2f}."
        return party, result

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _calculate_score(self, party: Party, players: Dict[str, Player]) -> int:
        """Calculate final score for a finished party."""
        alive = [pid for pid in party.member_ids if players[pid].is_alive]
        score = len(alive) * SCORE_SURVIVOR
        score += party.inventory.oxen * SCORE_OXEN
        score += party.inventory.wagon_wheels * SCORE_SPARE_PART
        score += party.inventory.wagon_axles * SCORE_SPARE_PART
        score += party.inventory.wagon_tongues * SCORE_SPARE_PART
        score += int(party.inventory.money * SCORE_PER_5_DOLLARS / 5)
        score += int(party.inventory.food * SCORE_PER_50_FOOD / 50)
        score += party.inventory.clothing * SCORE_PER_CLOTHING
        score += int(party.inventory.bullets * SCORE_PER_BULLET)

        profession_mult = {
            Profession.BANKER: 1,
            Profession.CARPENTER: 2,
            Profession.FARMER: 3,
        }.get(party.profession, 1)

        return score * profession_mult

    # ------------------------------------------------------------------
    # Outfit a new party
    # ------------------------------------------------------------------
    def choose_profession(self, party: Party, profession: Profession) -> Party:
        """Set the party's profession and starting money."""
        from game_data import PROFESSION_STARTING_MONEY
        party.profession = profession
        party.inventory.money = PROFESSION_STARTING_MONEY[profession]
        return party

    def buy_starting_supplies(self, party: Party, purchases: Dict[str, int]) -> Tuple[Party, Dict[str, Any]]:
        """Buy starting supplies at the Independence general store."""
        result = {"success": True, "message": "Purchases applied.", "errors": []}
        for item, qty in purchases.items():
            if qty <= 0:
                continue
            party, buy_result = self.buy_item(party, item, qty, price_multiplier=1.0)
            if not buy_result["success"]:
                result["success"] = False
                result["errors"].append(buy_result["message"])
        if result["errors"]:
            result["message"] = "Some purchases failed."
        return party, result

    def outfit_party(
        self, party: Party, profession: Profession, purchases: Dict[str, int]
    ) -> Tuple[Party, Dict[str, Any]]:
        """Set up a party at the start of the game with profession and purchases."""
        party = self.choose_profession(party, profession)
        party, result = self.buy_starting_supplies(party, purchases)
        party.status = "traveling"
        return party, result
