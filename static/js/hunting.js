/**
 * Hunting Mini-game Logic - Authentic Apple II Retro Style
 */
import * as Network from './network.js';

const canvas = document.getElementById('hunting-canvas');
const ctx = canvas.getContext('2d');
const ammoEl = document.getElementById('hunt-ammo');
const timerEl = document.getElementById('hunt-timer');
const overlay = document.getElementById('hunt-overlay');
const overlayText = document.getElementById('hunt-overlay-text');
const btnEnd = document.getElementById('btn-end-hunt');

let isRunning = false;
let huntStartTime = 0;
let huntDuration = 30; // seconds
let shotsHit = 0;
let bulletsLeft = 0;
let lastState = null;
let myPlayerId = null;

let animals = [];
let bullets = [];
let mouseX = canvas.width / 2;
let mouseY = canvas.height / 2;

// Hunter State
let hx = canvas.width / 2;
let hy = canvas.height / 2;
let hdx = 1; // Facing direction X
let hdy = 0; // Facing direction Y
let hSpeed = 3;

// Keyboard State
const keys = {
    ArrowUp: false, ArrowDown: false, ArrowLeft: false, ArrowRight: false,
    w: false, a: false, s: false, d: false, ' ': false
};

// ------------------------------------------------------------------
// Retro Assets (1 = pixel, space = empty)
// ------------------------------------------------------------------
const PIXEL_SIZE = 8;
const TERM_GREEN = '#4af626';

const SPRITES = {
    hunter: [
        "  111  ",
        "  111  ",
        "  111  ",
        " 11111 ",
        " 1 1 1 ",
        "  1 1  ",
        "  1 1  "
    ],
    hunter_shoot_right: [
        "  111  ",
        "  111  ",
        "  111  ",
        " 1111111",
        " 1 1   ",
        "  1 1  ",
        "  1 1  "
    ],
    rabbit: [
        " 1  1   ",
        " 1  1   ",
        " 11111  ",
        " 1111   ",
        "  1 1   "
    ],
    squirrel: [
        "   11 ",
        "  11  ",
        " 111  ",
        " 1111 ",
        "  1 1 "
    ],
    deer: [
        "1  1       ",
        " 11        ",
        "1111       ",
        " 111111111 ",
        "  111111111",
        "  11    11 ",
        "  1      1 "
    ],
    bear: [
        "  11       ",
        " 1111      ",
        "1111111111 ",
        "11111111111",
        "111    111 ",
        " 11      11"
    ],
    buffalo: [
        "  111      ",
        " 11111111  ",
        "11111111111",
        "11111111111",
        " 111111111 ",
        "  11    11 ",
        "  11    11 "
    ]
};

// ------------------------------------------------------------------
// Sound Synthesizer (Web Audio API)
// ------------------------------------------------------------------
let audioCtx = null;

function initAudio() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) audioCtx = new AudioContext();
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playBleep(frequency, duration, type='square') {
    if (!audioCtx) return;
    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(frequency, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
        
        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch (e) {
        console.error("Audio error", e);
    }
}

function playGunshot() {
    if (!audioCtx) return;
    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(100, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1, audioCtx.currentTime + 0.1);
        
        gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.1);
        
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.1);
    } catch (e) {
        console.error("Audio error", e);
    }
}

// ------------------------------------------------------------------
// Engine
// ------------------------------------------------------------------

export function start(state, playerId) {
    if (isRunning) return;
    isRunning = true;
    lastState = state;
    myPlayerId = playerId;
    
    const partyId = state.players[playerId].party_id;
    const party = state.parties[partyId];
    
    bulletsLeft = party.inventory ? (party.inventory.bullets || 0) : 0;
    shotsHit = 0;
    animals = [];
    bullets = [];
    huntStartTime = Date.now();
    hx = canvas.width / 2;
    hy = canvas.height / 2;
    hdx = 1;
    hdy = 0;
    
    updateUI();
    
    if (bulletsLeft <= 0) {
        showOverlay('NO BULLETS! HUNT FAILED.', 3000, () => {
            finishHunt();
        });
        return;
    }
    
    showOverlay('INITIATING CRT MODULE...', 2000, () => {
        initAudio(); // Required to start within user gesture (usually satisfied implicitly)
        requestAnimationFrame(gameLoop);
    });
}

