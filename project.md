# Oregon Trail: Classroom Edition

## Overview
A complete recreation of the classic *The Oregon Trail* rebuilt for the classroom. A teacher hosts a Python server and assigns students into 2–8 wagon parties (up to 4 students each). All parties travel the same trail simultaneously, experiencing the same weather and calendar, but each party controls its own pace, rations, and strategy. Parties work together internally via voting, but externally they compete (or cooperate) with other parties they meet on the trail.

## Tech Stack
- **Backend**: Python 3.11+, Flask, Flask-SocketIO (WebSockets), eventlet
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6+)
- **No build step required** — `pip install -r requirements.txt && python server.py`

## Session Flow
1. **Teacher Host** runs `python server.py` and opens the host dashboard at `/host`.
2. **Students** connect via browser to `/`, enter their name, and join the lobby.
3. **Host assigns parties**: drag-and-drop or random shuffle into named wagon parties.
4. **Host starts the game**. All parties enter the **Outfitting Phase** simultaneously.
5. **Auto-Advance Mode (Default)**: Server ticks every **15 seconds** (configurable 5–60s). The game plays itself — parties travel, eat, encounter events, and vote on decisions automatically.
6. **Host Override**: At any time, the host can **pause**, **inject events**, **edit party state**, **force decisions**, or **manual-advance** days.
7. **Inter-party encounters**: When parties are within 5 miles, they can trade or message.
8. **Win/Lose**: First party to Oregon City wins bragging rights. Game continues until all parties finish or die.

---

## Core Concepts

### The Global Clock
- A single calendar runs for the entire session: `date`, `weather`, and `season` are global.
- **Auto-Advance**: Background thread ticks at configurable interval (default 15s).
- **Manual Advance**: Host can click "Advance 1 Day" or "Advance 7 Days" anytime.
- **Pause**: Freezes all timers. Decision windows extend to 60s for classroom discussion.
- Random events are rolled per-party using the same global weather/season context.

### Party (Wagon)
- Self-contained unit: 1–4 students, one shared inventory, one wagon, one set of oxen.
- **Wagon Captain** (first player to join, or host-assigned) breaks ties on votes.
- All significant decisions are voted on by living party members.
- Parties make decisions independently. One party resting does not stop another.

### Player
- Student connected via browser. Belongs to exactly one party for the entire game.
- Sees their party's full state, a global leaderboard, and encounter notifications.
- Dead players become spectators (can see, cannot vote).

### Trail & Mileage
- The trail is **2,094 miles** with 18 shared landmarks.
- Each party tracks its own `distance_traveled` independently.
- Terrain types between landmarks affect speed and event probabilities.

---

## Auto-Advance & Decision Mechanics

### Auto-Advance (Default)
- Once the host clicks **Start**, the server automatically advances the global day every N seconds.
- Students vote on decisions with a **10-second window** during auto-play.
- If no majority, the Wagon Captain's default wins → game keeps moving.

### Host Override Powers
| Action | Effect |
|--------|--------|
| **Pause/Resume** | Freezes all timers; extends vote windows to 60s |
| **Inject Event** | Click "Cholera Outbreak," "Broken Wagon," etc. on any party instantly |
| **Edit Party** | Modify inventory, health, distance, money from dashboard |
| **Force Decision** | Override any pending party vote |
| **Manual Advance** | Skip 1 day, 7 days, or to next landmark |
| **Speed Control** | Adjust auto-tick interval (5–60s) on the fly |

### Decision Resolution
1. All living members vote. Majority wins.
2. Tie → Wagon Captain's choice wins.
3. No votes → default option wins.
4. During auto-advance: 10-second timeout.
5. While paused: 60-second timeout for discussion.

---

## Multi-Party Mechanics

### Leaderboard / Progress View
- Persistent sidebar showing all parties: name, members, current landmark, miles traveled, living/dead count.
- Visualized as a horizontal progress chart.

### Proximity Detection
After each tick, server checks pairwise distances:

| Gap | Interaction |
|-----|-------------|
| 0–5 miles | **Neighbors**: Can trade, message, see tombstones |
| 6–20 miles | **Within Sight**: Notified of nearby party |
| 21+ miles | No interaction |

### Inter-Party Actions (Neighbors Only)
- **Trade**: Offer food, bullets, clothing, parts, money. Both parties vote.
- **Message**: Short text (host can disable).
- **Shared Intel**: Recent river crossings shared with neighbors.

