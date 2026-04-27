/**
 * Host dashboard entry point — full game control and monitoring.
 */

import * as Network from './network.js';

let sessionId = null;
let sessionCode = null;
let lastState = null;

// DOM refs
const screens = {
    setup: document.getElementById('screen-host-setup'),
    lobby: document.getElementById('screen-host-lobby'),
    dash: document.getElementById('screen-host-dash'),
};

const els = {
    setupInfo: document.getElementById('setup-info'),
    sessionCode: document.getElementById('host-session-code'),
    unassignedList: document.getElementById('host-unassigned'),
    partiesContainer: document.getElementById('host-parties'),
    dashSessionCode: document.getElementById('dash-session-code'),
    dashDate: document.getElementById('dash-date'),
    dashWeather: document.getElementById('dash-weather'),
    dashStatus: document.getElementById('dash-status'),
    dashTick: document.getElementById('dash-tick'),
    partyCards: document.getElementById('party-cards'),
    selPartyInject: document.getElementById('sel-party-inject'),
    eventButtons: document.getElementById('event-buttons'),
    selPartyEdit: document.getElementById('sel-party-edit'),
    editFields: document.getElementById('edit-fields'),
    hostLog: document.getElementById('host-log'),
    chkAuto: document.getElementById('chk-auto'),
    rngInterval: document.getElementById('rng-interval'),
    lblInterval: document.getElementById('lbl-interval'),
};

// ------------------------------------------------------------------
// Init
// ------------------------------------------------------------------
// Removed immediate init; waiting for explicit connection

Network.on('onConnect', () => {
    console.log('[Host] Connected');
});

Network.on('onSessionState', (state) => {
    lastState = state;
    handleStateUpdate(state);
});

Network.on('onEventOccurred', (event) => {
    addHostLog(event.message || JSON.stringify(event));
});

Network.on('onGamePaused', () => {
    addHostLog('Game paused');
    updateControlUI();
});

Network.on('onGameResumed', () => {
    addHostLog('Game resumed');
    updateControlUI();
});

Network.on('onHostInjectedEvent', (data) => {
    addHostLog(`Injected event on ${data.party_id}: ${data.event_description}`);
});

Network.on('onError', (data) => {
    console.error('[Host] Error:', data.message);
    alert('Error: ' + data.message);
});

// ------------------------------------------------------------------
// Setup Screen
// ------------------------------------------------------------------
document.getElementById('btn-create-session').addEventListener('click', () => {
    const pwd = document.getElementById('host-password').value;
    if (!pwd) {
        alert('Please enter host password');
        return;
    }
    // Init network and attempt to connect
    Network.init(true, pwd);
    // Upon successful connection, server sends `session_state`, and handleStateUpdate renders correctly.
});

// ------------------------------------------------------------------
// Lobby Screen
// ------------------------------------------------------------------
document.getElementById('btn-add-party').addEventListener('click', () => {
    const name = prompt('Party name:', `Wagon Party ${Object.keys(lastState?.parties || {}).length + 1}`);
    if (name) {
        Network.emit('create_party', { party_name: name });
    }
});

document.getElementById('btn-shuffle').addEventListener('click', () => {
    Network.emit('shuffle_parties');
});

document.getElementById('btn-start-game').addEventListener('click', () => {
    Network.emit('start_game');
    showScreen('dash');
});

// ------------------------------------------------------------------
// Dashboard Controls
// ------------------------------------------------------------------
document.getElementById('btn-pause').addEventListener('click', () => {
    Network.emit('pause_game');
});

document.getElementById('btn-resume').addEventListener('click', () => {
    Network.emit('resume_game');
});

document.getElementById('btn-save').addEventListener('click', () => {
    Network.emit('save_state');
});

document.getElementById('btn-load').addEventListener('click', () => {
    if (confirm('Load state from disk? (This replaces the current session)')) {
        Network.emit('load_state');
    }
});

document.getElementById('btn-advance-1').addEventListener('click', () => {
    Network.emit('advance_day');
});

document.getElementById('btn-advance-7').addEventListener('click', () => {
    Network.emit('advance_days', { count: 7 });
});

