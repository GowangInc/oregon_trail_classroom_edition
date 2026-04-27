/**
 * Player UI — screen management, DOM rendering, decision handling.
 */

const screens = {
    join: document.getElementById('screen-join'),
    lobby: document.getElementById('screen-lobby'),
    game: document.getElementById('screen-game'),
    gameover: document.getElementById('screen-gameover'),
};

const els = {
    joinName: document.getElementById('player-name'),
    joinCode: document.getElementById('session-code'),
    joinError: document.getElementById('join-error'),
    lobbyPartyName: document.getElementById('lobby-party-name'),
    lobbyMembers: document.getElementById('lobby-members'),
    gameLog: document.getElementById('game-log'),
    partyMembers: document.getElementById('party-members'),
    inventoryList: document.getElementById('inventory-list'),
    leaderboard: document.getElementById('leaderboard'),
    decisionPanel: document.getElementById('decision-panel'),
    actionPanel: document.getElementById('action-panel'),
    decisionPrompt: document.getElementById('decision-prompt'),
    decisionTimer: document.getElementById('decision-timer'),
    choices: document.getElementById('choices'),
    statDate: document.getElementById('stat-date'),
    statWeather: document.getElementById('stat-weather'),
    statNext: document.getElementById('stat-next'),
    statMiles: document.getElementById('stat-miles'),
    statFood: document.getElementById('stat-food'),
    statHealth: document.getElementById('stat-health'),
    gameoverTitle: document.getElementById('gameover-title'),
    gameoverMessage: document.getElementById('gameover-message'),
    gameoverStats: document.getElementById('gameover-stats'),
};

let currentDecision = null;
let decisionTimerInterval = null;
let myPartyId = null;
let lastState = null;

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

function setJoinError(msg) {
    els.joinError.textContent = msg;
}

function updateLobby(state, myPlayerId) {
    myPartyId = state.parties ? Object.keys(state.parties).find(pid => {
        const p = state.parties[pid];
        return p.member_ids && p.member_ids.includes(myPlayerId);
    }) : null;

    if (myPartyId && state.parties[myPartyId]) {
        const party = state.parties[myPartyId];
        els.lobbyPartyName.textContent = party.party_name;
        els.lobbyMembers.innerHTML = '';
        party.member_ids.forEach(mid => {
            const player = state.players[mid];
            if (player) {
                const li = document.createElement('li');
                li.textContent = player.name + (mid === party.captain_id ? ' (Captain)' : '');
                els.lobbyMembers.appendChild(li);
            }
        });
    } else {
        els.lobbyPartyName.textContent = 'Not assigned yet';
        els.lobbyMembers.innerHTML = '';
    }
}