### Competition & Scarcity
- **Hunting Depletion**: Wildlife drops for all parties in the same trail segment.
- **Fort Supply Limits**: Limited stock at forts — first party gets best prices.
- **Tombstones**: Dead players leave memorials at their mile marker. Other parties see them.

---

## Party Internal Mechanics

### Professions
Each party picks a profession at outfitting, affecting starting money and final score multiplier:

| Profession | Starting Money | Score Multiplier |
|------------|---------------|------------------|
| Banker from Boston | $1,600 | ×1 |
| Carpenter from Ohio | $800 | ×2 |
| Farmer from Illinois | $400 | ×3 |

### Starting Purchases
Parties spend their profession's starting money on:
- **Oxen** ($40/yoke) — travel speed
- **Food** ($0.10/lb) — daily consumption
- **Clothing** ($10/set) — cold weather survival
- **Bullets** ($2/box of 20) — hunting
- **Spare Parts** ($10 each) — wheels, axles, tongues

### Pace & Rations
| Pace | Miles/Day | Health Impact | Oxen Wear |
|------|-----------|---------------|-----------|
| Steady | 12 | None | Normal |
| Strenuous | 16 | -1/day | 1.5× |
| Grueling | 20 | -3/day | 2.0× |

| Rations | Food/Person/Day | Health Impact |
|---------|-----------------|---------------|
| Filling | 3 lbs | +1/day |
| Meager | 2 lbs | None |
| Bare Bones | 1 lb | -2/day |

### Random Trail Events
- Wagon wheel / axle / tongue breaks (mitigated by spare parts)
- Oxen injured or dies
- Thief steals supplies at night
- Bad water (health penalty)
- Lost trail (wasted day)
- Find wild fruit (+food)
- Wrong path (-miles, -supplies)
- Grave site (flavor)
- Rough trail (exhaustion)

### Illness & Health
- 5 health tiers: Healthy → Fair → Poor → Very Poor → Dead
- Daily health drift based on: pace, rations, weather, food availability
- Illness chance based on: current health, weather, random roll
- Illness types: exhaustion, dysentery, cholera, measles, typhoid, snakebite, broken arm/leg
- Resting at landmarks improves health

### River Crossing
At each river landmark, parties vote on method:
- **Ford** — free, risky if >2.5 ft deep
- **Caulk Wagon** — moderate risk, better for deep water
- **Ferry** — safe, costs $5/person + $3/oxen
- **Wait** — lose a day, conditions may improve

Mishaps: lost supplies, drowned oxen, injured members, death (ford in deep water)

### Hunting Mini-Game
- Simple shooting gallery (canvas/DOM)
- Animals: rabbit, squirrel, deer, elk, bear, buffalo
- Food yield: 3–100 lbs depending on animal
- Bullets consumed per shot
- Overhunting depletes region (0–100%)

### Scoring
At Oregon City, score is calculated as:
- Survivors × 500
- Oxen × 4
- Spare parts × 2
- Money ÷ 5
- Food ÷ 50
- Clothing × 2
- Bullets × 0.1
- **Multiplied by profession multiplier**

---

## Trail & Landmarks

| # | Landmark | Miles | Type |
|---|----------|-------|------|
| 1 | Independence, Missouri | 0 | Start |
| 2 | Kansas River Crossing | 102 | River |
| 3 | Big Blue River Crossing | 185 | River |
| 4 | Fort Kearney | 304 | Fort |
| 5 | Chimney Rock | 554 | Scenic |
| 6 | Fort Laramie | 640 | Fort |
| 7 | Independence Rock | 830 | Scenic |
| 8 | South Pass | 932 | Mountain |
| 9 | Fort Bridger | 1,069 | Fort |
| 10 | Green River Crossing | 1,132 | River |
| 11 | Soda Springs | 1,235 | Scenic |
| 12 | Fort Hall | 1,300 | Fort |
| 13 | Snake River Crossing | 1,450 | River |
| 14 | Fort Boise | 1,534 | Fort |
| 15 | Blue Mountains | 1,640 | Mountain |
| 16 | Fort Walla Walla | 1,710 | Fort |
| 17 | The Dalles | 1,930 | River |
| 18 | Willamette Valley, Oregon | 2,094 | End |