export function stop() {
    isRunning = false;
    hideOverlay();
}

function gameLoop() {
    if (!isRunning) return;
    
    const elapsed = (Date.now() - huntStartTime) / 1000;
    const remaining = Math.max(0, huntDuration - elapsed);
    
    updateUI(remaining);
    updateGameLogic();
    render();
    
    if (remaining <= 0) {
        finishHunt();
    } else {
        requestAnimationFrame(gameLoop);
    }
}

// ------------------------------------------------------------------
// Game Logic
// ------------------------------------------------------------------

function updateGameLogic() {
    // Spawning
    if (Math.random() < 0.02 && animals.length < 5) {
        spawnAnimal();
    }
    
    // Move Hunter
    let moving = false;
    let newHdx = 0;
    let newHdy = 0;
    
    if (keys.ArrowUp || keys.w) { hy -= hSpeed; newHdy = -1; moving = true; }
    if (keys.ArrowDown || keys.s) { hy += hSpeed; newHdy = 1; moving = true; }
    if (keys.ArrowLeft || keys.a) { hx -= hSpeed; newHdx = -1; moving = true; }
    if (keys.ArrowRight || keys.d) { hx += hSpeed; newHdx = 1; moving = true; }
    
    if (moving) {
        hdx = newHdx;
        hdy = newHdy;
    }
    
    // Bounds check hunter
    hx = Math.max(10, Math.min(canvas.width - 10, hx));
    hy = Math.max(10, Math.min(canvas.height - 10, hy));
    
    // Update Animals
    for (let i = animals.length - 1; i >= 0; i--) {
        const a = animals[i];
        a.x += a.vx;
        
        // Out of bounds
        if (a.x < -100 || a.x > canvas.width + 100) {
            animals.splice(i, 1);
        }
    }
    
    // Update Bullets
    for (let i = bullets.length - 1; i >= 0; i--) {
        const b = bullets[i];
        b.x += b.vx;
        b.y += b.vy;
        b.life--;
        
        if (b.life <= 0) {
            bullets.splice(i, 1);
            continue;
        }
        
        // Collision Detection
        for (let j = animals.length - 1; j >= 0; j--) {
            const a = animals[j];
            const sprite = SPRITES[a.type];
            const w = sprite[0].length * PIXEL_SIZE;
            const h = sprite.length * PIXEL_SIZE;
            
            if (b.x >= a.x && b.x <= a.x + w && b.y >= a.y && b.y <= a.y + h) {
                // HIT!
                playBleep(800, 0.1, 'square');
                animals.splice(j, 1); // Remove animal
                bullets.splice(i, 1); // Remove bullet
                shotsHit++;
                updateUI();
                break;
            }
        }
    }
}

function spawnAnimal() {
    const types = ['rabbit', 'squirrel', 'deer', 'bear', 'buffalo'];
    const type = types[Math.floor(Math.random() * types.length)];
    
    let speedOpts = {
        'rabbit': { v: 3, points: 2 },
        'squirrel': { v: 4, points: 1 },
        'deer': { v: 2, points: 50 },
        'bear': { v: 1.5, points: 100 },
        'buffalo': { v: 1, points: 100 }
    };
    
    const isLeft = Math.random() < 0.5;
    const y = 50 + Math.random() * (canvas.height - 150);
    
    animals.push({
        type: type,
        x: isLeft ? -50 : canvas.width + 50,
        y: y,
        vx: isLeft ? speedOpts[type].v : -speedOpts[type].v,
        points: speedOpts[type].points,
        facingLeft: !isLeft
    });
}

// ------------------------------------------------------------------
// Rendering
// ------------------------------------------------------------------

