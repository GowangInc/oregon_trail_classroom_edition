# Agent Instructions — Oregon Trail: Classroom Edition

## Project Philosophy
- **Keep it simple and retro.** Text-and-CSS-heavy, terminal aesthetic. No canvas/WebGL except for lightweight mini-games.
- **No build tools.** Clone, create a venv, install deps, and run with `python server.py`.
- **Server is the source of truth.** All game logic lives in Python. The frontend is a dumb terminal that renders state and sends player inputs.
- **Multi-party first.** Every design decision must account for 2–8 parties existing simultaneously on the same trail.
- **Classroom-optimized.** Auto-advance by default so the teacher isn't micromanaging. Host retains god-mode override.

## Coding Standards

### Python
- **Style**: PEP 8. Max line length 100.
- **Typing**: Use type hints on all function signatures and class attributes.
- **Docstrings**: Google-style docstrings for all public modules, classes, and methods.
- **Dependencies**: Flask, Flask-SocketIO. Install into a venv. No eventlet, no ORMs, no Redis, no databases.
- **Engine purity**: `party_engine.py` and `game_data.py` must NOT import Flask. They operate on plain Python objects.
- **Error handling**: Explicit error returns or exceptions for unexpected cases. Log server-side; send user-friendly `error` events to clients.

### JavaScript
- **Style**: Consistent 2-space indentation. Semicolons required.
- **Modules**: ES6 modules (`import`/`export`). One module per responsibility.
- **No frameworks.** No React, Vue, jQuery. Native DOM APIs only.
- **State**: Frontend holds no authoritative game state. It receives `session_state` and renders. Local state is only for UI concerns (current screen, animations, input buffers).
- **Socket.IO**: All real-time communication goes through `network.js`. Other modules call wrapper functions, not `socket.emit` directly.
- **Reconnection**: Store `player_id` in `sessionStorage`. Send as `auth: { player_id }` on connect.

### CSS
- **Style**: BEM naming convention (`block__element--modifier`).
- **Design tokens**: CSS variables for colors, fonts, spacing in `:root`.
- **Responsive**: Usable on 13"+ laptops. Mobile is nice-to-have.
- **Aesthetic**: Green phosphor on soft black (`#4af626` on `#0a0a0a`) default. Monospace font stack (VT323 preferred). Host dashboard uses neutral dark theme.
- **Accessibility**: Respect `prefers-reduced-motion`. Provide focus indicators. Use `aria-live` on event log.

## Architecture

### Game Data (`game_data.py`)
- All game constants live here: landmarks, distances, prices, events, weather weights, terrain segments, scoring formulas.
- Events are defined as `TrailEvent` dataclasses with `base_probability`, `terrain_multipliers`, and `weather_multipliers`.
- **No logic** — only data and enums.

### Models (`models.py`)
- Plain dataclasses for `Player`, `Party`, `Inventory`, `Decision`, `Tombstone`, `GameSession`.
- Each model has `to_dict()` and `from_dict()` for JSON serialization.
- Validation in `__post_init__` or property setters. No engine logic.

### Party Engine (`party_engine.py`)
- `PartyEngine` instantiated per party with an optional `seed` for deterministic testing.
- Core method: `tick(party, players, global_date, global_weather) -> (party, players, events)`.
- Also exposes: `apply_decision()`, `resolve_hunt()`, `resolve_river_crossing()`, `buy_item()`, `outfit_party()`.
- Uses `random.Random` internally. Does NOT perform I/O.
- Returns complete state objects (deep-copied). Caller replaces old state with new.

### Session Manager (`session_manager.py`)
- Singleton-like object instantiated in `server.py`.
- Holds `GameSession`, all `PartyEngine` instances, and the auto-advance timer.
- Orchestrates the daily tick:
  1. Lock shared state
  2. Resolve pending decisions with defaults
  3. Call `PartyEngine.tick()` for each active party
  4. Compute proximity between parties
  5. Advance global date and weather
  6. Build and broadcast state snapshots
- Handles host commands: pause, resume, inject events, edit parties, force decisions.
- **Thread-safe**: All state mutations happen under `threading.Lock()`.

### Server (`server.py`)
- Thin Flask-SocketIO layer.
- **Threading async mode**: `async_mode='threading'` — simpler than eventlet, perfectly adequate for classroom scale (~32 players).
- **Room structure**:
  - `'global'` — all connected clients receive ticks and world state
  - `'party_{party_id}'` — party-private decisions and state updates
  - `request.sid` (implicit) — private messages to individual clients
- **Reconnection**: Map persistent `player_id` to `request.sid`. On connect, look up party and rejoin rooms automatically. Emit full `session_state` to catch up.
- Keep event handlers under 30 lines. Delegate to `SessionManager`.