### Terrain Segments
1. Independence → Fort Kearney: **Prairie**
2. Fort Kearney → Fort Laramie: **Prairie**
3. Fort Laramie → South Pass: **Mountains**
4. South Pass → Green River: **Desert**
5. Green River → Fort Hall: **Mountains**
6. Fort Hall → Fort Boise: **Desert**
7. Fort Boise → Fort Walla Walla: **Mountains**
8. Fort Walla Walla → The Dalles: **Forest**
9. The Dalles → Oregon City: **Mountains**

### Weather (Global, by Month)
- **March**: Cold, Cool, Warm
- **April**: Cold, Cool, Warm, Rain
- **May**: Cool, Warm, Hot, Rain
- **June**: Warm, Hot, Very Hot, Rain
- **July**: Hot, Very Hot
- **August**: Hot, Very Hot, Warm
- **September**: Warm, Cool, Hot, Rain
- **October**: Cool, Cold, Warm, Rain
- **November**: Cold, Very Cold, Snow
- **December**: Very Cold, Cold, Snow

---

## Server Architecture

### Game Loop (Auto-Advance)
```
Background timer fires every N seconds
├── If paused: skip
├── Resolve all pending decisions with defaults
├── For each active party:
│   ├── PartyEngine.tick() → travel, food, events, health
│   ├── Check landmark arrival → trigger decisions
│   └── Check deaths / win condition
├── Compute proximity between all parties
├── Advance global date + update weather
├── Build state snapshots (full for host, trimmed for players)
├── Broadcast via SocketIO rooms
└── Check if all parties finished/dead → end game
```

### State Management
- `GameSession` (models.py): Top-level dataclass holding all parties, players, global state.
- `SessionManager` (session_manager.py): Orchestrates ticks, auto-advance timer, host commands, broadcasts.
- `PartyEngine` (party_engine.py): Per-party pure Python game logic. Returns `(party, players, events)`.
- **No database.** All state in-memory. Sessions disappear when server restarts.

---

## Data Models

### Player
```python
player_id: str          # stable UUID
name: str
socket_id: str | None
party_id: str | None
is_host: bool
is_alive: bool
health_status: HealthStatus
profession: Profession
joined_at: datetime
last_seen: datetime
```

### Party
```python
party_id: str
party_name: str
member_ids: list[str]
captain_id: str
inventory: Inventory    # oxen, food, clothing, bullets, parts, money
profession: Profession
pace: Pace
rations: Rations
distance_traveled: int
current_landmark_index: int
miles_to_next: int
status: str             # outfitting, traveling, decision, hunting, river_crossing, resting, finished, dead
decision_pending: Decision | None
neighbor_party_ids: list[str]
event_log: list[dict]
tombstones: list[Tombstone]
score: int
hunting_region_depletion: float
```

### Inventory
```python
oxen: int
food: int           # pounds
clothing: int       # sets
bullets: int        # individual
wagon_wheels: int
wagon_axles: int
wagon_tongues: int
money: float        # dollars
```

### Decision
```python
decision_id: str
decision_type: DecisionType
prompt: str
options: list[str]
votes: dict[player_id, str]
captain_id: str
captain_default: str
timeout_seconds: int
resolved: bool
result: str | None
```

### GameSession
```python
session_id: str
session_code: str           # 4-letter join code
game_status: str            # lobby, outfitting, active, paused, ended
global_date: date
global_weather: Weather
parties: dict[str, Party]
players: dict[str, Player]
host_player_id: str
auto_advance_enabled: bool
auto_advance_interval: int  # seconds
tick_count: int
tombstones: list[Tombstone]
```

---

## Socket Events

### Client → Server
| Event | Payload | Auth |
|-------|---------|------|
| `join_session` | `{name}` | Any |
| `reconnect` | `{player_id}` | Any |
| `assign_party` | `{player_id, party_id}` | Host only |
| `create_party` | `{party_name}` | Host only |
| `shuffle_parties` | `{}` | Host only |
| `start_game` | `{}` | Host only |
| `submit_vote` | `{decision_id, choice}` | Party member |
| `captain_override` | `{decision_id, choice}` | Captain only |
| `advance_day` | `{}` | Host only |
| `advance_days` | `{count}` | Host only |
| `set_auto_advance` | `{enabled, interval_seconds}` | Host only |
| `pause_game` | `{}` | Host only |
| `resume_game` | `{}` | Host only |
| `inject_event` | `{party_id, event_id}` | Host only |
| `host_override_decision` | `{party_id, decision_id, choice}` | Host only |
| `host_edit_party` | `{party_id, field, value}` | Host only |
| `hunt_action` | `{party_id, shots_hit}` | Party member |
| `buy_item` | `{party_id, item, quantity}` | Party member |

