/**
 * Player entry point — wires network events to UI and handles user input.
 */

import * as Network from './network.js';
import * as UI from './ui.js';
import * as Hunting from './hunting.js';

let myPlayerId = null;
let myPartyId = null;
let lastState = null;

// ------------------------------------------------------------------
// Init
// ------------------------------------------------------------------
Network.init(false);

Network.on('onConnect', () => {
    console.log('[Main] Connected to server');
});

Network.on('onDisconnect', (reason) => {
    UI.addEventToLog({ message: `Disconnected: ${reason}. Trying to reconnect...` });
});

Network.on('onSessionState', (state) => {
    handleStateUpdate(state);
});

Network.on('onEventOccurred', (event) => {
    UI.addEventToLog(event);
    // Show epitaph editor on death for captains
    if (event.type === 'death' && event.player_name) {
        const state = lastState || {};
        const myPlayerId = Network.getPlayerId();
        const me = state.players ? state.players[myPlayerId] : null;
        if (me && me.party_id) {
            const party = state.parties ? state.parties[me.party_id] : null;
            if (party && party.captain_id === myPlayerId && event.tombstone_index !== undefined) {
                UI.showEpitaphEditor(event.player_name, me.party_id, event.tombstone_index);
            }
        }
    }
});

Network.on('onDecisionRequired', (data) => {
    // Decisions are handled via state updates in updateGame
});

Network.on('onVoteTallyUpdate', (data) => {
    // Handled in UI update
});

Network.on('onHuntResult', (result) => {
    UI.addEventToLog({ message: result.message || 'Hunt completed.' });
});

Network.on('onRiverResult', (result) => {
    UI.addEventToLog({ message: result.message || 'River crossing completed.' });
});

Network.on('onPlayerDied', (data) => {
    UI.addEventToLog({ type: 'death', message: data.message });
});

Network.on('onPartyFinished', (data) => {
    UI.addEventToLog({ type: 'landmark', message: `${data.party_name || 'A party'} has reached Oregon!` });
    if (data.party_id === myPartyId) {
        const stats = `
            <p>Rank: ${data.rank || '?'}</p>
            <p>Survivors: ${data.survivors || 0}</p>
            <p>Score: ${data.score || 0}</p>
        `;
        UI.showGameOver('OREGON CITY', 'You have completed the journey!', stats);
    }
});

Network.on('onGamePaused', () => {
    UI.addEventToLog({ message: 'Game paused by host.' });
});

Network.on('onGameResumed', () => {
    UI.addEventToLog({ message: 'Game resumed.' });
});

Network.on('onHostInjectedEvent', (data) => {
    UI.addEventToLog({ message: `[HOST] ${data.event_description}` });
});

Network.on('onGameOver', (data) => {
    const rankings = (data.final_rankings || []).map((r, i) => `${i + 1}. ${r.party_name} — Score: ${r.score}`).join('<br>');
    if (UI.getMyPartyId()) {
        UI.showGameOver('GAME OVER', 'The trail has claimed its toll.', `<p>Final Rankings:</p><p>${rankings}</p>`);
    }
});

Network.on('onError', (data) => {
    UI.setJoinError(data.message);
    console.error('[Main] Error:', data.message);
});

// ------------------------------------------------------------------
// Event Listeners
// ------------------------------------------------------------------
document.getElementById('btn-join').addEventListener('click', () => {
    const name = UI.els.joinName.value.trim();
    if (!name) {
        UI.setJoinError('Please enter your name.');
        return;
    }
    UI.setJoinError('');
    Network.emit('join_session', { name });
});

UI.els.joinName.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') document.getElementById('btn-join').click();
});

window.addEventListener('vote-submitted', (e) => {
    const { decision_id, choice } = e.detail;
    Network.emit('submit_vote', { decision_id, choice });
});

window.addEventListener('captain-override', (e) => {
    const { decision_id, choice } = e.detail;
    Network.emit('captain_override', { decision_id, choice });
});

window.addEventListener('choose-profession', (e) => {
    const { party_id, profession } = e.detail;
    Network.emit('choose_profession', { party_id, profession });
});

window.addEventListener('set-party-name', (e) => {
    const { party_id, name } = e.detail;
    Network.emit('set_party_name_player', { party_id, name });
});

window.addEventListener('buy-supplies', (e) => {
    const { party_id, item, quantity } = e.detail;
    Network.emit('buy_supplies', { party_id, item, quantity });
});

window.addEventListener('party-ready', (e) => {
    const { party_id } = e.detail;
    Network.emit('party_ready', { party_id });
});

window.addEventListener('submit-epitaph', (e) => {
    const { party_id, tombstone_index, epitaph } = e.detail;
    Network.emit('submit_epitaph', { party_id, tombstone_index, epitaph });
});

// Captain's Call vote buttons
document.getElementById('btn-call-pace')?.addEventListener('click', () => {
    const partyId = UI.getMyPartyId();
    if (partyId) Network.emit('call_vote', { party_id: partyId, vote_type: 'pace' });
});
document.getElementById('btn-call-hunt')?.addEventListener('click', () => {
    const partyId = UI.getMyPartyId();
    if (partyId) Network.emit('call_vote', { party_id: partyId, vote_type: 'hunt' });
});
document.getElementById('btn-call-rest')?.addEventListener('click', () => {
    const partyId = UI.getMyPartyId();
    if (partyId) Network.emit('call_vote', { party_id: partyId, vote_type: 'rest' });
});

// ------------------------------------------------------------------
// State Handling
// ------------------------------------------------------------------
function handleStateUpdate(state) {
    if (!state || !state.players) return;
    lastState = state;

    myPlayerId = Network.getPlayerId();
    const me = state.players[myPlayerId];
    if (!me) return;

    // Determine which screen to show
    const gameStatus = state.game_status;

    if (gameStatus === 'lobby') {
        UI.showScreen('lobby');
        UI.updateLobby(state, myPlayerId);
    } else if (gameStatus === 'outfitting') {
        UI.showScreen('outfitting');
        UI.renderOutfittingScreen(state, myPlayerId);
    } else if (gameStatus === 'active' || gameStatus === 'paused') {
        if (UI.getMyPartyId() && !me.party_id) {
            // We got removed or haven't been assigned — stay in lobby
            UI.showScreen('lobby');
            UI.updateLobby(state, myPlayerId);
        } else {
            const party = me.party_id ? state.parties[me.party_id] : null;
            if (party && party.status === 'hunting') {
                UI.showScreen('hunting');
                Hunting.start(state, myPlayerId);
            } else {
                UI.showScreen('game');
                UI.updateGame(state, myPlayerId);
            }
        }
    } else if (gameStatus === 'ended') {
        UI.showScreen('gameover');
    }

    myPartyId = me.party_id;
}