function updateGame(state, myPlayerId) {
    lastState = state;
    myPartyId = state.parties ? Object.keys(state.parties).find(pid => {
        const p = state.parties[pid];
        return p.member_ids && p.member_ids.includes(myPlayerId);
    }) : null;

    if (!myPartyId || !state.parties[myPartyId]) return;
    const party = state.parties[myPartyId];

    // Status bar
    els.statDate.textContent = state.global_date || '---';
    els.statWeather.textContent = state.global_weather || '---';
    els.statMiles.textContent = party.distance_traveled || 0;
    els.statFood.textContent = party.inventory ? party.inventory.food : 0;

    // Next landmark
    const landmarks = [
        "Independence, Missouri", "Kansas River Crossing", "Big Blue River Crossing",
        "Fort Kearney", "Chimney Rock", "Fort Laramie", "Independence Rock",
        "South Pass", "Fort Bridger", "Green River Crossing", "Soda Springs",
        "Fort Hall", "Snake River Crossing", "Fort Boise", "Blue Mountains",
        "Fort Walla Walla", "The Dalles", "Willamette Valley, Oregon"
    ];
    const nextIdx = (party.current_landmark_index || 0) + 1;
    els.statNext.textContent = landmarks[nextIdx] || 'Oregon City';

    // Health (worst living member)
    let worstHealth = 'Healthy';
    const healthOrder = ['Healthy', 'Fair', 'Poor', 'Very Poor', 'Dead'];
    party.member_ids.forEach(mid => {
        const p = state.players[mid];
        if (p && p.is_alive) {
            const idx = healthOrder.indexOf(p.health_status);
            const worstIdx = healthOrder.indexOf(worstHealth);
            if (idx > worstIdx) worstHealth = p.health_status;
        }
    });
    els.statHealth.textContent = worstHealth;

    // Party members
    els.partyMembers.innerHTML = '';
    party.member_ids.forEach(mid => {
        const player = state.players[mid];
        if (!player) return;
        const li = document.createElement('li');
        li.className = player.is_alive ? '' : 'dead-badge';
        li.textContent = player.name;
        if (mid === party.captain_id) {
            const badge = document.createElement('span');
            badge.className = 'captain-badge';
            badge.textContent = 'CAPTAIN';
            li.appendChild(badge);
        }
        if (!player.is_alive) {
            li.textContent += ' (DECEASED)';
        }
        els.partyMembers.appendChild(li);
    });

    // Inventory
    els.inventoryList.innerHTML = '';
    if (party.inventory) {
        const items = [
            `Oxen: ${party.inventory.oxen}`,
            `Food: ${party.inventory.food} lbs`,
            `Clothing: ${party.inventory.clothing}`,
            `Bullets: ${party.inventory.bullets}`,
            `Wheels: ${party.inventory.wagon_wheels}`,
            `Axles: ${party.inventory.wagon_axles}`,
            `Tongues: ${party.inventory.wagon_tongues}`,
            `Money: $${Math.round(party.inventory.money * 100) / 100}`,
        ];
        items.forEach(text => {
            const li = document.createElement('li');
            li.textContent = text;
            els.inventoryList.appendChild(li);
        });
    }

    // Leaderboard
    els.leaderboard.innerHTML = '';
    const partyList = Object.values(state.parties || {}).sort((a, b) => (b.distance_traveled || 0) - (a.distance_traveled || 0));
    partyList.forEach(p => {
        const li = document.createElement('li');
        const alive = p.member_ids.filter(mid => {
            const pl = state.players[mid];
            return pl && pl.is_alive;
        }).length;
        const total = p.member_ids.length;
        li.innerHTML = `
            <div style="display: flex; justify-content: space-between;">
                <span>${p.party_name}</span>
                <span>${p.distance_traveled || 0} mi</span>
            </div>
            <div style="font-size: 0.85rem; opacity: 0.8;">${alive}/${total} alive · ${p.status}</div>
            <div class="progress-bar"><div class="progress-fill" style="width: ${Math.min(100, (p.distance_traveled / 2094) * 100)}%"></div></div>
        `;
        els.leaderboard.appendChild(li);
    });

    // Decision panel
    if (party.decision_pending && !party.decision_pending.resolved) {
        showDecision(party.decision_pending, myPlayerId, party.captain_id);
    } else {
        hideDecision();
    }
}

