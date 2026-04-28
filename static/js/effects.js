/**
 * Visual effects module: travel animation, weather, flashes, transitions,
 * ambient messages, and typewriter text.
 */

// ------------------------------------------------------------------
// Terrain-aware ASCII landscapes
// ------------------------------------------------------------------

const TERRAIN_FRAMES = {
    prairie: [
        `    ~~~~~~                    ~~~~~~                ~~      \n   ~      ~                  ~      ~              ~  ~     \n  ~   __   ~       ~~        ~   __   ~    ~~      ~    ~   \n ~   /  \\   ~     ~  ~      ~   /  \\   ~  ~  ~    ~  __ ~  \n~___/    \\___~___~____~____~___/    \\___~____~_____/    \\_`,
        `   ~~~~~~                    ~~~~~~                ~~       \n  ~      ~                  ~      ~              ~  ~      \n ~   __   ~       ~~        ~   __   ~    ~~      ~    ~    \n~   /  \\   ~     ~  ~      ~   /  \\   ~  ~  ~    ~  __ ~   \n___/    \\___~___~____~____~___/    \\___~____~_____/    \\__`,
        `  ~~~~~~                    ~~~~~~                ~~        \n ~      ~                  ~      ~              ~  ~       \n~   __   ~       ~~        ~   __   ~    ~~      ~    ~     \n   /  \\   ~     ~  ~      ~   /  \\   ~  ~  ~    ~  __ ~    \n__/    \\___~___~____~____~___/    \\___~____~_____/    \\___`,
    ],
    mountains: [
        `                    /\\                                      \n      /\\          /  \\  /\\                  /\\            \n     /  \\  /\\    /    \\/  \\      /\\       /  \\   /\\      \n    /    \\/  \\  /          \\    /  \\  /\\  /    \\ /  \\     \n___/          \\/            \\__/    \\/  \\/      \\/    \\____`,
        `      /\\          /\\                    /\\                \n     /  \\  /\\    /  \\  /\\      /\\     /  \\   /\\          \n    /    \\/  \\  /    \\/  \\    /  \\   /    \\ /  \\   /\\    \n___/          \\/          \\  /    \\  /      \\/    \\ /  \\___\n                            \\/      \\/              \\/      `,
        `    /\\          /\\          /\\                          \n   /  \\  /\\    /  \\  /\\    /  \\        /\\       /\\       \n  /    \\/  \\  /    \\/  \\  /    \\  /\\  /  \\  /\\ /  \\      \n_/          \\/          \\/      \\ /  \\/    \\/  \\/    \\_____\n                                  \\/      \\/              `,
    ],
    desert: [
        `                                                             \n   .     .          .    .             .      .      .       \n      .       .  .      .    .    .       .      .    .  .  \n .  .    .  .     .  .     .     .   .  .    .  .    .      \n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~`,
        `  .     .          .    .             .      .      .       \n     .       .  .      .    .    .       .      .    .  .   \n.  .    .  .     .  .     .     .   .  .    .  .    .       \n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n                                                            `,
        `    .          .    .             .      .      .         \n .       .  .      .    .    .       .      .    .  .       \n  .    .  .     .  .     .     .   .  .    .  .    .        \n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n .     .          .    .             .      .      .         `,
    ],
    forest: [
        ` |  |      | |       |  |       |      |  |      | |       |\n/|\\/|\\    /|\\|      /|\\/|\\    /|\\    /|\\/|\\    /|\\|      \n || ||     | | |      || ||     | |     || ||     | | |     \n || ||     | | |      || ||     | |     || ||     | | |     \n____________________________________________________________`,
        `  | |      |  |       | |       |  |      | |      |  |     \n /|\\|      /|\\/|\\    /|\\|      /|\\/|\\    /|\\|      /|\\/|\\ \n | | |      || ||     | | |      || ||     | | |      || || \n | | |      || ||     | | |      || ||     | | |      || || \n____________________________________________________________`,
        ` |  |       | |      |  |       | |      |  |       | |    \n/|\\/|\\     /|\\|     /|\\/|\\     /|\\|     /|\\/|\\     /|\\|   \n || ||      | | |     || ||      | | |     || ||      | | |  \n || ||      | | |     || ||      | | |     || ||      | | |  \n____________________________________________________________`,
    ],
};

