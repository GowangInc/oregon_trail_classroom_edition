/**
 * Socket.IO network layer — handles connection, auth, reconnection, and emits.
 */

const SOCKET_URL = window.location.origin;

let socket = null;
let playerId = null;
let isHost = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

const callbacks = {
    onConnect: null,
    onDisconnect: null,
    onSessionState: null,
    onEventOccurred: null,
    onDecisionRequired: null,
    onVoteTallyUpdate: null,
    onHuntResult: null,
    onRiverResult: null,
    onBuyResult: null,
    onPlayerDied: null,
    onPartyFinished: null,
    onGamePaused: null,
    onGameResumed: null,
    onHostInjectedEvent: null,
    onGameOver: null,
    onError: null,
};

function init(isHostFlag = false, hostPassword = null) {
    isHost = isHostFlag;
    playerId = sessionStorage.getItem('player_id');

    socket = io(SOCKET_URL, {
        auth: {
            player_id: playerId,
            is_host: isHost,
            host_password: hostPassword,
        },
        reconnection: true,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
    });

    socket.on('connect', () => {
        console.log('[Network] Connected, sid:', socket.id);
        reconnectAttempts = 0;
        if (callbacks.onConnect) callbacks.onConnect();
    });

    socket.on('disconnect', (reason) => {
        console.log('[Network] Disconnected:', reason);
        if (callbacks.onDisconnect) callbacks.onDisconnect(reason);
    });

    socket.on('connect_error', (err) => {
        console.error('[Network] Connect error:', err.message);
        reconnectAttempts++;
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            if (callbacks.onError) callbacks.onError({ message: 'Failed to connect after multiple attempts. Please refresh.' });
        }
    });

    // Server events
    socket.on('connected', (data) => {
        if (data.player_id) {
            playerId = data.player_id;
            sessionStorage.setItem('player_id', playerId);
            isHost = data.is_host;
        }
    });

    socket.on('session_state', (data) => {
        if (callbacks.onSessionState) callbacks.onSessionState(data);
    });

    socket.on('event_occurred', (data) => {
        if (callbacks.onEventOccurred) callbacks.onEventOccurred(data);
    });

    socket.on('decision_required', (data) => {
        if (callbacks.onDecisionRequired) callbacks.onDecisionRequired(data);
    });

    socket.on('vote_tally_update', (data) => {
        if (callbacks.onVoteTallyUpdate) callbacks.onVoteTallyUpdate(data);
    });

    socket.on('hunt_result', (data) => {
        if (callbacks.onHuntResult) callbacks.onHuntResult(data);
    });

    socket.on('river_result', (data) => {
        if (callbacks.onRiverResult) callbacks.onRiverResult(data);
    });

    socket.on('buy_result', (data) => {
        if (callbacks.onBuyResult) callbacks.onBuyResult(data);
    });

    socket.on('player_died', (data) => {
        if (callbacks.onPlayerDied) callbacks.onPlayerDied(data);
    });

    socket.on('party_finished', (data) => {
        if (callbacks.onPartyFinished) callbacks.onPartyFinished(data);
    });

    socket.on('game_paused', (data) => {
        if (callbacks.onGamePaused) callbacks.onGamePaused(data);
    });

    socket.on('game_resumed', () => {
        if (callbacks.onGameResumed) callbacks.onGameResumed();
    });

    socket.on('host_injected_event', (data) => {
        if (callbacks.onHostInjectedEvent) callbacks.onHostInjectedEvent(data);
    });

    socket.on('game_over', (data) => {
        if (callbacks.onGameOver) callbacks.onGameOver(data);
    });

    socket.on('error', (data) => {
        console.error('[Network] Server error:', data.message);
        if (callbacks.onError) callbacks.onError(data);
    });
}

function emit(event, data) {
    if (!socket || !socket.connected) {
        console.warn('[Network] Not connected, cannot emit:', event);
        return false;
    }
    socket.emit(event, data);
    return true;
}

function getPlayerId() {
    return playerId;
}

function isConnected() {
    return socket && socket.connected;
}

function on(event, handler) {
    if (callbacks[event] !== undefined) {
        callbacks[event] = handler;
    }
}

export {
    init,
    emit,
    getPlayerId,
    isConnected,
    on,
};
