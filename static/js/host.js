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
    connStatus: document.getElementById('conn-status'),
    sessionCode: document.getElementById('host-session-code'),
    serverUrl: document.getElementById('host-server-url'),
    unassignedList: document.getElementById('host-unassigned'),
    partiesContainer: document.getElementById('host-parties'),
    dashSessionCode: document.getElementById('dash-session-code'),
    dashServerUrl: document.getElementById('dash-server-url'),
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
// Auto-reconnect if we have a previous host session stored
const storedPlayerId = sessionStorage.getItem('player_id');
const storedIsHost = sessionStorage.getItem('is_host') === '1';
if (storedPlayerId && storedIsHost) {
    els.setupInfo.textContent = 'Reconnecting to previous session...';
    Network.init(true);
}

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
    // If we were trying to auto-reconnect, clear the message and show login
    if (els.connStatus && els.connStatus.textContent.includes('Reconnecting')) {
        els.connStatus.textContent = 'Reconnect failed. Please log in again.';
        sessionStorage.removeItem('player_id');
        sessionStorage.removeItem('is_host');
    } else {
        alert('Error: ' + data.message);
    }
});

Network.on('onDisconnect', () => {
    if (els.connStatus) {
        els.connStatus.textContent = 'Disconnected. Refresh to reconnect.';
        els.connStatus.style.color = 'var(--term-danger)';
    }
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

document.getElementById('btn-start-outfitting').addEventListener('click', () => {
    Network.emit('start_game');
});

document.getElementById('btn-begin-journey').addEventListener('click', () => {
    Network.emit('begin_journey');
});

document.getElementById('btn-quick-start').addEventListener('click', () => {
    Network.emit('quick_start');
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

document.getElementById('btn-new-session').addEventListener('click', () => {
    if (confirm('Start a brand new session? All current progress will be lost.')) {
        Network.emit('new_session');
        showScreen('setup');
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

    // Update server URL displays
    const serverUrl = state.server_url || '';
    if (els.serverUrl) els.serverUrl.textContent = serverUrl || '---';
    if (els.dashServerUrl) els.dashServerUrl.textContent = serverUrl || '---';

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

    // Render lobby if in lobby
    if (state.game_status === 'lobby') {
        showScreen('lobby');
        renderLobby(state);
    }

    // Render lobby (outfitting view) if in outfitting
    if (state.game_status === 'outfitting') {
        showScreen('lobby');
        renderLobby(state);
        renderOutfittingProgress(state);
    }

    // Render dashboard if active/paused/ended
    if (['active', 'paused', 'ended'].includes(state.game_status)) {
        showScreen('dash');
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

    // Update lobby hint and button states
    const unassignedCount = Object.values(state.players || {}).filter(p => !p.is_host && !p.party_id).length;
    const partyCount = Object.keys(state.parties || {}).length;
    const totalMembers = Object.values(state.parties || {}).reduce((sum, p) => sum + p.member_ids.length, 0);
    const startBtn = document.getElementById('btn-start-outfitting');
    const journeyBtn = document.getElementById('btn-begin-journey');
    const quickBtn = document.getElementById('btn-quick-start');
    const hint = document.getElementById('lobby-hint');
    const isOutfitting = state.game_status === 'outfitting';

    if (hint) {
        if (isOutfitting) {
            const readyCount = Object.values(state.parties || {}).filter(p => p.outfitting_complete).length;
            hint.textContent = `Outfitting phase! ${readyCount}/${partyCount} parties ready. Click BEGIN JOURNEY when ready.`;
            hint.style.color = readyCount === partyCount ? 'var(--term-green)' : 'var(--term-warn)';
        } else if (partyCount === 0) {
            hint.textContent = `Step 1: Click + PARTY to create a party. (${unassignedCount} player(s) waiting)`;
            hint.style.color = 'var(--term-warn)';
        } else if (totalMembers === 0) {
            hint.textContent = `Step 2: Drag players from Unassigned into a party.`;
            hint.style.color = 'var(--term-warn)';
        } else {
            hint.textContent = `Ready! ${totalMembers} player(s) in ${partyCount} party(s). Click START OUTFITTING or QUICK START.`;
            hint.style.color = 'var(--term-green)';
        }
    }

    if (startBtn) {
        startBtn.hidden = isOutfitting;
        startBtn.disabled = partyCount === 0 || totalMembers === 0;
        startBtn.style.opacity = startBtn.disabled ? '0.5' : '1';
    }
    if (journeyBtn) {
        journeyBtn.hidden = !isOutfitting;
        const readyCount = Object.values(state.parties || {}).filter(p => p.outfitting_complete).length;
        journeyBtn.disabled = readyCount === 0;
        journeyBtn.style.opacity = journeyBtn.disabled ? '0.5' : '1';
    }
}

function renderOutfittingProgress(state) {
    // Show outfitting status in party cards area
    els.partiesContainer.innerHTML = '';
    Object.values(state.parties || {}).forEach(party => {
        const div = document.createElement('div');
        div.className = 'lobby-panel';
        div.style.marginBottom = '0.5rem';
        const inv = party.inventory || {};
        const prof = party.profession || 'Not chosen';
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between;">
                <strong>${party.party_name}</strong>
                <span style="color: ${party.outfitting_complete ? 'var(--term-green)' : 'var(--term-warn)'};">${party.outfitting_complete ? 'READY' : 'OUTFITTING'}</span>
            </div>
            <div style="font-size: 0.85rem;">
                Profession: ${prof} · Money: $${Math.round(inv.money * 100) / 100}
                · Oxen: ${inv.oxen || 0} · Food: ${inv.food || 0} lbs
                · Clothing: ${inv.clothing || 0} · Bullets: ${inv.bullets || 0}
                · Wheels: ${inv.wagon_wheels || 0} · Axles: ${inv.wagon_axles || 0} · Tongues: ${inv.wagon_tongues || 0}
            </div>
        `;
        els.partiesContainer.appendChild(div);
    });
}

function renderTombstones(state) {
    const container = document.getElementById('host-tombstones');
    if (!container) return;
    container.innerHTML = '';
    const tombstones = state.all_tombstones || [];
    if (tombstones.length === 0) {
        container.textContent = 'No tombstones yet.';
        return;
    }
    tombstones.forEach((ts, idx) => {
        const div = document.createElement('div');
        div.style.cssText = 'margin-bottom: 0.5rem; border-bottom: 1px solid rgba(102,204,255,0.2); padding-bottom: 0.3rem;';
        div.innerHTML = `
            <div><strong>${ts.player_name}</strong> — ${ts.cause} @ mile ${ts.mile_marker}</div>
            <div style="font-style: italic; opacity: 0.9;">"${ts.epitaph}"</div>
            <button class="terminal-btn" style="min-width: auto; font-size: 0.75rem; padding: 0.2rem 0.4rem; margin-top: 0.2rem;"
                onclick="window.__hostEditTombstone(${idx}, '${(ts.epitaph || '').replace(/'/g, "\\'")}')">EDIT</button>
        `;
        container.appendChild(div);
    });
}

function renderDashboard(state) {
    // Update party selector options
    const partyIds = Object.keys(state.parties || {});
    updateSelectOptions(els.selPartyInject, partyIds, state.parties);
    updateSelectOptions(els.selPartyEdit, partyIds, state.parties);

    // Tombstones
    renderTombstones(state);

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
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    // Color-code different event types
    let color = 'var(--term-green)';
    let isTombstone = false;
    if (msg.includes('tombstone') || msg.includes('Tombstone')) {
        color = '#aa88ff';
        isTombstone = true;
    } else if (msg.includes('died') || msg.includes('dead') || msg.includes('perished') || msg.includes('DECEASED')) {
        color = 'var(--term-danger)';
    } else if (msg.includes('reached') || msg.includes('Oregon') || msg.includes('finished') || msg.includes('landmark')) {
        color = 'var(--term-info)';
    } else if (msg.includes('hunt') || msg.includes('Hunt')) {
        color = '#ffaa00';
    } else if (msg.includes('decision') || msg.includes('vote') || msg.includes('Vote')) {
        color = '#cc88ff';
    } else if (msg.includes('rest') || msg.includes('Rest')) {
        color = '#88ccff';
    } else if (msg.includes('event') || msg.includes('Event') || msg.includes('injured') || msg.includes('broken')) {
        color = '#ff6666';
    }

    p.style.cssText = 'margin-bottom: 0.3rem; border-bottom: 1px solid rgba(102,204,255,0.15); padding-bottom: 0.3rem; font-size: 0.9rem; line-height: 1.3;';
    if (isTombstone) {
        p.classList.add('host-log-tombstone');
    }

    p.innerHTML = `<span style="opacity: 0.6; font-size: 0.8rem;">[${time}]</span> <span style="color: ${color};">${msg}</span>`;
    els.hostLog.appendChild(p);
    els.hostLog.scrollTop = els.hostLog.scrollHeight;
    while (els.hostLog.children.length > 500) {
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

window.__hostEditTombstone = (idx, currentEpitaph) => {
    const newEpitaph = prompt('Edit epitaph:', currentEpitaph);
    if (newEpitaph !== null) {
        Network.emit('host_edit_tombstone', { tombstone_index: idx, epitaph: newEpitaph });
    }
};