document.getElementById('btn-end-game').addEventListener('click', () => {
    if (confirm('End the game for all players?')) {
        Network.emit('end_game');
    }
});

els.chkAuto.addEventListener('change', () => {
    const enabled = els.chkAuto.checked;
    const interval = parseInt(els.rngInterval.value, 10);
    Network.emit('set_auto_advance', { enabled, interval_seconds: interval });
});

els.rngInterval.addEventListener('input', () => {
    els.lblInterval.textContent = els.rngInterval.value + 's';
});

els.rngInterval.addEventListener('change', () => {
    if (els.chkAuto.checked) {
        Network.emit('set_auto_advance', {
            enabled: true,
            interval_seconds: parseInt(els.rngInterval.value, 10),
        });
    }
});

// ------------------------------------------------------------------
// Event Injection
// ------------------------------------------------------------------
const EVENT_TYPES = [
    { id: 'broken_wheel', label: 'Broken Wheel' },
    { id: 'broken_axle', label: 'Broken Axle' },
    { id: 'broken_tongue', label: 'Broken Tongue' },
    { id: 'oxen_injured', label: 'Oxen Injured' },
    { id: 'oxen_died', label: 'Oxen Died' },
    { id: 'thief', label: 'Thief!' },
    { id: 'bad_water', label: 'Bad Water' },
    { id: 'lost_trail', label: 'Lost Trail' },
    { id: 'find_wild_fruit', label: 'Find Wild Fruit' },
    { id: 'wrong_path', label: 'Wrong Path' },
    { id: 'rough_trail', label: 'Rough Trail' },
];

function renderEventButtons() {
    els.eventButtons.innerHTML = '';
    EVENT_TYPES.forEach(ev => {
        const btn = document.createElement('button');
        btn.className = 'terminal-btn';
        btn.style.cssText = 'min-width: auto; font-size: 0.85rem; padding: 0.3rem 0.5rem;';
        btn.textContent = ev.label;
        btn.onclick = () => {
            const partyId = els.selPartyInject.value;
            if (!partyId) {
                alert('Select a party first');
                return;
            }
            Network.emit('inject_event', { party_id: partyId, event_id: ev.id });
        };
        els.eventButtons.appendChild(btn);
    });
}
renderEventButtons();

// ------------------------------------------------------------------
// Party Editor
// ------------------------------------------------------------------
const EDITABLE_FIELDS = [
    { key: 'party_name', label: 'Name', type: 'text' },
    { key: 'distance_traveled', label: 'Distance (mi)', type: 'number' },
    { key: 'money', label: 'Money ($)', type: 'number' },
    { key: 'food', label: 'Food (lbs)', type: 'number' },
    { key: 'oxen', label: 'Oxen', type: 'number' },
    { key: 'clothing', label: 'Clothing', type: 'number' },
    { key: 'bullets', label: 'Bullets', type: 'number' },
    { key: 'wagon_wheels', label: 'Wheels', type: 'number' },
    { key: 'wagon_axles', label: 'Axles', type: 'number' },
    { key: 'wagon_tongues', label: 'Tongues', type: 'number' },
    { key: 'pace', label: 'Pace', type: 'select', options: ['Steady', 'Strenuous', 'Grueling'] },
    { key: 'rations', label: 'Rations', type: 'select', options: ['Filling', 'Meager', 'Bare Bones'] },
    { key: 'status', label: 'Status', type: 'select', options: ['traveling', 'resting', 'decision', 'hunting', 'river_crossing', 'finished', 'dead'] },
];

