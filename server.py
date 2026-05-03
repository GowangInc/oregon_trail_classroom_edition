"""Flask-SocketIO server for The Oregon Trail multiplayer game."""

import os
import socket
import sys
from datetime import datetime
from typing import Optional

from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit, ConnectionRefusedError

from session_manager import SessionManager
from game_data import DEFAULT_AUTO_ADVANCE_INTERVAL, contains_swear, filter_swear, Profession

# ---------------------------------------------------------------------------
# Flask & SocketIO Setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# Global state registry: session_id -> SessionManager
sessions: dict[str, SessionManager] = {}
player_to_session: dict[str, str] = {}  # player_id -> session_id
sid_to_player: dict[str, str] = {}      # sid -> player_id

# Auto-advance thread tracking
auto_threads: dict[str, any] = {}
thread_lock = __import__('threading').Lock()

# Server network info (set in __main__)
SERVER_URL: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_local_ip() -> str:
    """Return the local network IP address, fallback to 127.0.0.1."""
    try:
        # Connect to a non-routable address to determine outgoing interface
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("10.254.254.254", 1))
            ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    return ip


def _host_state(mgr: SessionManager) -> dict:
    """Wrap host state with runtime server URL and tombstones so the UI can display them."""
    state = mgr.get_host_state()
    state["server_url"] = SERVER_URL
    state["all_tombstones"] = [ts.to_dict() for ts in mgr.session.tombstones]
    return state


# ---------------------------------------------------------------------------
# HTML Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/host")
def host():
    return render_template("host.html")


@app.route("/map")
def map_view():
    return render_template("map.html")

@app.route("/debug/state")
def debug_state():
    """Return raw state of all active sessions."""
    data = {}
    for sid, mgr in sessions.items():
        data[sid] = _host_state(mgr)
    return data


# ---------------------------------------------------------------------------
# SocketIO Events
# ---------------------------------------------------------------------------
@socketio.on("connect")
def on_connect(auth):
    """Handle client connection."""
    player_id = auth.get("player_id") if auth else None
    is_host_request = auth.get("is_host") if auth else False

    # Host connection: create or reconnect to session
    if is_host_request:
        # If host has a player_id, try to reconnect to existing session (no password needed)
        if player_id and player_id in player_to_session:
            session_id = player_to_session[player_id]
            mgr = sessions.get(session_id)
            if mgr:
                stored_player = mgr.session.players.get(player_id)
                if stored_player and stored_player.is_host:
                    sid_to_player[request.sid] = player_id
                    mgr.session.players[player_id].socket_id = request.sid
                    mgr._host_sid = request.sid
                    join_room("global")
                    emit("connected", {
                        "player_id": player_id,
                        "session_id": mgr.session.session_id,
                        "session_code": mgr.session.session_code,
                        "is_host": True,
                    })
                    emit("session_state", _host_state(mgr))
                    print(f"[{datetime.now()}] Host {player_id} reconnected to session {mgr.session.session_code}")
                    return

        # New host connection: require password
        if auth.get("host_password") != "admin":
            return False  # Reject connection

        # Create new session
        host_id = player_id or f"host_{request.sid[:8]}"
        mgr = SessionManager(host_player_id=host_id, host_name="Teacher")
        sessions[mgr.session.session_id] = mgr
        player_to_session[host_id] = mgr.session.session_id
        sid_to_player[request.sid] = host_id

        # Update host socket id
        mgr.session.players[host_id].socket_id = request.sid
        mgr._host_sid = request.sid

        join_room("global")
        emit("connected", {
            "player_id": host_id,
            "session_id": mgr.session.session_id,
            "session_code": mgr.session.session_code,
            "is_host": True,
        })
        emit("session_state", _host_state(mgr))
        print(f"[{datetime.now()}] Host {host_id} created session {mgr.session.session_code}")
        return

    # Player reconnection
    if player_id and player_id in player_to_session:
        session_id = player_to_session[player_id]
        mgr = sessions.get(session_id)
        if mgr:
            stored_player = mgr.session.players.get(player_id)
            # Only reconnect if the stored player is NOT the host
            if stored_player and not stored_player.is_host:
                player = mgr.reconnect_player(player_id, request.sid)
                if player:
                    sid_to_player[request.sid] = player_id
                    join_room("global")
                    if player.party_id:
                        join_room(f"party_{player.party_id}")
                    emit("connected", {
                        "player_id": player_id,
                        "session_id": session_id,
                        "session_code": mgr.session.session_code,
                        "is_host": player.is_host,
                    })
                    # Send current state
                    emit("session_state", mgr.get_player_state(player_id))
                    print(f"[{datetime.now()}] Player {player.name} reconnected")
                    return

    # New player connection (no player_id yet)
    emit("connected", {"player_id": None, "session_id": None})