## SocketIO Patterns (from Research)

### Background Timer (Auto-Advance)
```python
# Use socketio.start_background_task() — works with threading mode
game_thread = socketio.start_background_task(game_loop)

# Inside the loop, use socketio.sleep()
def game_loop():
    while True:
        socketio.sleep(15)
        with state_lock:
            snapshot = session_manager.tick()
        socketio.emit('session_state', snapshot, to='global')
```

### Broadcasting
```python
# Global broadcast
socketio.emit('world_update', data, to='global')

# Party-only
socketio.emit('party_update', data, to=f'party_{party_id}')

# Host-only private
socketio.emit('host_dashboard', data, to=host_sid)

# Exclude sender
emit('player_moved', data, to='global', include_self=False)
```

### State Locking
```python
# Use RLock (reentrant) so nested calls within the same thread don't deadlock
state_lock = threading.RLock()

with state_lock:
    # Mutate state
    pass
```

## Multi-Party Rules to Enforce

### Party Formation
1. **Host authority**: Only host can create parties, assign/reassign players, shuffle randomly, start game.
2. **Party size**: 1–4 players. Hard cap at 4.
3. **No mid-game switching**: Once active, players cannot change parties.

### Decision Making
4. **Party voting**: All living members vote. Majority wins.
5. **Captain tie-breaker**: Wagon Captain breaks ties. If Captain abstains, default wins.
6. **Auto-resolve**: 10s timeout during auto-advance; 60s when paused.
7. **Dead players spectate**: Can see state, cannot vote.

### Inter-Party Mechanics
8. **Proximity gating**: Trade/messaging only allowed when ≤5 miles apart. Enforce server-side.
9. **Hunting depletion**: Tracked per party's `hunting_region_depletion` (0.0–1.0). Server enforces reduced yields.
10. **Tombstones**: Global read-only state. Parties passing within 1 mile see them.

### Global Clock
11. **Auto-advance default**: Background timer ticks all parties simultaneously.
12. **Pause**: Host can freeze everything. Decision timers extend.
13. **Weather global**: All parties share the same weather, computed once per tick.

## Naming Conventions
- **Python**: `snake_case` variables/functions, `PascalCase` classes, `SCREAMING_SNAKE_CASE` constants.
- **JS/CSS**: `camelCase` JS variables/functions, `kebab-case` CSS classes and filenames, `PascalCase` JS classes.

## State Update Protocol
- Server broadcasts `session_state` on every tick.
- Host receives **full** state (all party inventories, all player health).
- Players receive **trimmed** state: their party's full data + other parties' public stats (name, distance, status, living count).
- Rationale: Even with 8 parties, full JSON is <30KB. Simplicity beats bandwidth.
- Frontend completely re-renders on each update. Use `innerHTML` or template replacement.

## Host Dashboard
- Separate page (`/host`) with its own JS (`host.js`).
- Host is a `Player` with `is_host=True`, no `party_id`.
- Host can see everything but cannot vote or take in-game actions.

## Debugging & Logging
- Server logs all engine events to stdout with timestamps.
- Add `?debug=1` query param to enable verbose console logging.
- Provide `/debug/state` HTTP GET endpoint returning full `GameSession` as JSON.

## Environment Setup
Always use a virtual environment:
```bash
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Testing
- Use `pytest` for Python tests.
- Test `PartyEngine` deterministically by passing a fixed `seed`.
- Do not test Flask handlers; test engine and session manager directly.

## Auto-Advance Implementation Notes
- Use `socketio.start_background_task()` for the timer loop.
- Use `socketio.sleep()` inside the loop (not `time.sleep`).
- Acquire `state_lock` before mutating, release before emitting if possible.
- Cancel the timer thread on pause; start fresh on resume.
- Resolve pending decisions with defaults BEFORE ticking to ensure valid state.
- Manual advance should reset the auto-advance timer to prevent double-ticks.
- Guard against Flask reloader duplication: `if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN')`.

## Forbidden Patterns
- ❌ Do NOT store game state in Flask `session` or unsafe globals. Use a single `SessionManager` instance on the Flask app.
- ❌ Do NOT let the frontend calculate game outcomes. Frontend sends intent; server resolves and returns.
- ❌ Do NOT let clients claim proximity eligibility. Server validates all inter-party actions.
- ❌ Do NOT use `eval()`, `exec()`, or dynamic code execution.
- ❌ Do NOT commit `__pycache__`, IDE configs, or lockfiles.
- ❌ Do NOT use `threading.Lock()` if nested calls might reacquire. Use `threading.RLock()` instead.

## Commit Message Style
```
<type>: <short summary>

<body>
```
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