function renderEditFields() {
    els.editFields.innerHTML = '';
    EDITABLE_FIELDS.forEach(field => {
        const row = document.createElement('div');
        row.style.cssText = 'display: flex; gap: 0.3rem; align-items: center;';

        const label = document.createElement('label');
        label.style.cssText = 'font-size: 0.85rem; width: 100px;';
        label.textContent = field.label;
        row.appendChild(label);

        let input;
        if (field.type === 'select') {
            input = document.createElement('select');
            input.className = 'terminal-input';
            input.style.cssText = 'flex: 1; font-size: 0.85rem; padding: 0.2rem;';
            field.options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt;
                input.appendChild(option);
            });
        } else {
            input = document.createElement('input');
            input.type = field.type;
            input.className = 'terminal-input';
            input.style.cssText = 'flex: 1; font-size: 0.85rem; padding: 0.2rem;';
        }
        input.dataset.field = field.key;
        row.appendChild(input);

        const btn = document.createElement('button');
        btn.textContent = 'SET';
        btn.className = 'terminal-btn';
        btn.style.cssText = 'min-width: auto; font-size: 0.75rem; padding: 0.2rem 0.4rem;';
        btn.onclick = () => {
            const partyId = els.selPartyEdit.value;
            if (!partyId) {
                alert('Select a party first');
                return;
            }
            let value = input.value;
            if (field.type === 'number') value = parseFloat(value);
            Network.emit('host_edit_party', { party_id: partyId, field: field.key, value });
        };
        row.appendChild(btn);

        els.editFields.appendChild(row);
    });
}
renderEditFields();

// ------------------------------------------------------------------
// State Handling
// ------------------------------------------------------------------
function handleStateUpdate(state) {
    if (!state) return;

    sessionId = state.session_id;
    sessionCode = state.session_code;

    // Update session code displays
    els.sessionCode.textContent = sessionCode || '---';
    els.dashSessionCode.textContent = sessionCode || '---';

    // Update dashboard stats
    els.dashDate.textContent = state.global_date || '---';
    els.dashWeather.textContent = state.global_weather || '---';
    els.dashStatus.textContent = state.game_status || '---';
    els.dashTick.textContent = state.tick_count || 0;

    // Update auto-advance controls
    els.chkAuto.checked = state.auto_advance_enabled || false;
    if (state.auto_advance_interval) {
        els.rngInterval.value = state.auto_advance_interval;
        els.lblInterval.textContent = state.auto_advance_interval + 's';
    }

    // Render lobby if in lobby/outfitting
    if (state.game_status === 'lobby' || state.game_status === 'outfitting') {
        renderLobby(state);
    }

    // Render dashboard if active/paused/ended
    if (['active', 'paused', 'ended'].includes(state.game_status)) {
        renderDashboard(state);
    }
}

function renderLobby(state) {
    // Unassigned players
    els.unassignedList.innerHTML = '';
    Object.values(state.players || {}).forEach(player => {
        if (player.is_host || player.party_id) return;
        const li = document.createElement('li');
        li.textContent = player.name;
        li.draggable = true;
        li.dataset.playerId = player.player_id;
        els.unassignedList.appendChild(li);
    });

    // Parties
    els.partiesContainer.innerHTML = '';
    Object.values(state.parties || {}).forEach(party => {
        const div = document.createElement('div');
        div.className = 'lobby-panel';
        div.style.marginBottom = '0.5rem';

        const header = document.createElement('div');
        header.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';
        const nameInput = document.createElement('input');
        nameInput.className = 'terminal-input';
        nameInput.style.cssText = 'font-size: 1rem; padding: 0.2rem; width: 200px;';
        nameInput.value = party.party_name;
        nameInput.onchange = () => {
            Network.emit('set_party_name', { party_id: party.party_id, name: nameInput.value });
        };
        header.appendChild(nameInput);

        const dropZone = document.createElement('div');
        dropZone.className = 'member-list';
        dropZone.style.minHeight = '40px';
        dropZone.style.border = '1px dashed var(--term-border)';
        dropZone.style.padding = '0.5rem';
        dropZone.dataset.partyId = party.party_id;
        dropZone.ondragover = (e) => e.preventDefault();
        dropZone.ondrop = (e) => {
            e.preventDefault();
            const pid = e.dataTransfer.getData('text/plain');
            if (pid) Network.emit('assign_party', { player_id: pid, party_id: party.party_id });
        };

        party.member_ids.forEach(mid => {
            const player = state.players[mid];
            if (!player) return;
            const li = document.createElement('div');
            li.style.cssText = 'padding: 0.2rem; cursor: grab;';
            li.textContent = player.name + (mid === party.captain_id ? ' (C)' : '');
            li.draggable = true;
            li.ondragstart = (e) => {
                e.dataTransfer.setData('text/plain', mid);
            };
            dropZone.appendChild(li);
        });

        div.appendChild(header);
        div.appendChild(dropZone);
        els.partiesContainer.appendChild(div);
    });
}