const TERRAIN_LABELS = {
    prairie: 'Great Plains',
    mountains: 'Rocky Mountains',
    desert: 'High Desert',
    forest: 'Timberlands',
};

// Landmark ASCII vignettes
const LANDMARK_ASCII = {
    default: `
        /\\
       /  \\
      /    \\
     /______\\
        ||
        ||`,
    'Independence, Missouri': `
    _____
   |  _  |___
   | |_| |___|
   |_____|
   |  |  |
  _|__|__|_
 |_________|`,
    'Kansas River Crossing': `
   ~~~~~~~~~~~~~~~
   ~~~~~~~~~~~~~~~
   ~~  _|_  ~~~~~~
   ~~ /   \\ ~~~~~
   ~~/_____\\~~~~~
   ~~~~~~~~~~~~~~~`,
    'Big Blue River Crossing': `
   ~~~~~~~~~~~~~~~
   ~~ /\\  /\\ ~~~~
   ~~/  \\/  \\~~~~
   ~~~~~~~~~~~~~~~
   ~~~~~~~~~~~~~~~`,
    'Fort Kearney': `
      /\\
     /__\\
    |    |
    | [] |
    |____|
   /|    |\\
  / |____| \\`,
    'Chimney Rock': `
         /\\
        /  \\
       /    \\
      /      \\
     /________\\
    /          \\
   /            \\`,
    'Fort Laramie': `
   _____________
  |  []   []   |
  |____________|
   | |    | |
   |_|____|_|`,
    'Independence Rock': `
       _____
     /       \\
    /         \\
   /___________\\
   \\___________/`,
    'South Pass': `
       /\\    /\\
      /  \\  /  \\
   __/    \\/    \\__
  /                  \\
 /____________________\\`,
    'Fort Bridger': `
      _____
     |     |
     | [ ] |
     |_____|
    /       \\
   /_________\\`,
    'Green River Crossing': `
   ~~~~~~~~~~~~~~~~~~
   ~~~~~~~~~~~~~~~~~~
   ~~  _      _  ~~~~
   ~~ / \\    / \\ ~~~
   ~~/___\\  /___\\~~
   ~~~~~~~~~~~~~~~~~~`,
    'Soda Springs': `
      o    o
       o  o
    o   oo   o
     o  oo  o
      oooooo
   ~~~~~~~~~~~~`,
    'Fort Hall': `
    ___________
   | []     [] |
   |___________|
    | |_____| |
    | |     | |`,
    'Snake River Crossing': `
   ~~~~~~~~~~~~~~~~~~~~
   ~~~~  ~~~~~~  ~~~~~~
   ~~  \/      \/  ~~~~
   ~~~~~~~~~~~~~~~~~~~~
   ~~~~~~~~~~~~~~~~~~~~`,
    'Fort Boise': `
      /\\____/\\
     /        \\
    |   []     |
    |__________|
     | |    | |`,
    'Blue Mountains': `
      /\\      /\\
     /  \\    /  \\
    /    \\  /    \\
   /      \\/      \\
  /__________________\\`,
    'Fort Walla Walla': `
    ___________
   |  |    |  |
   |__|____|__|
   |          |
   |__________|`,
    'The Dalles': `
   ~~~~~~~~~~~~~~~~~~~~
   ~~~~~~~~~~~~~~~~~~~~
   ~~ /\\  /\\  /\\ ~~~~
   ~~/  \\/  \\/  \\~~~~
   ~~~~~~~~~~~~~~~~~~~~`,
    'Willamette Valley, Oregon': `
      \\\   |   ///
       \\\  |  ///
        \\\ | ///
    _____\\\|///_____
   /                \\
  /__________________\\`,
};

// Wagon ASCII art (stationary in center)
const WAGON_ART = `
     (|)
  __/|\\__
 /  o o  \\
|    >    |
 \\_______/
   |   |
  O|   |O`;

// Idle ambient messages
const IDLE_MESSAGES = [
    'The oxen plod steadily forward...',
    'Dust kicks up behind the wagon.',
    'A hawk circles overhead.',
    'The prairie stretches endlessly westward.',
    'You hear the creak of wagon wheels.',
    'Grasshoppers buzz in the tall grass.',
    'The sun beats down on the canvas cover.',
    'A gentle breeze carries the smell of sage.',
    'The trail winds onward through the wilderness.',
    'Birds call from distant trees.',
    'Your wagon sways with each rut in the trail.',
    'The oxen low softly as they pull.',
    'Clouds drift lazily across the sky.',
    'The horizon seems to move no closer.',
    'A rabbit darts across the trail.',
];

