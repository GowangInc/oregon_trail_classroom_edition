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
    MAX_SPARE_PARTS,
    BARLOW_TOLL_ROAD_COST,
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

    @staticmethod
    def calculate_risks(
        party: Party,
        players: Dict[str, Player],
        global_weather: Weather,
        terrain: Terrain,
        river_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return a dict of current risk percentages for display to the player."""
        alive_members = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]

        # Trail events (any event today)
        any_event_prob = 0.0
        wagon_breakdown_prob = 0.0
        for event in TRAIL_EVENTS:
            prob = event.base_probability
            prob *= event.terrain_multipliers.get(terrain, 1.0)
            prob *= event.weather_multipliers.get(global_weather, 1.0)
            any_event_prob = 1 - (1 - any_event_prob) * (1 - prob)
            if event.id in ("broken_wheel", "broken_axle", "broken_tongue"):
                wagon_breakdown_prob = 1 - (1 - wagon_breakdown_prob) * (1 - prob)

        # Illness probability
        if alive_members:
            avg_health_mult = sum(
                ILLNESS_HEALTH_MULTIPLIERS.get(players[pid].health_status, 1.0)
                for pid in alive_members
            ) / len(alive_members)
        else:
            avg_health_mult = 1.0

        illness_prob_per_person = ILLNESS_BASE_PROBABILITY * avg_health_mult * ILLNESS_WEATHER_MULTIPLIERS.get(global_weather, 1.0)
        illness_prob_any = 1 - (1 - illness_prob_per_person) ** max(1, len(alive_members))

        # Hunting yield estimate
        depletion = 1.0 - party.hunting_region_depletion
        est_food_per_bullet = int(17.5 * depletion)

        # Health trend
        pace_impact = PACE_HEALTH_IMPACT[party.pace]
        rations_impact = RATIONS_HEALTH_IMPACT[party.rations]
        weather_impact = WEATHER_HEALTH_IMPACT[global_weather]

        clothing_penalty = 0
        if global_weather in (Weather.COLD, Weather.VERY_COLD, Weather.SNOW):
            clothing_needed = len(alive_members)
            if party.inventory.clothing < clothing_needed:
                clothing_penalty = -1
                if global_weather in (Weather.VERY_COLD, Weather.SNOW):
                    clothing_penalty = -2

        food_penalty = 0
        if party.inventory.food <= 0:
            starvation_days = getattr(party, '_starvation_days', 0)
            if starvation_days >= 10:
                food_penalty = -4
            elif starvation_days >= 5:
                food_penalty = -3
            else:
                food_penalty = -2

        health_trend = pace_impact + rations_impact + weather_impact + clothing_penalty + food_penalty

        # River crossing risks
        river_risks = None
        if river_depth is not None:
            depth_cat = "shallow"
            if river_depth >= 11:
                depth_cat = "very_deep"
            elif river_depth >= 7:
                depth_cat = "deep"
            elif river_depth >= 4:
                depth_cat = "moderate"

            river_risks = {}
            for method_key, label in [
                ("ford", "Ford the river"),
                ("caulk", "Caulk the wagon"),
                ("ferry", "Take a ferry"),
                ("wait", "Wait for better conditions"),
            ]:
                chance = RIVER_MISHAP_CHANCES.get(depth_cat, {}).get(method_key, 0.0)
                river_risks[method_key] = {
                    "mishap_chance_pct": round(chance * 100),
                    "label": label,
                }
            ferry_cost = (len(alive_members) * FERRY_COST_PER_PERSON) + (party.inventory.oxen * FERRY_COST_PER_OXEN)
            river_risks["ferry_cost"] = ferry_cost
            river_risks["depth_feet"] = river_depth
            river_risks["depth_category"] = depth_cat

        return {
            "trail_event_chance_pct": round(min(any_event_prob, 1.0) * 100),
            "wagon_breakdown_chance_pct": round(min(wagon_breakdown_prob, 1.0) * 100),
            "illness_chance_per_person_pct": round(min(illness_prob_per_person, 1.0) * 100),
            "illness_chance_any_pct": round(min(illness_prob_any, 1.0) * 100),
            "hunting_food_per_bullet": est_food_per_bullet,
            "health_trend": health_trend,
            "terrain": terrain.value,
            "weather": global_weather.value,
            "river_risks": river_risks,
        }

    @staticmethod
    def _estimate_river_depth(weather: Weather) -> int:
        """Estimate typical river depth in feet based on weather (for risk display)."""
        base = 2
        if weather == Weather.RAIN:
            base += 4
        elif weather == Weather.SNOW:
            base += 2
        elif weather in (Weather.VERY_HOT, Weather.HOT):
            base = max(1, base - 1)
        return base + 1

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
        original_tombstones = getattr(party, '_global_tombstones', [])
        party = deepcopy(party)
        players = {pid: deepcopy(p) for pid, p in players.items()}
        party._global_tombstones = original_tombstones
        party.member_ids = [pid for pid in party.member_ids if pid in players]
        party.global_date = global_date

        # If party is finished, dead, hunting, or outfitting, nothing happens
        if party.status in ("finished", "dead", "hunting", "outfitting"):
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

        # If a decision is pending, skip travel and new decision creation
        decision_pending = party.decision_pending is not None and not party.decision_pending.resolved

        if not decision_pending:
            # Clear any stale decision
            party.decision_pending = None

        terrain = self._get_terrain_at(party.distance_traveled)
        base_risks = self.calculate_risks(party, players, global_weather, terrain)
        miles_today = 0

        if not decision_pending:
            # 1. Travel
            miles_today = self._calculate_travel(party, global_weather, terrain)
            if miles_today > 0:
                party.distance_traveled = min(party.distance_traveled + miles_today, TOTAL_DISTANCE)
                party.days_at_current_location = 0
            else:
                party.days_at_current_location += 1

        # 2. Consume food
        alive_members = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
        food_consumed = self._consume_food(party, len(alive_members))

        if not decision_pending:
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

        if not decision_pending:
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
                            risk_data=base_risks,
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
                            risk_data=base_risks,
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
                    "description": next_lm.description,
                    "is_fort": next_lm.is_fort,
                    "is_river": next_lm.is_river,
                })
                if next_lm.name == "Willamette Valley, Oregon":
                    party.status = "finished"
                    events.append({
                        "type": "finished",
                        "message": f"{party.party_name} has reached Oregon!",
                    })

                # Only create a landmark decision if none is already pending
                elif party.decision_pending is None:
                    # --- BRANCH POINT: South Pass ---
                    if next_lm.name == "South Pass":
                        party.status = "decision"
                        party.travel_days_since_decision = 0
                        party.decision_pending = Decision(
                            party_id=party.party_id,
                            decision_type=DecisionType.TAKE_SHORTCUT,
                            prompt="You have reached the Continental Divide at South Pass. Which route will you take?",
                            options=["Head to Fort Bridger (safer, fort ahead)", "Take the Green River shortcut (shorter, riskier)"],
                            captain_id=party.captain_id,
                            captain_default="Head to Fort Bridger (safer, fort ahead)",
                            timeout_seconds=10,
                            risk_data=base_risks,
                        )

                    # --- BRANCH POINT: The Dalles ---
                    elif next_lm.name == "The Dalles":
                        party.status = "decision"
                        party.travel_days_since_decision = 0
                        toll_cost = BARLOW_TOLL_ROAD_COST
                        party.decision_pending = Decision(
                            party_id=party.party_id,
                            decision_type=DecisionType.TAKE_SHORTCUT,
                            prompt=f"The Dalles — the end of the overland trail. You must find a way to the Willamette Valley. The Barlow Toll Road costs ${toll_cost}.",
                            options=[f"Take the Barlow Toll Road (${toll_cost}, safer)", "Float down the Columbia River (free, dangerous)"],
                            captain_id=party.captain_id,
                            captain_default=f"Take the Barlow Toll Road (${toll_cost}, safer)",
                            timeout_seconds=10,
                            risk_data=base_risks,
                        )

                    elif next_lm.is_river:
                        party.status = "river_crossing"
                        party.travel_days_since_decision = 0
                        # Snake River gets an Indian guide option
                        options = ["Ford the river", "Caulk the wagon", "Take a ferry", "Wait for better conditions"]
                        if next_lm.name == "Snake River Crossing":
                            options.insert(2, "Hire an Indian guide ($5)")
                        estimated_depth = self._estimate_river_depth(global_weather)
                        river_risks = self.calculate_risks(party, players, global_weather, terrain, river_depth=estimated_depth)
                        party.decision_pending = Decision(
                            party_id=party.party_id,
                            decision_type=DecisionType.RIVER_METHOD,
                            prompt=f"You must cross the {next_lm.name}. {next_lm.description} How will you proceed?",
                            options=options,
                            captain_id=party.captain_id,
                            captain_default="Ford the river",
                            timeout_seconds=5,
                            risk_data=river_risks,
                        )
                    elif next_lm.is_fort:
                        party.status = "decision"
                        party.travel_days_since_decision = 0
                        party.decision_pending = Decision(
                            party_id=party.party_id,
                            decision_type=DecisionType.BUY_SUPPLIES,
                            prompt=f"You have reached {next_lm.name}. {next_lm.description} Would you like to buy supplies?",
                            options=["Buy supplies", "Continue on"],
                            captain_id=party.captain_id,
                            captain_default="Continue on",
                            timeout_seconds=5,
                            risk_data=base_risks,
                        )
                    else:
                        party.status = "decision"
                        party.travel_days_since_decision = 0
                        party.decision_pending = Decision(
                            party_id=party.party_id,
                            decision_type=DecisionType.REST,
                            prompt=f"You have reached {next_lm.name}. {next_lm.description} What would you like to do?",
                            options=["Rest here", "Hunt for food", "Continue on"],
                            captain_id=party.captain_id,
                            captain_default="Continue on",
                            timeout_seconds=5,
                            risk_data=base_risks,
                        )

        # Check if all dead
        alive_members = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
        party.is_alive = bool(alive_members)
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
                if pid in players and players[pid].is_alive and self._roll_probability(0.5):
                    self._worsen_health(players[pid])
            msg += " Some of the party feels sick."

        elif event_id == "lost_trail":
            # No travel today - handled by returning 0 miles, but we already traveled.
            # So instead, we consume extra food and take health penalty.
            party.inventory.food = max(0, party.inventory.food - 10)
            # One random member takes a health hit from the stress
            alive_pids = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
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
                if pid in players and players[pid].is_alive and self._roll_probability(0.5):
                    self._worsen_health(players[pid])
            msg += " The rough going has exhausted the party."

        elif event_id == "heavy_fog":
            # Lose 1 day of travel (no miles gained today, handled by event)
            party.inventory.food = max(0, party.inventory.food - 5)
            msg += " You lost a day waiting for visibility to clear."

        elif event_id == "blizzard":
            # Severe: halt travel, health decline for all, food loss
            party.inventory.food = max(0, party.inventory.food - 20)
            for pid in party.member_ids:
                if pid in players and players[pid].is_alive:
                    self._worsen_health(players[pid])
                    # Extra damage if clothing is insufficient
                    alive_count = len([p for p in party.member_ids if p in players and players[p].is_alive])
                    if party.inventory.clothing < alive_count:
                        self._worsen_health(players[pid])
            msg += " The blizzard has caused severe damage. The party is trapped!"

        elif event_id == "no_grass":
            # Oxen starve, reduced effectiveness
            if party.inventory.oxen > 0 and self._roll_probability(0.3):
                party.inventory.oxen = max(0, party.inventory.oxen - 1)
                msg += " An ox has weakened and died from lack of food."
            else:
                msg += " The oxen are suffering. Travel will be slower."

        elif event_id == "abandoned_wagon":
            # Gain random supplies
            gains = []
            food_found = self.rng.randint(10, 50)
            party.inventory.food += food_found
            gains.append(f"{food_found} lbs food")
            if self._roll_probability(0.5):
                clothes = self.rng.randint(1, 3)
                party.inventory.clothing += clothes
                gains.append(f"{clothes} sets of clothing")
            if self._roll_probability(0.3):
                bullets = self.rng.randint(10, 40)
                party.inventory.bullets += bullets
                gains.append(f"{bullets} bullets")
            if self._roll_probability(0.2):
                part_type = self.rng.choice(["wagon_wheels", "wagon_axles", "wagon_tongues"])
                current = getattr(party.inventory, part_type)
                if current < MAX_SPARE_PARTS:
                    setattr(party.inventory, part_type, current + 1)
                    gains.append(f"1 spare {part_type.replace('_', ' ').rstrip('s')}")
            msg += f" You salvaged: {', '.join(gains)}."

        elif event_id == "npc_trade":
            # NPC offers a trade — randomly beneficial or slightly unfavorable
            trades = [
                ("food", 30, "clothing", 2, "30 lbs of food for 2 sets of clothing"),
                ("bullets", 20, "food", 25, "20 bullets for 25 lbs of food"),
                ("clothing", 3, "bullets", 30, "3 sets of clothing for 30 bullets"),
            ]
            trade = self.rng.choice(trades)
            give_item, give_qty, get_item, get_qty, description = trade
            # Check if party has enough to trade
            current_give = getattr(party.inventory, give_item, 0)
            if current_give >= give_qty:
                setattr(party.inventory, give_item, current_give - give_qty)
                current_get = getattr(party.inventory, get_item, 0)
                setattr(party.inventory, get_item, current_get + get_qty)
                msg += f" You traded {description}."
            else:
                msg += f" They wanted {description}, but you didn't have enough to trade."

        return party, players, msg

    # ------------------------------------------------------------------
    # Health & Illness
    # ------------------------------------------------------------------
    def _update_health(
        self, party: Party, players: Dict[str, Player], weather: Weather
    ) -> Tuple[Party, Dict[str, Player], List[Dict[str, Any]]]:
        """Update health for all party members."""
        events = []
        alive_members = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
        if not alive_members:
            return party, players, events

        # Base health modifiers from pace, rations, weather
        pace_impact = PACE_HEALTH_IMPACT[party.pace]
        rations_impact = RATIONS_HEALTH_IMPACT[party.rations]
        weather_impact = WEATHER_HEALTH_IMPACT[weather]

        # Clothing shortage in cold weather (original: inadequate clothing
        # in cold/mountains causes rapid health drops)
        clothing_penalty = 0
        if weather in (Weather.COLD, Weather.VERY_COLD, Weather.SNOW):
            clothing_needed = len(alive_members)
            if party.inventory.clothing < clothing_needed:
                # Not enough clothing sets for the party
                clothing_penalty = -1
                if weather == Weather.VERY_COLD or weather == Weather.SNOW:
                    clothing_penalty = -2
                events.append({
                    "type": "trail_event",
                    "event_id": "cold_exposure",
                    "message": "Inadequate clothing! The party suffers in the cold.",
                })

        # Food shortage penalty — escalates the longer food is at zero
        food_penalty = 0
        if party.inventory.food <= 0:
            # Track consecutive days without food
            starvation_days = getattr(party, '_starvation_days', 0) + 1
            party._starvation_days = starvation_days
            if starvation_days >= 10:
                food_penalty = -4  # Severe — deaths imminent
            elif starvation_days >= 5:
                food_penalty = -3  # Dire
            else:
                food_penalty = -2  # Bad
            if starvation_days >= 3:
                events.append({
                    "type": "trail_event",
                    "event_id": "starvation",
                    "message": f"The party is starving! No food for {starvation_days} days.",
                })
        else:
            party._starvation_days = 0

        for pid in alive_members:
            if pid not in players:
                continue
            player = players[pid]
            # Apply daily health drift
            total_impact = pace_impact + rations_impact + weather_impact + food_penalty + clothing_penalty

            # Random variance
            total_impact += self.rng.randint(-1, 1)

            if total_impact < 0:
                # Allow up to 2 steps of health loss per day for severe conditions
                steps = min(abs(total_impact), 2)
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
            if pid in players and players[pid].is_alive:
                self._improve_health(players[pid])
                # Second improvement if very poor
                if players[pid].health_status == HealthStatus.VERY_POOR and self._roll_probability(0.5):
                    self._improve_health(players[pid])

    def _check_deaths(
        self, party: Party, players: Dict[str, Player], current_date: date
    ) -> List[Dict[str, Any]]:
        """Check if any players have died today.
        
        Original mechanic: the wagon leader (captain) only becomes vulnerable
        to death after ALL other party members have died.
        """
        events = []
        
        # Determine who's dying today (excluding captain protection logic)
        for pid in party.member_ids:
            if pid not in players:
                continue
            player = players[pid]
            if player.is_alive and player.health_status == HealthStatus.DEAD:
                # Wagon leader dies last: if this is the captain and others
                # are still alive, bounce back to Very Poor instead of dying
                if pid == party.captain_id:
                    other_alive = [
                        p for p in party.member_ids 
                        if p != pid and p in players and players[p].is_alive
                    ]
                    if other_alive:
                        player.health_status = HealthStatus.VERY_POOR
                        events.append({
                            "type": "trail_event",
                            "event_id": "captain_near_death",
                            "message": f"{player.name} is gravely ill but clings to life for the party.",
                        })
                        continue

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
        self, party: Party, players: Dict[str, Player], choice: str, river_depth: int = 3
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
            if "Indian guide" in choice or "indian guide" in choice.lower():
                # Hire an Indian guide — costs $5, reduces risk by ~80%
                guide_cost = 5
                if party.inventory.money >= guide_cost:
                    party.inventory.money -= guide_cost
                    party.status = "traveling"
                    events.append({"type": "decision", "message": f"You hired an Indian guide for ${guide_cost}. They led you safely across the river."})
                else:
                    # Can't afford guide — attempt to ford instead
                    party, players, result = self.resolve_river_crossing(party, players, "Ford the river", river_depth)
                    events.append({"type": "river_crossing", "message": f"Couldn't afford the guide. {result['message']}", "losses": result.get("losses", [])})
            else:
                party, players, result = self.resolve_river_crossing(party, players, choice, river_depth)
                events.append({"type": "river_crossing", "message": result["message"], "losses": result.get("losses", [])})

        elif decision.decision_type == DecisionType.BUY_SUPPLIES:
            if choice == "Buy supplies":
                # Set status to outfitting so the store UI can be shown
                party.status = "outfitting"
                events.append({"type": "decision", "message": "You browse the fort's store."})
            else:
                party.status = "traveling"

        elif decision.decision_type == DecisionType.VISIT_TOMBSTONE:
            if choice == "Stop and pay respects":
                events.append({"type": "tombstone", "message": "You stopped to pay your respects."})
            else:
                events.append({"type": "tombstone", "message": "You continued past the tombstone."})
            party.status = "traveling"

        elif decision.decision_type == DecisionType.TAKE_SHORTCUT:
            # Handle South Pass and The Dalles branch decisions
            if "Fort Bridger" in choice:
                # Safer route via Fort Bridger (default path in landmarks)
                events.append({"type": "decision", "message": "You head toward Fort Bridger. A longer but safer route with supplies ahead."})
                party.status = "traveling"
            elif "Green River" in choice:
                # Shortcut — shorter but riskier, skip Fort Bridger
                events.append({"type": "decision", "message": "You take the Green River shortcut. The trail is rough but shorter."})
                # Skip ahead past Fort Bridger (jump distance closer to Green River)
                party.distance_traveled = max(party.distance_traveled, 1100)
                # Risk: health penalty for the rough shortcut
                for pid in party.member_ids:
                    if pid in players and players[pid].is_alive and self._roll_probability(0.3):
                        self._worsen_health(players[pid])
                party.status = "traveling"
            elif "Barlow" in choice or "Toll Road" in choice:
                # Pay the toll, safer overland route
                if party.inventory.money >= BARLOW_TOLL_ROAD_COST:
                    party.inventory.money -= BARLOW_TOLL_ROAD_COST
                    events.append({"type": "decision", "message": f"You paid ${BARLOW_TOLL_ROAD_COST} for the Barlow Toll Road. The final stretch is tough but manageable."})
                else:
                    events.append({"type": "decision", "message": "You can't afford the toll! You must float down the Columbia River."})
                    # Fall through to Columbia River logic
                    if self._roll_probability(0.4):
                        lost_food = min(party.inventory.food, self.rng.randint(30, 80))
                        party.inventory.food -= lost_food
                        events.append({"type": "trail_event", "event_id": "columbia_mishap", "message": f"The raft struck rocks! Lost {lost_food} lbs of food."})
                        alive = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
                        if alive and self._roll_probability(0.2):
                            victim = self.rng.choice(alive)
                            self._worsen_health(players[victim])
                            self._worsen_health(players[victim])
                            events.append({"type": "trail_event", "event_id": "columbia_injury", "message": f"{players[victim].name} was injured by the rapids!"})
                party.status = "traveling"
            elif "Columbia" in choice or "float" in choice.lower():
                # Float the Columbia — free but dangerous
                events.append({"type": "decision", "message": "You build a raft and float down the Columbia River!"})
                if self._roll_probability(0.4):
                    lost_food = min(party.inventory.food, self.rng.randint(30, 80))
                    party.inventory.food -= lost_food
                    events.append({"type": "trail_event", "event_id": "columbia_mishap", "message": f"The raft struck rocks! Lost {lost_food} lbs of food."})
                    alive = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
                    if alive and self._roll_probability(0.2):
                        victim = self.rng.choice(alive)
                        self._worsen_health(players[victim])
                        self._worsen_health(players[victim])
                        events.append({"type": "trail_event", "event_id": "columbia_injury", "message": f"{players[victim].name} was injured by the rapids!"})
                else:
                    events.append({"type": "decision", "message": "The river ride was exhilarating! You made it through safely."})
                party.status = "traveling"
            else:
                # Generic shortcut (fallback for any old-style shortcut decisions)
                if "Take shortcut" in choice:
                    if self._roll_probability(0.4):
                        party.distance_traveled += 20
                        events.append({"type": "decision", "message": "Shortcut saved time!"})
                    else:
                        party.distance_traveled = max(0, party.distance_traveled - 10)
                        for pid in party.member_ids:
                            if pid in players and players[pid].is_alive and self._roll_probability(0.5):
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
            alive_count = len([pid for pid in party.member_ids if pid in players and players[pid].is_alive])
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
                alive = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
                if alive:
                    victim = self.rng.choice(alive)
                    self._worsen_health(players[victim])
                    result["message"] += f"Disaster! {players[victim].name} was injured."
                    result["losses"].append(f"{players[victim].name} injured")

            # If ford was chosen and very deep, chance of death
            if method_key == "ford" and depth_cat in ("deep", "very_deep"):
                alive = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
                if alive and self._roll_probability(0.3):
                    victim = self.rng.choice(alive)
                    players[victim].health_status = HealthStatus.DEAD
                    players[victim].is_alive = False
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

        if quantity <= 0:
            result["message"] = "Quantity must be greater than 0."
            return party, result

        # Check for spare parts caps
        if item in ("wagon_wheel", "wagon_axle", "wagon_tongue"):
            current_parts = 0
            if item == "wagon_wheel":
                current_parts = party.inventory.wagon_wheels
            elif item == "wagon_axle":
                current_parts = party.inventory.wagon_axles
            elif item == "wagon_tongue":
                current_parts = party.inventory.wagon_tongues
            
            if current_parts + quantity > MAX_SPARE_PARTS:
                result["message"] = f"You can't carry more than {MAX_SPARE_PARTS} {item.replace('_', ' ')}s."
                return party, result

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
        alive = [pid for pid in party.member_ids if pid in players and players[pid].is_alive]
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