### Server → Client
| Event | Payload |
|-------|---------|
| `session_state` | Full or trimmed session state |
| `party_state_update` | `{party_id, party_state}` |
| `decision_required` | `{party_id, decision}` |
| `vote_tally_update` | `{decision_id, votes_so_far}` |
| `event_occurred` | `{party_id, event}` |
| `neighbor_alert` | `{party_id, neighbor_party_id, distance}` |
| `player_died` | `{party_id, player_name, cause}` |
| `tombstone_discovered` | `{mile_marker, tombstone}` |
| `party_finished` | `{party_id, rank, survivors, score}` |
| `game_paused` | `{by_host}` |
| `game_resumed` | `{}` |
| `host_injected_event` | `{party_id, event_description}` |
| `game_over` | `{final_rankings}` |
| `error` | `{message}` |

---

## UI Screens

### Player Screens
1. **Join Screen**: Enter name, connect.
2. **Lobby**: See assigned party and members. Wait for host.
3. **Outfitting**: General store. Shared budget. Party votes on purchases.
4. **Trail (Main Game)**:
   - Status bar: date, weather, health, food, next landmark
   - Party roster with health and captain indicator
   - Inventory summary
   - Progress bar / map with all parties
   - Scrollable event log
   - Decision vote panel with countdown timer
5. **Hunting Overlay**: Canvas mini-game
6. **River Crossing**: Stats + method options + outcome
7. **Game Over**: Result, rank, stats recap

### Host Dashboard (`/host`)
- God-view map of all party positions
- Party management: rename, reassign, create
- **Auto-advance controls**: Start/Stop/Pause, interval slider
- **Manual overrides**: Advance 1/7 days, skip to landmark
- **Event injection**: Clickable event list per party
- **Party editor**: Edit inventory, health, distance, money
- **Decision override**: Force-resolve pending votes
- End game / export scores

---

## File Structure
```
/
├── server.py                 # Flask-SocketIO entry point
├── session_manager.py        # Auto-advance timer, orchestration, host commands
├── party_engine.py           # Pure game logic (tick, events, health, travel)
├── game_data.py              # All constants: landmarks, prices, events, mechanics
├── models.py                 # Dataclasses: Player, Party, Inventory, Decision, GameSession
├── requirements.txt
├── project.md                # This file
├── agent.md                  # Coding standards & architecture rules
├── static/
│   ├── css/
│   │   └── style.css         # Retro terminal CRT aesthetic
│   └── js/
│       ├── main.js           # Entry point, screen router
│       ├── network.js        # Socket.IO wrapper, reconnect
│       ├── ui.js             # DOM rendering, decision modals, event log
│       ├── map.js            # Trail progress chart
│       ├── hunting.js        # Hunting mini-game
│       ├── river.js          # River crossing UI
│       └── host.js           # Host dashboard logic
└── templates/
    ├── index.html            # Player view
    └── host.html             # Host dashboard
```

---

## Installation & Running

### 1. Create a virtual environment (recommended)
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows (CMD)
python -m venv venv
venv\Scripts\activate.bat

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server
```bash
python server.py
```
- **Host**: Open browser to `http://localhost:5000/host`
- **Students**: Open browser to `http://<your-computer-ip>:5000/`

### Quick Start (Windows)
A `run.bat` script is included for convenience:
```bash
run.bat
```

---

## Stretch Goals (Post-MVP)
- [ ] In-game chat (party-only and global)
- [ ] Custom tombstone epitaphs
- [ ] Detailed scoreboard with survival rate, avg pace, etc.
- [ ] Difficulty presets (Easy / Normal / Hardcore)
- [ ] Save/load session state to JSON
- [ ] Bot players to fill empty party slots
- [ ] The Dalles raft-ride mini-game
- [ ] Teacher lesson plan tie-ins (history pop-ups at landmarks)
- [ ] Sound effects (8-bit beeps, ambient wind)