function drawSprite(arr, px, py, flipX=false) {
    const rows = arr.length;
    const cols = arr[0].length;
    
    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            if (arr[y][x] !== ' ') {
                const drawX = flipX ? (px + (cols - 1 - x) * PIXEL_SIZE) : (px + x * PIXEL_SIZE);
                const drawY = py + y * PIXEL_SIZE;
                ctx.fillRect(drawX, drawY, PIXEL_SIZE, PIXEL_SIZE);
            }
        }
    }
}

function render() {
    if (!ctx) return;

    // Clear
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Scenery (Horizon line)
    ctx.fillStyle = TERM_GREEN;
    for(let i=0; i<canvas.width; i+=20) {
         ctx.fillRect(i, canvas.height - 50, 10, 2);
    }
    
    ctx.fillStyle = TERM_GREEN;

    // Draw Animals
    animals.forEach(a => {
        drawSprite(SPRITES[a.type], a.x, a.y, a.facingLeft);
    });
    
    // Draw Hunter
    const mouseIsLeft = hdx < 0;
    // Basic sprite selection
    const spriteName = (hdx !== 0 || hdy !== 0) ? 'hunter_shoot_right' : 'hunter';
    drawSprite(SPRITES[spriteName], hx - 14, hy - 14, mouseIsLeft);
    
    // Draw Bullets
    bullets.forEach(b => {
        ctx.fillRect(b.x, b.y, 4, 4);
    });
    
    // Draw crosshair or sight line to show direction
    if (bulletsLeft > 0) {
        ctx.fillStyle = 'rgba(74, 246, 38, 0.3)';
        ctx.fillRect(hx + hdx * 20, hy + hdy * 20 + 10, 4, 4);
    }
}

function updateUI(remaining = huntDuration) {
    if (ammoEl) ammoEl.textContent = bulletsLeft;
    if (timerEl) timerEl.textContent = Math.ceil(remaining);
}

function showOverlay(text, duration, callback) {
    if (!overlay) return;
    overlay.hidden = false;
    overlayText.textContent = text;
    if (duration) {
        setTimeout(() => {
            hideOverlay();
            if (callback) callback();
        }, duration);
    }
}

function hideOverlay() {
    if (overlay) overlay.hidden = true;
}

function finishHunt() {
    if (!isRunning) return;
    isRunning = false;
    
    showOverlay('HUNT OVER!', 2000, () => {
        const partyId = lastState.players[myPlayerId].party_id;
        Network.emit('resolve_hunt', {
            party_id: partyId,
            shots_hit: shotsHit
        });
    });
}

// ------------------------------------------------------------------
// Interaction
// ------------------------------------------------------------------

if (canvas) {
    // Also listen to keyboard for movement and shooting
    document.addEventListener('keydown', (e) => {
        if (!isRunning) return;
        if (keys.hasOwnProperty(e.key)) {
            keys[e.key] = true;
            if (e.key === ' ' || e.key === 'Spacebar') {
                e.preventDefault(); // prevent scrolling
                fireBullet();
            }
        }
    });

    document.addEventListener('keyup', (e) => {
        if (!isRunning) return;
        if (keys.hasOwnProperty(e.key)) {
            keys[e.key] = false;
        }
    });
    
    // Mouse fallback for shooting
    canvas.addEventListener('mousedown', (e) => {
        if (!isRunning) return;
        
        // Calculate direction towards mouse
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const mx = (e.clientX - rect.left) * scaleX;
        const my = (e.clientY - rect.top) * scaleY;
        
        const dx = mx - hx;
        const dy = my - hy;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        hdx = dx / dist;
        hdy = dy / dist;

        fireBullet();
    });
}

function fireBullet() {
    if (bulletsLeft <= 0) return;
    initAudio();
    
    bulletsLeft--;
    playGunshot();
    
    // Normalize direction
    let dx = hdx;
    let dy = hdy;
    if (dx === 0 && dy === 0) dx = 1; // default fire right
    const dist = Math.sqrt(dx*dx + dy*dy);
    
    bullets.push({
        x: hx,
        y: hy + 10,
        vx: (dx / dist) * 15,
        vy: (dy / dist) * 15,
        life: 50
    });
    
    updateUI();
}

if (btnEnd) {
    btnEnd.addEventListener('click', () => {
        finishHunt();
    });
}