function showDecision(decision, myPlayerId, captainId) {
    if (currentDecision && currentDecision.decision_id === decision.decision_id) {
        // Just update timer and votes
        updateDecisionVotes(decision, myPlayerId);
        return;
    }

    currentDecision = decision;
    els.decisionPanel.hidden = false;
    els.actionPanel.hidden = true;
    els.decisionPrompt.textContent = decision.prompt || 'WHAT IS YOUR CHOICE?';
    els.choices.innerHTML = '';

    const isDead = !lastState.players[myPlayerId]?.is_alive;

    decision.options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'choice-btn';
        btn.textContent = opt;
        btn.disabled = isDead;
        if (decision.votes && decision.votes[myPlayerId] === opt) {
            btn.classList.add('voted');
        }
        btn.onclick = () => {
            window.dispatchEvent(new CustomEvent('vote-submitted', {
                detail: { decision_id: decision.decision_id, choice: opt }
            }));
            btn.classList.add('voted');
        };
        els.choices.appendChild(btn);
    });

    // Captain override dropdown
    if (myPlayerId === captainId && !isDead) {
        const overrideLabel = document.createElement('div');
        overrideLabel.style.cssText = 'width: 100%; font-size: 0.9rem; margin-top: 0.3rem; opacity: 0.8;';
        overrideLabel.textContent = 'CAPTAIN DEFAULT: ';
        const sel = document.createElement('select');
        sel.className = 'terminal-input';
        sel.style.cssText = 'width: auto; display: inline-block; margin-left: 0.3rem;';
        decision.options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt;
            option.textContent = opt;
            if (decision.captain_default === opt) option.selected = true;
            sel.appendChild(option);
        });
        sel.onchange = () => {
            window.dispatchEvent(new CustomEvent('captain-override', {
                detail: { decision_id: decision.decision_id, choice: sel.value }
            }));
        };
        overrideLabel.appendChild(sel);
        els.choices.appendChild(overrideLabel);
    }

    startDecisionTimer(decision);
    updateDecisionVotes(decision, myPlayerId);
}

function updateDecisionVotes(decision, myPlayerId) {
    const counts = {};
    Object.values(decision.votes || {}).forEach(v => {
        counts[v] = (counts[v] || 0) + 1;
    });

    const buttons = els.choices.querySelectorAll('.choice-btn');
    buttons.forEach(btn => {
        const count = counts[btn.textContent] || 0;
        if (count > 0) {
            btn.textContent = `${btn.textContent.split(' (')[0]} (${count})`;
        }
    });
}

function startDecisionTimer(decision) {
    if (decisionTimerInterval) clearInterval(decisionTimerInterval);

    const timeout = decision.timeout_seconds || 10;
    const created = new Date(decision.created_at);
    const endTime = new Date(created.getTime() + timeout * 1000);

    function update() {
        const now = new Date();
        const remaining = Math.max(0, Math.ceil((endTime - now) / 1000));
        els.decisionTimer.textContent = `Time remaining: ${remaining}s`;
        if (remaining <= 0) {
            clearInterval(decisionTimerInterval);
            hideDecision();
        }
    }

    update();
    decisionTimerInterval = setInterval(update, 1000);
}

function hideDecision() {
    currentDecision = null;
    if (decisionTimerInterval) {
        clearInterval(decisionTimerInterval);
        decisionTimerInterval = null;
    }
    els.decisionPanel.hidden = true;
    els.actionPanel.hidden = false;
}

function addEventToLog(event) {
    const p = document.createElement('p');
    p.className = 'narrative';

    if (event.type === 'death') {
        p.classList.add('death');
        p.textContent = `☠ ${event.message}`;
    } else if (event.type === 'landmark' || event.type === 'finished') {
        p.classList.add('landmark');
        p.textContent = `▶ ${event.message}`;
    } else if (event.type === 'trail_event' || event.type === 'illness') {
        p.classList.add('event');
        p.textContent = `! ${event.message}`;
    } else {
        p.textContent = event.message || JSON.stringify(event);
    }

    els.gameLog.appendChild(p);
    els.gameLog.scrollTop = els.gameLog.scrollHeight;

    // Limit log size
    while (els.gameLog.children.length > 200) {
        els.gameLog.removeChild(els.gameLog.firstChild);
    }
}

function showGameOver(title, message, statsHtml) {
    els.gameoverTitle.textContent = title;
    els.gameoverMessage.textContent = message;
    els.gameoverStats.innerHTML = statsHtml || '';
    showScreen('gameover');
}

function getMyPartyId() {
    return myPartyId;
}

export {
    showScreen,
    setJoinError,
    updateLobby,
    updateGame,
    addEventToLog,
    showGameOver,
    getMyPartyId,
    els,
};