@socketio.on("disconnect")
def on_disconnect():
    """Handle client disconnection."""
    player_id = sid_to_player.pop(request.sid, None)
    if not player_id:
        return

    session_id = player_to_session.get(player_id)
    if not session_id:
        return

    mgr = sessions.get(session_id)
    if mgr:
        mgr.remove_player(player_id)
        player = mgr.session.players.get(player_id)
        if player:
            print(f"[{datetime.now()}] Player {player.name} disconnected")


# ---------------------------------------------------------------------------
# Lobby & Party Management
# ---------------------------------------------------------------------------
@socketio.on("join_spectator")
def on_join_spectator(data=None):
    if len(sessions) == 1:
        mgr = next(iter(sessions.values()))
        join_room("global")
        emit("session_state", _host_state(mgr))
        print(f"[{datetime.now()}] Spectator joined session {mgr.session.session_code}")

@socketio.on("join_session")
def on_join_session(data):
    name = data.get("name", "Unknown")
    if contains_swear(name):
        name = filter_swear(name, "???")

    # Find the active session (there should be exactly one)
    mgr = None
    if len(sessions) == 1:
        mgr = next(iter(sessions.values()))

    if not mgr:
        emit("error", {"message": "No active game session. Please wait for your teacher to start the session."})
        return

    player = mgr.add_player(name, request.sid)
    player_to_session[player.player_id] = mgr.session.session_id
    sid_to_player[request.sid] = player.player_id

    join_room("global")
    emit("connected", {
        "player_id": player.player_id,
        "session_id": mgr.session.session_id,
        "session_code": mgr.session.session_code,
        "is_host": False,
    })
    emit("session_state", mgr.get_player_state(player.player_id))

    # Notify everyone of state change
    _broadcast_session_state(mgr)

    print(f"[{datetime.now()}] Player {name} joined session {mgr.session.session_code}")


