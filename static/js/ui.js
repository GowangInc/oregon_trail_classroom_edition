/**
 * Player UI — screen management, DOM rendering, decision handling.
 */

import * as Effects from './effects.js';

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
    els.statHealth.className = 'highlight ' + Effects.getHealthClass(worstHealth);
    
    // Status Bar Weather Styling
    els.statWeather.className = 'highlight ' + Effects.getWeatherClass(state.global_weather);
    
    // Food Warning
    const food = party.inventory ? party.inventory.food : 0;
    if (food <= 0) {
        els.statFood.className = 'highlight stat-food-critical';
    } else {
        els.statFood.className = 'highlight';
    }

    // Animation Management
    if (party.status === 'traveling' && !party.decision_pending) {
        Effects.startTravelAnimation(party.distance_traveled);
        Effects.startAmbientMessages();
        Effects.startWeatherEffect(state.global_weather);
    } else {
        Effects.stopTravelAnimation();
        Effects.stopAmbientMessages();
        Effects.stopWeatherEffect();
    }

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
    Effects.resetDecisionTimerBar();

    const timeout = decision.timeout_seconds || 10;
    const created = new Date(decision.created_at);
    const endTime = new Date(created.getTime() + timeout * 1000);

    function update() {
        const now = new Date();
        const diffMs = endTime - now;
        const remaining = Math.max(0, Math.ceil(diffMs / 1000));
        els.decisionTimer.textContent = `Time remaining: ${remaining}s`;
        
        Effects.updateDecisionTimerBar(Math.max(0, diffMs / 1000), timeout);

        if (remaining <= 0) {
            clearInterval(decisionTimerInterval);
            hideDecision();
        }
    }

    update();
    decisionTimerInterval = setInterval(update, 100); // Higher frequency for smooth bar
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
function renderOutfittingScreen(state, myPlayerId, isFortVisit = false) {
    const party = Object.values(state.parties || {}).find(p => p.member_ids && p.member_ids.includes(myPlayerId));
    if (!party) return;

    const isCaptain = party.captain_id === myPlayerId;
    
    const partyNameInput = document.getElementById('outfit-party-name');
    if (partyNameInput) {
        if (!partyNameInput.dataset.wired) {
            partyNameInput.dataset.wired = "true";
            partyNameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    if (!isCaptain) return;
                    const name = partyNameInput.value.trim();
                    if (name) {
                        window.dispatchEvent(new CustomEvent('set-party-name', {
                            detail: { party_id: party.party_id, name: name }
                        }));
                        partyNameInput.blur();
                    }
                }
            });
        }
        partyNameInput.disabled = !isCaptain;
        if (party.party_name !== partyNameInput.value && document.activeElement !== partyNameInput) {
            partyNameInput.value = party.party_name || "";
        }
    }

    const professionEl = document.getElementById('profession-selected');
    const professionSelector = document.getElementById('profession-selector');
    if (professionSelector) {
        professionSelector.hidden = isFortVisit;
    }
    if (professionEl) {
        if (party.inventory && party.inventory.money > 0) {
            professionEl.textContent = `Selected: ${party.profession || 'Unknown'}`;
        } else {
            professionEl.textContent = 'No profession selected';
        }
    }

    // Store logic
    const storePanel = document.getElementById('outfitting-store-panel');
    const storeFunds = document.getElementById('store-funds');
    const storeMainInput = document.getElementById('store-main-input');
    const storeBuyContainer = document.getElementById('store-buy-container');
    const storeMainGroup = document.getElementById('store-main-input-group');
    const storeBuyPrompt = document.getElementById('store-buy-prompt');
    const storeBuyInput = document.getElementById('store-buy-input');
    const readyBtn = document.getElementById('btn-outfit-ready');

    if (storePanel) {
        const hasProfession = party.inventory && party.inventory.money > 0;
        storePanel.hidden = !hasProfession;
        if (storeFunds) storeFunds.textContent = Math.round((party.inventory ? party.inventory.money : 0) * 100) / 100;
        
        if (readyBtn) {
            // During a fort visit, enable the button regardless of outfitting_complete
            readyBtn.disabled = !isCaptain;
            readyBtn.textContent = isFortVisit ? 'LEAVE STORE' : 'READY TO DEPART';
            readyBtn.onclick = () => {
                window.dispatchEvent(new CustomEvent('party-ready', {
                    detail: { party_id: party.party_id }
                }));
            };
        }

        const itemsKeys = ['oxen', 'food', 'clothing', 'bullets', 'wagon_wheel', 'wagon_axle', 'wagon_tongue'];
        const labels = {
            oxen: 'yoke of oxen',
            food: 'pounds of food',
            clothing: 'sets of clothes',
            bullets: 'boxes of bullets',
            wagon_wheel: 'wagon wheels',
            wagon_axle: 'wagon axles',
            wagon_tongue: 'wagon tongues',
        };
        
        if (storeMainInput && !storeMainInput.dataset.wired) {
            storeMainInput.dataset.wired = "true";
            
            // Re-disable inputs if not captain
            storeMainInput.disabled = !isCaptain;
            storeBuyInput.disabled = !isCaptain;
            
            storeMainInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    if (!isCaptain) return;
                    const val = parseInt(storeMainInput.value, 10);
                    if (val >= 1 && val <= 7) {
                        const itemKey = itemsKeys[val - 1];
                        storeMainGroup.hidden = true;
                        storeBuyContainer.hidden = false;
                        storeBuyPrompt.textContent = `How many ${labels[itemKey]} do you want?`;
                        storeBuyInput.value = '';
                        storeBuyInput.dataset.itemKey = itemKey;
                        storeBuyInput.focus();
                    }
                }
            });
            
            storeBuyInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    if (!isCaptain) return;
                    const qty = parseInt(storeBuyInput.value, 10) || 0;
                    if (qty > 0) {
                        window.dispatchEvent(new CustomEvent('buy-supplies', {
                            detail: { party_id: party.party_id, item: storeBuyInput.dataset.itemKey, quantity: qty }
                        }));
                    }
                    storeBuyContainer.hidden = true;
                    storeMainGroup.hidden = false;
                    storeMainInput.value = '';
                    storeMainInput.focus();
                }
            });
        }
    }

    // Month of Departure
    const monthPanel = document.getElementById('outfitting-month-panel');
    const monthInput = document.getElementById('month-input');
    const monthSelected = document.getElementById('month-selected');
    const monthNames = ['March', 'April', 'May', 'June', 'July'];
    
    if (monthPanel) {
        const hasProfession = party.inventory && party.inventory.money > 0;
        monthPanel.hidden = !hasProfession || isFortVisit;
        
        if (party.start_month) {
            monthSelected.textContent = `Selected: ${monthNames[party.start_month - 3] || 'Unknown'}`;
        }
        
        if (monthInput && !monthInput.dataset.wired) {
            monthInput.dataset.wired = "true";
            monthInput.disabled = !isCaptain;
            
            monthInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    if (!isCaptain) return;
                    const val = parseInt(monthInput.value, 10);
                    if (val >= 1 && val <= 5) {
                        const actualMonth = val + 2; // 1=March(3), 5=July(7)
                        window.dispatchEvent(new CustomEvent('choose-month', {
                            detail: { party_id: party.party_id, month: actualMonth }
                        }));
                        monthInput.value = '';
                    }
                }
            });
        }
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

    const statusEl = document.getElementById('outfit-status');
    if (statusEl) {
        const hasProfession = party.inventory && party.inventory.money > 0;
        if (!isCaptain) {
            statusEl.textContent = isFortVisit ? 'Waiting for the captain to finish shopping...' : 'Waiting for the captain to finish outfitting...';
        } else if (isFortVisit) {
            statusEl.textContent = 'You are at a fort. Buy supplies, then click Leave Store to continue.';
        } else if (party.outfitting_complete) {
            statusEl.textContent = 'Your party is ready to depart!';
        } else {
            statusEl.textContent = hasProfession ? 'Buy supplies for the trail, then type your choice to depart.' : 'Choose a profession to begin.';
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