function renderDashboard(state) {
    // Update party selector options
    const partyIds = Object.keys(state.parties || {});
    updateSelectOptions(els.selPartyInject, partyIds, state.parties);
    updateSelectOptions(els.selPartyEdit, partyIds, state.parties);

    // Party cards
    els.partyCards.innerHTML = '';
    Object.values(state.parties || {}).forEach(party => {
        const card = document.createElement('div');
        card.className = 'lobby-panel';
        card.style.marginBottom = '0.5rem';

        const alive = party.member_ids.filter(mid => {
            const p = state.players[mid];
            return p && p.is_alive;
        }).length;

        const healths = party.member_ids.map(mid => state.players[mid]?.health_status || '?').join(', ');

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between;">
                <strong>${party.party_name}</strong>
                <span>${party.status}</span>
            </div>
            <div class="progress-bar" style="margin: 0.3rem 0;">
                <div class="progress-fill" style="width: ${Math.min(100, (party.distance_traveled / 2094) * 100)}%"></div>
            </div>
            <div style="font-size: 0.9rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                <span>${party.distance_traveled} mi</span>
                <span>${alive}/${party.member_ids.length} alive</span>
                <span>Pace: ${party.pace}</span>
                <span>Rations: ${party.rations}</span>
                <span>Food: ${party.inventory?.food || 0}</span>
                <span>Oxen: ${party.inventory?.oxen || 0}</span>
                <span>Health: ${healths}</span>
            </div>
            ${party.decision_pending ? `
                <div style="margin-top: 0.3rem; font-size: 0.85rem; color: var(--term-warn);">
                    Decision: ${party.decision_pending.prompt}
                    <button class="terminal-btn" style="min-width: auto; font-size: 0.8rem; padding: 0.2rem 0.4rem; margin-left: 0.5rem;"
                        onclick="window.__hostForceDecision('${party.party_id}', '${party.decision_pending.options[0]}')">
                        Force: ${party.decision_pending.options[0]}
                    </button>
                </div>
            ` : ''}
        `;
        els.partyCards.appendChild(card);
    });
}

function updateSelectOptions(select, partyIds, parties) {
    const currentVal = select.value;
    select.innerHTML = '<option value="">Select party...</option>';
    partyIds.forEach(pid => {
        const opt = document.createElement('option');
        opt.value = pid;
        opt.textContent = parties[pid]?.party_name || pid;
        select.appendChild(opt);
    });
    if (currentVal && partyIds.includes(currentVal)) {
        select.value = currentVal;
    }
}

function updateControlUI() {
    if (!lastState) return;
    const paused = lastState.game_status === 'paused';
    document.getElementById('btn-pause').disabled = paused;
    document.getElementById('btn-resume').disabled = !paused;
}

function addHostLog(msg) {
    const p = document.createElement('div');
    p.style.cssText = 'margin-bottom: 0.2rem; border-bottom: 1px solid rgba(102,204,255,0.1); padding-bottom: 0.2rem;';
    const time = new Date().toLocaleTimeString();
    p.textContent = `[${time}] ${msg}`;
    els.hostLog.appendChild(p);
    els.hostLog.scrollTop = els.hostLog.scrollHeight;
    while (els.hostLog.children.length > 100) {
        els.hostLog.removeChild(els.hostLog.firstChild);
    }
}

function showScreen(name) {
    Object.values(screens).forEach(s => {
        s.classList.remove('active');
        s.hidden = true;
    });
    if (screens[name]) {
        screens[name].hidden = false;
        screens[name].classList.add('active');
    }
}

// Expose force decision helper globally for inline onclick handlers
window.__hostForceDecision = (partyId, choice) => {
    Network.emit('host_override_decision', { party_id: partyId, choice });
};
