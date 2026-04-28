# Canvas Animation Architecture: 8-bit Hunting Mini-game

## 1. Lane System Design

- **Viewport**: 640×400 px.
- **Playable vertical band**: ~320 px (e.g., `y: 60` to `y: 380`), reserving top for sky and bottom for grass/HUD.
- **Lane count**: 6 lanes, each `LANE_HEIGHT = 48 px`.
- **Lane Y calculation**:
  - `baseY = 72` (first lane center)
  - `laneY = baseY + (laneIndex * LANE_HEIGHT) + (LANE_HEIGHT / 2)`
- **Jitter**: Add `±6 px` random offset so animals don't look like they're on rails.
- **Occupancy** (optional, prevents stacking):
  - Maintain `laneOccupiedUntil[laneIndex] = timestamp` (in ms).
  - Before spawning, check `Date.now() > laneOccupiedUntil[lane]`. If occupied, pick another lane or delay spawn.

```js
const LANE_HEIGHT = 48;
const LANE_BASE = 72;
const LANES = 6;

function getLaneY(index) {
  const jitter = (Math.random() * 12) - 6;
  return LANE_BASE + (index * LANE_HEIGHT) + (LANE_HEIGHT / 2) + jitter;
}

// Optional occupancy guard
const laneFreeAt = new Array(LANES).fill(0);
function isLaneOpen(index) { return performance.now() > laneFreeAt[index]; }
function occupyLane(index, durationMs) { laneFreeAt[index] = performance.now() + durationMs; }
```

## 2. Animal Entry/Exit Logic

- **Direction**: 50/50 random. `dir = Math.random() < 0.5 ? -1 : 1`.
- **Spawn edge**:
  - Moving right (`dir = 1`): spawn at `x = -SPRITE_WIDTH`.
  - Moving left (`dir = -1`): spawn at `x = CANVAS_WIDTH + SPRITE_WIDTH`.
- **Spawn timer**: Countdown in ms.
  - Base interval: `1000–3000 ms`.
  - Rarity multiplier: `rarity === 'rare' ? 3.0 : 1.0`.
- **Exit**: Mark for removal when fully off-screen (`x < -64` or `x > 704`).
- **Recycling**: Use an object pool (`animalPool`) to avoid GC stutter.

```js
const CANVAS_W = 640;
const POOL_SIZE = 16;
let animalPool = Array.from({ length: POOL_SIZE }, () => createBlankAnimal());
let activeAnimals = [];
let spawnTimer = 0;

function spawnAnimal(dt) {
  spawnTimer -= dt * 1000;
  if (spawnTimer > 0) return;

  // Pick rarity
  const rarity = Math.random() < 0.2 ? 'rare' : 'common';
  const nextDelay = (1000 + Math.random() * 2000) * (rarity === 'rare' ? 3 : 1);
  spawnTimer = nextDelay;

  // Lane selection with occupancy fallback
  let lane = Math.floor(Math.random() * LANES);
  if (!isLaneOpen(lane)) lane = (lane + 1) % LANES; // simple rotate

  // Recycle
  let animal = animalPool.find(a => !a.alive) || createBlankAnimal();
  animal.reset({
    lane,
    y: getLaneY(lane),
    dir: Math.random() < 0.5 ? -1 : 1,
    speed: (40 + Math.random() * 60), // px/sec
    type: rarity
  });
  animal.x = animal.dir === 1 ? -32 : CANVAS_W + 32;
  activeAnimals.push(animal);
  occupyLane(lane, 2500);
}

function updateAnimals(dt) {
  for (let i = activeAnimals.length - 1; i >= 0; i--) {
    const a = activeAnimals[i];
    a.x += a.dir * a.speed * dt;

    if ((a.dir === -1 && a.x < -64) || (a.dir === 1 && a.x > CANVAS_W + 64)) {
      a.alive = false;
      activeAnimals.splice(i, 1);
    }
  }
}
```

## 3. Hit Detection Strategy

- **Crosshair**: Rendered as a 12×12 reticle. For physics, treat as an 8×8 px AABB centered on mouse/touch.
- **Animal hitbox**: AABB slightly smaller than the 32×32 sprite (e.g., 24×20) so edges feel fair.
- **Input**: Single `mousedown` / `touchstart` listener on canvas. Convert touch to canvas-local coordinates.
- **Resolution**: On click, iterate active animals **back-to-front** (sorted by depth) and return the first overlap.
- **Hit vs Miss**:
  - If overlap found → `onHit(animal)` (add score, trigger death animation).
  - If no overlap → `onMiss()` (play whiff sound, brief screen flash).
- **Invulnerability / Feedback**:
  - Set `animal.state = 'dying'` immediately; remove from hit-test list.
  - Death animation runs for `400 ms` before `alive = false`.

```js
const crosshair = { x: 0, y: 0, w: 8, h: 8 };

function getPointer(e) {
  const rect = canvas.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;
  return {
    x: clientX - rect.left,
    y: clientY - rect.top
  };
}

function checkHit(px, py) {
  // Sort by depth (lower y first = far away), but we want front-most first:
  const sorted = activeAnimals.slice().sort((a, b) => b.y - a.y);

  for (const a of sorted) {
    if (a.state !== 'alive') continue;

    // Simple AABB
    if (px >= a.hitX && px <= a.hitX + a.hitW &&
        py >= a.hitY && py <= a.hitY + a.hitH) {
      return a;
    }
  }
  return null;
}

canvas.addEventListener('mousedown', (e) => {
  const p = getPointer(e);
  const target = checkHit(p.x, p.y);
  if (target) {
    target.state = 'dying';
    target.dyingTimer = 0.4;
    triggerHitFx(target.x, target.y);
  } else {
    triggerMissFx(p.x, p.y);
  }
});
```

## 4. Z-Ordering / Depth

- **Painter's Algorithm**: Draw from back (horizon) to front (near camera).
- Since higher `y` = closer to bottom of screen = closer to player, sort by `y` ascending:
  1. Draw background elements (sky, mountains).
  2. Sort `activeAnimals` by `a.y - b.y` (smaller y first).
  3. Draw animals in that order.
  4. Draw foreground (grass tufts, HUD).

```js
function draw(ctx) {
  ctx.clearRect(0, 0, CANVAS_W, 400);
  drawBackground(ctx);

  // Z-sort: far (small y) → near (large y)
  activeAnimals.sort((a, b) => a.y - b.y);
  for (const a of activeAnimals) {
    drawAnimal(ctx, a);
  }

  drawForeground(ctx);
  drawCrosshair(ctx, crosshair.x, crosshair.y);
}
```

## 5. Frame Budget / Performance

- **Max on-screen animals**: Cap at `10`. If `activeAnimals.length >= 10`, skip spawning.
- **Delta time**: Use `dt` in seconds, capped at `0.1 s` to prevent physics explosions on lag spikes.
- **Object pool**: Re-use animal objects; avoid `new` / `delete` per spawn.
- **Draw call batching**: Use a single `drawImage` sprite sheet; avoid state changes.
- **Target**: 60 FPS on low-end hardware. If frame time > 16 ms, reduce particle counts first.

```js
let lastTime = performance.now();

function loop(now) {
  const rawDt = (now - lastTime) / 1000;
  const dt = Math.min(rawDt, 0.1); // cap delta
  lastTime = now;

  if (activeAnimals.length < 10) spawnAnimal(dt);
  updateAnimals(dt);
  updateFx(dt);
  draw(ctx);

  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
```

---

*Designed for a 640×400 8-bit aesthetic. All values are tuned for 1× pixel art; adjust hitbox sizes if sprites scale.*
