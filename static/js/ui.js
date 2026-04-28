/**
 * Player UI — screen management, DOM rendering, decision handling.
 */

const screens = {
    join: document.getElementById('screen-join'),
    lobby: document.getElementById('screen-lobby'),
    outfitting: document.getElementById('screen-outfitting'),
    game: document.getElementById('screen-game'),
    gameover: document.getElementById('screen-gameover'),
};

const els = {
    joinName: document.getElementById('player-name'),
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

// Outfitting UI state
let outfittingState = {
    profession: null,
    money: 0,
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
        if (player.is_npc) {
            li.textContent += ' (NPC)';
        }
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

    // Captain's Call panel
    const captainPanel = document.getElementById('captain-panel');
    if (captainPanel) {
        const isCaptain = myPlayerId === party.captain_id;
        const me = state.players[myPlayerId];
        captainPanel.hidden = !isCaptain || !me || !me.is_alive;
    }

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
    els.decisionPrompt.textContent = decision.prompt || 'DECISION:';
    els.choices.innerHTML = '';

    const isDead = !lastState.players[myPlayerId]?.is_alive;

    // Display options as a numbered list
    const ul = document.createElement('ul');
    ul.style.listStyleType = 'none';
    ul.style.padding = '0';
    ul.style.margin = '0 0 1rem 0';
    
    decision.options.forEach((opt, idx) => {
        const li = document.createElement('li');
        li.textContent = `${idx + 1}. ${opt}`;
        li.style.marginBottom = '0.5rem';
        if (decision.votes && decision.votes[myPlayerId] === opt) {
            li.style.color = 'var(--term-highlight)';
        }
        ul.appendChild(li);
    });
    els.choices.appendChild(ul);
    
    // Add input field for typing choice
    const inputWrapper = document.createElement('div');
    inputWrapper.style.display = 'flex';
    inputWrapper.style.alignItems = 'center';
    inputWrapper.style.gap = '0.5rem';
    
    const label = document.createElement('span');
    label.textContent = "What is your choice?";
    
    const input = document.createElement('input');
    input.type = 'number';
    input.min = 1;
    input.max = decision.options.length;
    input.className = 'terminal-input';
    input.style.width = '4rem';
    input.disabled = isDead || (decision.votes && decision.votes[myPlayerId]);
    
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const val = parseInt(input.value, 10);
            if (val >= 1 && val <= decision.options.length) {
                const opt = decision.options[val - 1];
                window.dispatchEvent(new CustomEvent('vote-submitted', {
                    detail: { decision_id: decision.decision_id, choice: opt }
                }));
                input.disabled = true;
            }
        }
    });
    
    inputWrapper.appendChild(label);
    inputWrapper.appendChild(input);
    els.choices.appendChild(inputWrapper);

    // Captain override dropdown
    if (myPlayerId === captainId && !isDead) {
        const overrideLabel = document.createElement('div');
        overrideLabel.style.cssText = 'width: 100%; font-size: 0.9rem; margin-top: 1rem; opacity: 0.8;';
        overrideLabel.textContent = 'CAPTAIN DEFAULT: ';
        const sel = document.createElement('select');
        sel.className = 'terminal-input';
        sel.style.cssText = 'width: auto; display: inline-block; margin-left: 0.3rem;';
        decision.options.forEach((opt, idx) => {
            const option = document.createElement('option');
            option.value = opt;
            option.textContent = `${idx + 1}. ${opt}`;
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
    
    if (!input.disabled) {
        setTimeout(() => input.focus(), 0);
    }
}

function updateDecisionVotes(decision, myPlayerId) {
    const counts = {};
    Object.values(decision.votes || {}).forEach(v => {
        counts[v] = (counts[v] || 0) + 1;
    });

    const items = els.choices.querySelectorAll('li');
    items.forEach((li, idx) => {
        const opt = decision.options[idx];
        const count = counts[opt] || 0;
        li.textContent = `${idx + 1}. ${opt}${count > 0 ? ` (${count} votes)` : ''}`;
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

// ------------------------------------------------------------------
// Outfitting Screen
// ------------------------------------------------------------------
function renderOutfittingScreen(state, myPlayerId) {
    const party = Object.values(state.parties || {}).find(p => p.member_ids && p.member_ids.includes(myPlayerId));
    if (!party) return;

    const isCaptain = party.captain_id === myPlayerId;
    const professionEl = document.getElementById('profession-selected');
    const storeItemsEl = document.getElementById('store-items');
    const moneyEl = document.getElementById('store-money');
    const readyBtn = document.getElementById('btn-outfit-ready');
    const statusEl = document.getElementById('outfit-status');

    // Party name input
    const nameInput = document.getElementById('outfit-party-name');
    if (nameInput) {
        nameInput.value = party.party_name || '';
        nameInput.disabled = !isCaptain || party.outfitting_complete;
        nameInput.onchange = () => {
            if (!isCaptain) return;
            window.dispatchEvent(new CustomEvent('set-party-name', {
                detail: { party_id: party.party_id, name: nameInput.value.trim() }
            }));
        };
    }

    // Profession display
    const profMap = {
        'Banker from Boston': 'Banker ($1,600)',
        'Carpenter from Ohio': 'Carpenter ($800)',
        'Farmer from Illinois': 'Farmer ($400)',
    };
    const hasProf = party.inventory && party.inventory.money > 0;
    const profName = hasProf ? (party.profession || 'Unknown') : 'Not selected';
    professionEl.textContent = profMap[profName] || profName;

    // Money display
    const money = party.inventory ? party.inventory.money : 0;
    moneyEl.textContent = `$${Math.round(money * 100) / 100}`;

    // Store items
    const prices = {
        oxen: 40,
        food: 0.10,
        clothing: 10,
        bullets: 2,
        wagon_wheel: 10,
        wagon_axle: 10,
        wagon_tongue: 10,
    };
    const labels = {
        oxen: 'Oxen (yoke)',
        food: 'Food (lbs)',
        clothing: 'Clothing (sets)',
        bullets: 'Bullets (boxes of 20)',
        wagon_wheel: 'Wagon Wheels',
        wagon_axle: 'Wagon Axles',
        wagon_tongue: 'Wagon Tongues',
    };

    if (storeItemsEl && storeItemsEl.children.length === 0) {
        Object.entries(prices).forEach(([item, price]) => {
            const row = document.createElement('div');
            row.style.cssText = 'display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;';
            row.innerHTML = `
                <span style="flex: 1;">${labels[item]} — $${price} each</span>
                <input type="number" class="terminal-input store-qty" data-item="${item}" value="0" min="0" style="width: 60px; text-align: center;" ${isCaptain ? '' : 'disabled'}>
                <button class="terminal-btn store-buy" data-item="${item}" data-price="${price}" style="min-width: auto; font-size: 0.85rem; padding: 0.2rem 0.5rem;" ${isCaptain ? '' : 'disabled'}>BUY</button>
            `;
            storeItemsEl.appendChild(row);
        });

        // Wire up buy buttons (once)
        storeItemsEl.querySelectorAll('.store-buy').forEach(btn => {
            btn.addEventListener('click', () => {
                const item = btn.dataset.item;
                const qtyInput = storeItemsEl.querySelector(`.store-qty[data-item="${item}"]`);
                const qty = parseInt(qtyInput.value, 10) || 0;
                if (qty > 0) {
                    window.dispatchEvent(new CustomEvent('buy-supplies', {
                        detail: { party_id: party.party_id, item, quantity: qty }
                    }));
                    qtyInput.value = '0';
                }
            });
        });
    }

    // Profession selection (enabled until money is set)
    const hasProfession = party.inventory && party.inventory.money > 0;
    const profInput = document.getElementById('profession-input');
    if (profInput) {
        profInput.disabled = !isCaptain || hasProfession;
        // Only add listener if not already added to avoid duplicates
        if (!profInput.dataset.wired) {
            profInput.dataset.wired = "true";
            profInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    if (!isCaptain || hasProfession) return;
                    const val = parseInt(profInput.value, 10);
                    const profs = ["Banker from Boston", "Carpenter from Ohio", "Farmer from Illinois"];
                    if (val >= 1 && val <= 3) {
                        window.dispatchEvent(new CustomEvent('choose-profession', {
                            detail: { party_id: party.party_id, profession: profs[val - 1] }
                        }));
                    }
                }
            });
        }
    }

    // Ready button
    if (readyBtn) {
        readyBtn.disabled = !isCaptain || !hasProfession || party.outfitting_complete;
        readyBtn.onclick = () => {
            window.dispatchEvent(new CustomEvent('party-ready', {
                detail: { party_id: party.party_id }
            }));
        };
    }

    if (statusEl) {
        if (!isCaptain) {
            statusEl.textContent = 'Waiting for the captain to finish outfitting...';
        } else if (party.outfitting_complete) {
            statusEl.textContent = 'Your party is ready to depart!';
        } else {
            statusEl.textContent = 'Choose a profession and buy supplies, then click READY.';
        }
    }
}

// ------------------------------------------------------------------
// Epitaph Editor
// ------------------------------------------------------------------
function showEpitaphEditor(playerName, partyId, tombstoneIndex) {
    // Remove any existing epitaph editor first
    const existing = document.getElementById('epitaph-editor');
    if (existing) existing.remove();

    const panel = document.createElement('div');
    panel.id = 'epitaph-editor';
    panel.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.9); display: flex; align-items: center; justify-content: center; z-index: 10001;';
    panel.innerHTML = `
        <div style="border: 2px solid var(--term-green); background: #000; padding: 1.5rem; max-width: 420px; width: 90%; box-shadow: 0 0 20px rgba(74,246,38,0.3);">
            <h2 style="margin-top: 0; color: var(--term-green);">☗ Write an Epitaph</h2>
            <p style="margin-bottom: 0.5rem;"><strong>${playerName}</strong> has died. What should the tombstone say?</p>
            <textarea class="terminal-input epitaph-text" rows="3" style="width: 100%; margin-bottom: 1rem; resize: none;" placeholder="Here lies..." maxlength="200"></textarea>
            <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button class="terminal-btn epitaph-cancel" style="min-width: auto;">Skip</button>
                <button class="terminal-btn epitaph-submit" style="min-width: auto; color: var(--term-green); border-color: var(--term-green);">Write Epitaph</button>
            </div>
        </div>
    `;
    document.body.appendChild(panel);

    const textarea = panel.querySelector('.epitaph-text');
    const cancelBtn = panel.querySelector('.epitaph-cancel');
    const submitBtn = panel.querySelector('.epitaph-submit');

    cancelBtn.onclick = () => panel.remove();
    submitBtn.onclick = () => {
        const text = textarea.value.trim();
        if (text) {
            window.dispatchEvent(new CustomEvent('submit-epitaph', {
                detail: { party_id: partyId, tombstone_index: tombstoneIndex, epitaph: text }
            }));
        }
        panel.remove();
    };

    // Keyboard shortcuts
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitBtn.click();
        }
        if (e.key === 'Escape') {
            cancelBtn.click();
        }
    });

    textarea.focus();
}

export {
    showScreen,
    setJoinError,
    updateLobby,
    updateGame,
    renderOutfittingScreen,
    showEpitaphEditor,
    addEventToLog,
    showGameOver,
    getMyPartyId,
    els,
};