let travelAnimationId = null;
let weatherInterval = null;
let idleMessageInterval = null;
let currentTerrain = 'prairie';
let travelFrameIndex = 0;
let travelTick = 0;

// ------------------------------------------------------------------
// Travel Animation
// ------------------------------------------------------------------

function getTerrainForMiles(miles) {
    if (miles < 304) return 'prairie';
    if (miles < 640) return 'prairie';
    if (miles < 932) return 'mountains';
    if (miles < 1132) return 'desert';
    if (miles < 1300) return 'mountains';
    if (miles < 1534) return 'desert';
    if (miles < 1710) return 'mountains';
    if (miles < 1830) return 'forest';
    return 'mountains';
}

function renderTravelScene(terrain, frameIdx) {
    const frames = TERRAIN_FRAMES[terrain] || TERRAIN_FRAMES.prairie;
    const frame = frames[frameIdx % frames.length];
    const lines = frame.split('\n');

    // Insert wagon into the middle-bottom area
    const wagonLines = WAGON_ART.trim().split('\n');
    const outputLines = lines.map((line, i) => {
        const targetRow = lines.length - wagonLines.length + wagonLines.findIndex(() => true);
        // Find which wagon line should go here
        const wagonRow = i - (lines.length - wagonLines.length);
        if (wagonRow >= 0 && wagonRow < wagonLines.length) {
            const wagonLine = wagonLines[wagonRow];
            const insertPos = Math.floor((line.length - wagonLine.length) / 2);
            if (insertPos > 0) {
                return line.slice(0, insertPos) + wagonLine + line.slice(insertPos + wagonLine.length);
            }
        }
        return line;
    });

    return outputLines.join('\n');
}

function startTravelAnimation(miles) {
    stopTravelAnimation();
    currentTerrain = getTerrainForMiles(miles || 0);
    travelFrameIndex = 0;
    travelTick = 0;

    const sceneEl = document.getElementById('travel-scene');
    const labelEl = document.getElementById('travel-terrain');
    if (!sceneEl) return;

    if (labelEl) labelEl.textContent = TERRAIN_LABELS[currentTerrain] || '';

    function tick() {
        travelTick++;
        if (travelTick % 4 === 0) {
            travelFrameIndex++;
            if (sceneEl) {
                sceneEl.textContent = renderTravelScene(currentTerrain, travelFrameIndex);
            }
        }
        travelAnimationId = requestAnimationFrame(tick);
    }
    // Initial render
    sceneEl.textContent = renderTravelScene(currentTerrain, 0);
    travelAnimationId = requestAnimationFrame(tick);
}

function updateTravelTerrain(miles) {
    const newTerrain = getTerrainForMiles(miles || 0);
    if (newTerrain !== currentTerrain) {
        currentTerrain = newTerrain;
        const labelEl = document.getElementById('travel-terrain');
        if (labelEl) labelEl.textContent = TERRAIN_LABELS[currentTerrain] || '';
    }
}

function stopTravelAnimation() {
    if (travelAnimationId) {
        cancelAnimationFrame(travelAnimationId);
        travelAnimationId = null;
    }
}

// ------------------------------------------------------------------
// Landmark Overlays
// ------------------------------------------------------------------

function showLandmarkOverlay(landmarkName, description) {
    const overlay = document.getElementById('landmark-overlay');
    const asciiEl = document.getElementById('landmark-ascii');
    const nameEl = document.getElementById('landmark-name');
    const descEl = document.getElementById('landmark-desc');
    if (!overlay) return;

    const ascii = LANDMARK_ASCII[landmarkName] || LANDMARK_ASCII.default;
    if (asciiEl) asciiEl.textContent = ascii;
    if (nameEl) nameEl.textContent = landmarkName;
    if (descEl) descEl.textContent = description || '';

    overlay.hidden = false;
    // Force reflow
    overlay.offsetHeight;
    overlay.classList.add('show');

    // Auto-hide after 4 seconds
    setTimeout(() => hideLandmarkOverlay(), 4000);
}