@socketio.on("create_party")
def on_create_party(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    party_name = data.get("party_name", "New Party")
    party = mgr.create_party(party_name)
    emit("party_created", party.to_dict(include_private=True))
    _broadcast_session_state(mgr)


@socketio.on("assign_party")
def on_assign_party(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    player_id = data.get("player_id")
    party_id = data.get("party_id")
    success = mgr.assign_player_to_party(player_id, party_id)

    if success:
        player = mgr.session.players.get(player_id)
        if player and player.socket_id:
            leave_room("global", sid=player.socket_id)
            join_room(f"party_{party_id}", sid=player.socket_id)
            join_room("global", sid=player.socket_id)
            socketio.emit("assigned_to_party", {"party_id": party_id}, to=player.socket_id)
            socketio.emit("session_state", mgr.get_player_state(player_id), to=player.socket_id)
        _broadcast_session_state(mgr)
    else:
        emit("error", {"message": "Failed to assign player to party."})


@socketio.on("shuffle_parties")
def on_shuffle_parties(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    mgr.shuffle_parties()
    _broadcast_session_state(mgr)


@socketio.on("set_party_name")
def on_set_party_name(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    party_id = data.get("party_id")
    name = data.get("name", "")
    if contains_swear(name):
        name = filter_swear(name, "???")
    mgr.set_party_name(party_id, name)
    _broadcast_session_state(mgr)


@socketio.on("set_party_name_player")
def on_set_party_name_player(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return
    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    name = data.get("name", "")
    if contains_swear(name):
        name = filter_swear(name, "???")

    # Only allow captain during outfitting
    party = mgr.session.parties.get(party_id)
    if not party or party.captain_id != player_id:
        emit("error", {"message": "Only the captain can rename the party."})
        return
    if mgr.session.game_status != "outfitting":
        emit("error", {"message": "Can only rename during outfitting."})
        return

    mgr.set_party_name(party_id, name)
    _broadcast_session_state(mgr)


# ---------------------------------------------------------------------------
# Game Lifecycle
# ---------------------------------------------------------------------------
@socketio.on("start_game")
def on_start_game(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    success = mgr.start_game()
    if success:
        mgr.set_auto_advance(True, DEFAULT_AUTO_ADVANCE_INTERVAL)
        _start_auto_advance(mgr)
        _broadcast_session_state(mgr)
        print(f"[{datetime.now()}] Game started in session {mgr.session.session_code}")
    else:
        emit("error", {"message": "Cannot start game. Create at least one party and assign players."})


@socketio.on("quick_start")
def on_quick_start(data=None):
    """Auto-create parties, assign all unassigned players, auto-outfit, and begin journey."""
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    # Create at least one party if none exist
    if not mgr.session.parties:
        mgr.create_party("Wagon Party 1")

    # Assign all unassigned players to parties evenly
    mgr.shuffle_parties()

    # Ensure parties are filled to 5 with NPCs
    for party in list(mgr.session.parties.values()):
        mgr.fill_party_with_npcs(party.party_id)

    # Start outfitting phase
    success = mgr.start_game()
    if not success:
        emit("error", {"message": "Cannot start game. Make sure at least one player has joined."})
        return

    # Auto-outfit all parties with defaults and begin journey immediately
    for party in list(mgr.session.parties.values()):
        engine = mgr.engines.get(party.party_id)
        if engine:
            purchases = {
                'oxen': 6,
                'food': 400,
                'clothing': 8,
                'bullets': 4,
                'wagon_wheel': 2,
                'wagon_axle': 2,
                'wagon_tongue': 2,
            }
            profession = party.profession or Profession.CARPENTER
            party, _ = engine.outfit_party(party, profession, purchases)
            party.outfitting_complete = True
            mgr.session.parties[party.party_id] = party

    mgr.begin_journey()
    mgr.set_auto_advance(True, DEFAULT_AUTO_ADVANCE_INTERVAL)
    _start_auto_advance(mgr)
    _broadcast_session_state(mgr)
    print(f"[{datetime.now()}] Quick start in session {mgr.session.session_code}")


@socketio.on("end_game")
def on_end_game(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    mgr.end_game()
    _stop_auto_advance(mgr)
    _broadcast_session_state(mgr)


# ---------------------------------------------------------------------------
# Player Actions
# ---------------------------------------------------------------------------
@socketio.on("submit_vote")
def on_submit_vote(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return

    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    decision_id = data.get("decision_id")
    choice = data.get("choice")
    success = mgr.submit_vote(player_id, decision_id, choice)

    if success:
        party_id = mgr.session.players[player_id].party_id
        if party_id:
            party = mgr.session.parties.get(party_id)
            if party and party.decision_pending:
                socketio.emit("vote_tally_update", {
                    "decision_id": decision_id,
                    "votes": party.decision_pending.votes,
                }, to=f"party_{party_id}")
    else:
        emit("error", {"message": "Vote failed."})


@socketio.on("captain_override")
def on_captain_override(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return

    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    decision_id = data.get("decision_id")
    choice = data.get("choice")
    success = mgr.captain_override(player_id, decision_id, choice)

    if success:
        party_id = mgr.session.players[player_id].party_id
        if party_id:
            socketio.emit("captain_override_set", {
                "decision_id": decision_id,
                "choice": choice,
            }, to=f"party_{party_id}")
    else:
        emit("error", {"message": "Override failed. Only the captain can set defaults."})


@socketio.on("resolve_hunt")
def on_resolve_hunt(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return

    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    shots_hit = data.get("shots_hit", 0)
    result = mgr.resolve_hunt(party_id, shots_hit)

    if party_id:
        socketio.emit("hunt_result", result, to=f"party_{party_id}")
        _broadcast_session_state(mgr)


@socketio.on("buy_item")
def on_buy_item(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return

    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    item = data.get("item")
    quantity = data.get("quantity", 1)
    result = mgr.buy_item(party_id, item, quantity)

    emit("buy_result", result)
    _broadcast_session_state(mgr)


@socketio.on("cross_river")
def on_cross_river(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return

    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    method = data.get("method")
    result = mgr.cross_river(party_id, method)

    if party_id:
        socketio.emit("river_result", result, to=f"party_{party_id}")
        _broadcast_session_state(mgr)


# ---------------------------------------------------------------------------
# Host Controls
# ---------------------------------------------------------------------------
@socketio.on("advance_day")
def on_advance_day(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    result = mgr.tick()
    _broadcast_tick_result(mgr, result)


@socketio.on("advance_days")
def on_advance_days(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    count = data.get("count", 1)
    result = mgr.advance_days(count)
    _broadcast_tick_result(mgr, result)


@socketio.on("set_auto_advance")
def on_set_auto_advance(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    enabled = data.get("enabled", False)
    interval = data.get("interval_seconds", 15)
    mgr.set_auto_advance(enabled, interval)

    if enabled:
        _start_auto_advance(mgr)
    else:
        _stop_auto_advance(mgr)

    _broadcast_session_state(mgr)


@socketio.on("pause_game")
def on_pause_game(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    mgr.pause()
    socketio.emit("game_paused", {"by_host": True}, to="global")
    _broadcast_session_state(mgr)


@socketio.on("resume_game")
def on_resume_game(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    mgr.resume()
    socketio.emit("game_resumed", {}, to="global")
    _broadcast_session_state(mgr)


@socketio.on("inject_event")
def on_inject_event(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    party_id = data.get("party_id")
    event_id = data.get("event_id")
    result = mgr.host_inject_event(party_id, event_id)

    if party_id:
        socketio.emit("host_injected_event", {
            "party_id": party_id,
            "event_description": result.get("message", ""),
        }, to="global")
    _broadcast_session_state(mgr)


@socketio.on("host_override_decision")
def on_host_override_decision(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    party_id = data.get("party_id")
    choice = data.get("choice")
    success = mgr.host_override_decision(party_id, choice)

    if success:
        _broadcast_session_state(mgr)
    else:
        emit("error", {"message": "Failed to override decision."})


@socketio.on("host_edit_party")
def on_host_edit_party(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    party_id = data.get("party_id")
    field = data.get("field")
    value = data.get("value")
    success = mgr.host_edit_party(party_id, field, value)

    if success:
        _broadcast_session_state(mgr)
    else:
        emit("error", {"message": "Failed to edit party."})


@socketio.on("host_set_player_health")
def on_host_set_player_health(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    player_id = data.get("player_id")
    health = data.get("health_status")
    success = mgr.host_set_player_health(player_id, health)

    if success:
        _broadcast_session_state(mgr)
    else:
        emit("error", {"message": "Failed to set player health."})


@socketio.on("begin_journey")
def on_begin_journey(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    success = mgr.begin_journey()
    if success:
        mgr.set_auto_advance(True, DEFAULT_AUTO_ADVANCE_INTERVAL)
        _start_auto_advance(mgr)
        _broadcast_session_state(mgr)
        print(f"[{datetime.now()}] Journey began in session {mgr.session.session_code}")
    else:
        emit("error", {"message": "Cannot begin journey. Make sure parties are ready."})


@socketio.on("new_session")
def on_new_session(data=None):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    _stop_auto_advance(mgr)
    old_session_id = mgr.session.session_id
    
    # Notify old clients to refresh
    socketio.emit("error", {"message": "The host started a new session. Please refresh."}, room="global", skip_sid=request.sid)

    mgr.new_session()
    
    # Remove old session ID and add the new one
    if old_session_id in sessions:
        del sessions[old_session_id]
    sessions[mgr.session.session_id] = mgr

    # Reconnect host to the new session
    sid_to_player[request.sid] = host_id
    player_to_session[host_id] = mgr.session.session_id
    mgr.session.players[host_id].socket_id = request.sid
    mgr._host_sid = request.sid

    emit("connected", {
        "player_id": host_id,
        "session_id": mgr.session.session_id,
        "session_code": mgr.session.session_code,
        "is_host": True,
    })
    emit("session_state", _host_state(mgr))
    socketio.emit("event_occurred", {"message": "A new session has started!"}, to="global")
    print(f"[{datetime.now()}] New session started: {mgr.session.session_code}")


@socketio.on("choose_profession")
def on_choose_profession(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return
    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    profession = data.get("profession")
    result = mgr.choose_profession(party_id, profession)
    emit("buy_result", result)
    _broadcast_session_state(mgr)


@socketio.on("choose_month")
def on_choose_month(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return
    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    start_month = data.get("month")
    result = mgr.choose_month(party_id, start_month)
    emit("buy_result", result)
    _broadcast_session_state(mgr)


@socketio.on("buy_supplies")
def on_buy_supplies(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return
    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    item = data.get("item")
    quantity = data.get("quantity", 1)
    result = mgr.buy_starting_supplies(party_id, item, quantity)
    emit("buy_result", result)
    _broadcast_session_state(mgr)


@socketio.on("party_ready")
def on_party_ready(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return
    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    result = mgr.party_outfit_complete(party_id)
    emit("buy_result", result)
    _broadcast_session_state(mgr)


@socketio.on("call_vote")
def on_call_vote(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return
    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    vote_type = data.get("vote_type")
    success = mgr.call_vote(party_id, vote_type)
    if success:
        _broadcast_session_state(mgr)
    else:
        emit("error", {"message": "Cannot call vote right now. A decision may already be pending."})


@socketio.on("submit_epitaph")
def on_submit_epitaph(data):
    player_id = _get_player_id()
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return
    mgr = _get_manager_for_player(player_id)
    if not mgr:
        emit("error", {"message": "Session not found"})
        return

    party_id = data.get("party_id")
    tombstone_index = data.get("tombstone_index", -1)
    epitaph = data.get("epitaph", "")
    if contains_swear(epitaph):
        epitaph = filter_swear(epitaph, "[redacted]")
    success = mgr.submit_epitaph(party_id, tombstone_index, epitaph)
    if success:
        socketio.emit("event_occurred", {"message": f"A new epitaph was written."}, to="global")
        _broadcast_session_state(mgr)
    else:
        emit("error", {"message": "Failed to submit epitaph."})


@socketio.on("host_edit_tombstone")
def on_host_edit_tombstone(data):
    host_id = _require_host()
    if not host_id:
        return
    mgr = _get_manager_for_host(host_id)
    if not mgr:
        return

    tombstone_index = data.get("tombstone_index", -1)
    epitaph = data.get("epitaph", "")
    if contains_swear(epitaph):
        epitaph = filter_swear(epitaph, "[redacted]")
    success = mgr.host_edit_tombstone(tombstone_index, epitaph)
    if success:
        _broadcast_session_state(mgr)
    else:
        emit("error", {"message": "Failed to edit tombstone."})


# ---------------------------------------------------------------------------
# Auto-Advance Background Thread
# ---------------------------------------------------------------------------
def _auto_advance_worker(session_id: str):
    """Background loop that ticks the session at configured intervals."""
    while True:
        mgr = sessions.get(session_id)
        if not mgr:
            break

        interval = mgr.session.auto_advance_interval
        socketio.sleep(interval)

        mgr = sessions.get(session_id)
        if not mgr:
            break
        if not mgr.session.auto_advance_enabled:
            continue
        if mgr.session.game_status not in ("active",):
            continue

        result = mgr.tick()
        _broadcast_tick_result(mgr, result)


def _start_auto_advance(mgr: SessionManager):
    """Start the background auto-advance thread for a session."""
    with thread_lock:
        sid = mgr.session.session_id
        if sid in auto_threads:
            return
        auto_threads[sid] = socketio.start_background_task(_auto_advance_worker, sid)
        print(f"[{datetime.now()}] Auto-advance started for session {mgr.session.session_code}")


def _stop_auto_advance(mgr: SessionManager):
    """Stop the background thread. Note: we can't truly kill it, but the loop will exit on next check."""
    with thread_lock:
        sid = mgr.session.session_id
        mgr.set_auto_advance(False, mgr.session.auto_advance_interval)
        auto_threads.pop(sid, None)
        print(f"[{datetime.now()}] Auto-advance stopped for session {mgr.session.session_code}")


# ---------------------------------------------------------------------------
# Broadcasting Helpers
# ---------------------------------------------------------------------------
def _broadcast_session_state(mgr: SessionManager):
    """Broadcast appropriate state views to all connected clients."""
    # Host gets full state
    if mgr._host_sid:
        socketio.emit("session_state", _host_state(mgr), to=mgr._host_sid)

    # Players get trimmed state
    for player in mgr.session.players.values():
        if player.is_host or not player.socket_id:
            continue
        socketio.emit("session_state", mgr.get_player_state(player.player_id), to=player.socket_id)


def _broadcast_tick_result(mgr: SessionManager, result: dict):
    """Broadcast a tick result including events."""
    session_state = result.get("session_state", _host_state(mgr))
    events = result.get("events", [])

    # Broadcast events globally
    for ev in events:
        socketio.emit("event_occurred", ev, to="global")

    # Send state to host
    if mgr._host_sid:
        socketio.emit("session_state", _host_state(mgr), to=mgr._host_sid)

    # Send state to each player
    for player in mgr.session.players.values():
        if player.is_host or not player.socket_id:
            continue
        socketio.emit("session_state", mgr.get_player_state(player.player_id), to=player.socket_id)


@socketio.on("save_state")
def on_save_state(data=None):
    host_id = _require_host()
    if not host_id: return
    mgr = _get_manager_for_host(host_id)
    if not mgr: return
    
    import json
    import os
    try:
        os.makedirs("saves", exist_ok=True)
        with open("saves/save.json", "w") as f:
            json.dump(mgr.session.to_dict(player_id=host_id), f, indent=2)
        emit("event_occurred", {"message": "Game state saved to disk!"})
    except Exception as e:
        emit("error", {"message": f"Failed to save state: {str(e)}"})

@socketio.on("load_state")
def on_load_state(data=None):
    host_id = _require_host()
    if not host_id: return
    mgr = _get_manager_for_host(host_id)
    if not mgr: return

    import json
    import os
    try:
        if not os.path.exists("saves/save.json"):
            emit("error", {"message": "No save file found."})
            return
        with open("saves/save.json", "r") as f:
            data = json.load(f)
        
        # We need to preserve the current session's host connection details
        current_session_id = mgr.session.session_id
        current_session_code = mgr.session.session_code
        
        if mgr.load_from_dict(data):
            # Restore the active session identifiers so routing still works
            mgr.session.session_id = current_session_id
            mgr.session.session_code = current_session_code
            mgr.session.host_player_id = host_id
            
            _broadcast_session_state(mgr)
            emit("event_occurred", {"message": "Game state loaded successfully!"})
        else:
            emit("error", {"message": "Failed to parse save file."})
    except Exception as e:
        emit("error", {"message": f"Failed to load state: {str(e)}"})


# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------
def _get_player_id() -> Optional[str]:
    return sid_to_player.get(request.sid)


def _require_host() -> Optional[str]:
    player_id = sid_to_player.get(request.sid)
    if not player_id:
        emit("error", {"message": "Not authenticated"})
        return None

    session_id = player_to_session.get(player_id)
    if not session_id:
        emit("error", {"message": "Session not found"})
        return None

    mgr = sessions.get(session_id)
    if not mgr or mgr.session.host_player_id != player_id:
        emit("error", {"message": "Host access required"})
        return None

    return player_id


def _get_manager_for_host(host_id: str) -> Optional[SessionManager]:
    session_id = player_to_session.get(host_id)
    return sessions.get(session_id) if session_id else None


def _get_manager_for_player(player_id: str) -> Optional[SessionManager]:
    session_id = player_to_session.get(player_id)
    return sessions.get(session_id) if session_id else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Prevent auto-reloader from spawning double threads
    use_reloader = False
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        use_reloader = True

    local_ip = _get_local_ip()
    SERVER_URL = f"http://{local_ip}:5001"

    print("=" * 50)
    print("Oregon Trail: Classroom Edition - Server")
    print("=" * 50)
    print(f"Local URL:  {SERVER_URL}/")
    print(f"Host URL:   {SERVER_URL}/host")
    print(f"Network IP: {local_ip}")
    print("=" * 50)

    socketio.run(
        app,
        host="0.0.0.0",
        port=5001,
        debug=use_reloader,
        use_reloader=use_reloader,
        allow_unsafe_werkzeug=True,
    )