function hideLandmarkOverlay() {
    const overlay = document.getElementById('landmark-overlay');
    if (!overlay) return;
    overlay.classList.remove('show');
    setTimeout(() => {
        if (!overlay.classList.contains('show')) {
            overlay.hidden = true;
        }
    }, 500);
}

// ------------------------------------------------------------------
// Weather Effects
// ------------------------------------------------------------------

function startWeatherEffect(weatherType) {
    stopWeatherEffect();
    const overlay = document.getElementById('weather-overlay');
    const container = document.getElementById('weather-particles');
    if (!overlay || !container) return;

    overlay.hidden = false;
    container.innerHTML = '';
    overlay.className = 'weather-overlay';

    if (weatherType === 'Heavy Rain') {
        overlay.classList.add('weather-rain');
        createParticles(container, 60, 'rain');
    } else if (weatherType === 'Snow') {
        overlay.classList.add('weather-snow');
        createParticles(container, 40, 'snow');
    } else if (weatherType === 'Hot' || weatherType === 'Very Hot') {
        overlay.classList.add('weather-heat');
        createParticles(container, 20, 'heat');
    } else {
        overlay.hidden = true;
    }
}

function createParticles(container, count, type) {
    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.className = 'weather-particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDelay = Math.random() * 3 + 's';
        p.style.animationDuration = (1.5 + Math.random() * 2) + 's';
        if (type === 'heat') {
            p.style.top = Math.random() * 100 + '%';
            p.style.animationDuration = (3 + Math.random() * 4) + 's';
        }
        container.appendChild(p);
    }
}

function stopWeatherEffect() {
    const overlay = document.getElementById('weather-overlay');
    const container = document.getElementById('weather-particles');
    if (overlay) {
        overlay.hidden = true;
        overlay.className = 'weather-overlay';
    }
    if (container) container.innerHTML = '';
}

// ------------------------------------------------------------------
// Flash Effects
// ------------------------------------------------------------------

function flashScreen(type, duration = 600) {
    const overlay = document.getElementById('flash-overlay');
    if (!overlay) return;

    overlay.className = 'flash-overlay';
    overlay.hidden = false;
    overlay.offsetHeight; // reflow
    overlay.classList.add('active', `flash-${type}`);

    setTimeout(() => {
        overlay.classList.remove('active');
        setTimeout(() => {
            if (!overlay.classList.contains('active')) {
                overlay.hidden = true;
            }
        }, 150);
    }, duration);
}

// ------------------------------------------------------------------
// Screen Transitions
// ------------------------------------------------------------------

function transitionTo(callback, delay = 300) {
    const curtain = document.getElementById('transition-curtain');
    if (!curtain) {
        callback();
        return;
    }
    curtain.hidden = false;
    curtain.offsetHeight;
    curtain.classList.add('show');

    setTimeout(() => {
        callback();
        setTimeout(() => {
            curtain.classList.remove('show');
            setTimeout(() => {
                if (!curtain.classList.contains('show')) curtain.hidden = true;
            }, 400);
        }, delay);
    }, 400);
}

function playCRTBoot(onComplete) {
    const bootEl = document.getElementById('crt-boot');
    const textEl = bootEl ? bootEl.querySelector('.crt-boot-text') : null;
    if (!bootEl || !textEl) {
        if (onComplete) onComplete();
        return;
    }

    bootEl.hidden = false;
    const lines = [
        'BIOS DATE 01/15/1847 14:22:51 VER 1.02',
        'CPU: OREGON-TRAIL-486 8MHz',
        '640K RAM SYSTEM... OK',
        '',
        'LOADING OREGON TRAIL: CLASSROOM EDITION...',
        'MOUNTING WAGON_DRIVE... OK',
        'CALIBRATING OXEN... OK',
        'CHECKING SUPPLIES... OK',
        '',
        'PRESS ANY KEY TO CONTINUE...',
    ];

    let lineIdx = 0;
    textEl.textContent = '';

    function typeNextLine() {
        if (lineIdx >= lines.length) {
            setTimeout(() => {
                bootEl.style.opacity = '0';
                bootEl.style.transition = 'opacity 0.5s ease';
                setTimeout(() => {
                    bootEl.hidden = true;
                    bootEl.style.opacity = '';
                    bootEl.style.transition = '';
                    if (onComplete) onComplete();
                }, 500);
            }, 600);
            return;
        }
        textEl.textContent += lines[lineIdx] + '\n';
        lineIdx++;
        setTimeout(typeNextLine, 180 + Math.random() * 200);
    }

    // Small initial delay for dramatic effect
    setTimeout(typeNextLine, 400);

    // Allow click/keyboard to skip
    const skip = () => {
        lineIdx = lines.length;
        textEl.textContent = lines.join('\n');
    };
    bootEl.addEventListener('click', skip, { once: true });
    document.addEventListener('keydown', skip, { once: true });
}

// ------------------------------------------------------------------
// Ambient Messages
// ------------------------------------------------------------------

function startAmbientMessages() {
    stopAmbientMessages();
    const ticker = document.getElementById('ambient-ticker');
    if (!ticker) return;

    function showNext() {
        const msg = IDLE_MESSAGES[Math.floor(Math.random() * IDLE_MESSAGES.length)];
        ticker.style.opacity = '0';
        setTimeout(() => {
            ticker.textContent = `— ${msg}`;
            ticker.style.opacity = '1';
        }, 400);
    }

    ticker.style.transition = 'opacity 0.4s ease';
    showNext();
    idleMessageInterval = setInterval(showNext, 8000);
}

function stopAmbientMessages() {
    if (idleMessageInterval) {
        clearInterval(idleMessageInterval);
        idleMessageInterval = null;
    }
}

// ------------------------------------------------------------------
// Typewriter Text
// ------------------------------------------------------------------

function typewriterText(element, text, speed = 30) {
    return new Promise((resolve) => {
        if (!element) {
            resolve();
            return;
        }
        element.textContent = '';
        element.classList.add('typewriter-text');
        let i = 0;

        function typeChar() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(typeChar, speed);
            } else {
                // Keep cursor blinking briefly then remove
                setTimeout(() => {
                    element.classList.remove('typewriter-text');
                    resolve();
                }, 1200);
            }
        }
        typeChar();
    });
}

// ------------------------------------------------------------------
// Decision Timer Bar
// ------------------------------------------------------------------

function updateDecisionTimerBar(remaining, total) {
    const fill = document.getElementById('decision-timer-fill');
    if (!fill) return;

    const pct = Math.max(0, (remaining / total) * 100);
    fill.style.width = pct + '%';

    fill.classList.remove('warning', 'danger');
    if (pct <= 20) {
        fill.classList.add('danger');
    } else if (pct <= 50) {
        fill.classList.add('warning');
    }
}

function resetDecisionTimerBar() {
    const fill = document.getElementById('decision-timer-fill');
    if (!fill) return;
    fill.style.width = '100%';
    fill.classList.remove('warning', 'danger');
}

// ------------------------------------------------------------------
// Status Bar Helpers
// ------------------------------------------------------------------

function getHealthClass(healthStatus) {
    const map = {
        'Healthy': 'stat-health-good',
        'Fair': 'stat-health-fair',
        'Poor': 'stat-health-poor',
        'Very Poor': 'stat-health-verypoor',
        'Dead': 'stat-health-dead',
    };
    return map[healthStatus] || 'stat-health-good';
}

function getWeatherClass(weather) {
    if (weather === 'Heavy Rain') return 'stat-weather-rain';
    if (weather === 'Snow') return 'stat-weather-snow';
    if (weather === 'Hot' || weather === 'Very Hot') return 'stat-weather-hot';
    if (weather === 'Cold' || weather === 'Very Cold') return 'stat-weather-cold';
    return '';
}

// ------------------------------------------------------------------
// Exports
// ------------------------------------------------------------------

export {
    startTravelAnimation,
    stopTravelAnimation,
    updateTravelTerrain,
    showLandmarkOverlay,
    hideLandmarkOverlay,
    startWeatherEffect,
    stopWeatherEffect,
    flashScreen,
    transitionTo,
    playCRTBoot,
    startAmbientMessages,
    stopAmbientMessages,
    typewriterText,
    updateDecisionTimerBar,
    resetDecisionTimerBar,
    getHealthClass,
    getWeatherClass,
};
