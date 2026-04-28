/**
 * Hunting Mini-game Engine for Oregon Trail (1985/1990 faithful remake)
 *
 * Mechanics based on the original Apple II / DOS versions:
 * - 100 lb carry limit per hunt (excess is wasted)
 * - 1 day cost per hunt
 * - ~30-45 second real-time daylight timer
 * - Third-person hunter character who aims in 8 directions
 * - Terrain zones affect animal spawns
 * - Upside-down flip death animation
 * - Free-roaming animal movement
 * - Black background with scattered terrain objects
 *
 * Drop this file into static/js/hunting_game.js for your Flask app.
 */

// ---------------------------------------------------------------------------
// Animal Configuration
// ---------------------------------------------------------------------------
import { SpriteRenderer } from './hunting_sprites.js';
import { TerrainSystem } from './hunting_terrain.js';

const ANIMAL_DATA = {
  squirrel: {
    speed: 2.2,
    hitbox_w: 16, hitbox_h: 10,
    food: 2,
    sprite_w: 20, sprite_h: 14,
    color: '#8d6e63',
    // Erratic, fast zig-zag pattern
    movementPattern: 'zigzag'
  },
  rabbit: {
    speed: 1.8,
    hitbox_w: 20, hitbox_h: 12,
    food: 5,
    sprite_w: 24, sprite_h: 16,
    color: '#9e9e9e',
    // Fast, quick direction changes
    movementPattern: 'zigzag'
  },
  deer: {
    speed: 1.3,
    hitbox_w: 40, hitbox_h: 28,
    food: 60,
    sprite_w: 48, sprite_h: 34,
    color: '#d7ccc8',
    // Graceful, longer straight runs with occasional turns
    movementPattern: 'graceful'
  },
  elk: {
    speed: 1.1,
    hitbox_w: 50, hitbox_h: 36,
    food: 100,
    sprite_w: 60, sprite_h: 42,
    color: '#5d4037',
    // Steady, medium straight runs
    movementPattern: 'steady'
  },
  bear: {
    speed: 0.9,
    hitbox_w: 55, hitbox_h: 40,
    food: 400,
    sprite_w: 66, sprite_h: 48,
    color: '#3e2723',
    // Slow but powerful, may charge toward player
    movementPattern: 'wander'
  },
  buffalo: {
    speed: 0.7,
    hitbox_w: 60, hitbox_h: 44,
    food: 800,
    sprite_w: 72, sprite_h: 52,
    color: '#424242',
    // Very slow and steady
    movementPattern: 'steady'
  }
};

// ---------------------------------------------------------------------------
// Terrain Zones - which animals appear where
// ---------------------------------------------------------------------------
// Fallback zone mappings (TerrainSystem.ZONES is authoritative)
const ZONE_ANIMALS = {
  eastern_forest:  ['squirrel', 'rabbit', 'deer'],
  plains:          ['rabbit', 'deer', 'buffalo'],
  rocky_mountains: ['deer', 'elk', 'bear'],
  desert:          ['rabbit', 'squirrel'],
  western_forest:  ['deer', 'elk', 'bear']
};

// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------

/**
 * Snap an angle (in radians) to the nearest of 8 directions (N, NE, E, SE, S, SW, W, NW).
 * @param {number} angle - angle in radians
 * @returns {number} snapped angle in radians
 */
function snapTo8Direction(angle) {
  const step = Math.PI / 4; // 45 degrees
  return Math.round(angle / step) * step;
}

/**
 * Check if two axis-aligned bounding boxes intersect.
 * @param {{x:number,y:number,w:number,h:number}} a
 * @param {{x:number,y:number,w:number,h:number}} b
 * @returns {boolean}
 */
function aabbIntersect(a, b) {
  return (
    a.x < b.x + b.w &&
    a.x + a.w > b.x &&
    a.y < b.y + b.h &&
    a.y + a.h > b.y
  );
}

// ---------------------------------------------------------------------------
// Bullet Class
// ---------------------------------------------------------------------------
class Bullet {
  /**
   * @param {number} x - starting x position
   * @param {number} y - starting y position
   * @param {number} angle - direction in radians
   * @param {number} speed - pixels per second
   * @param {number} maxRange - maximum travel distance in pixels
   */
  constructor(x, y, angle, speed = 600, maxRange = 500) {
    this.x = x;
    this.y = y;
    this.startX = x;
    this.startY = y;
    this.angle = angle;
    this.speed = speed;
    this.maxRange = maxRange;
    this.active = true;
    this.radius = 2;
  }

  update(dt) {
    if (!this.active) return;

    const sec = dt / 1000;
    this.x += Math.cos(this.angle) * this.speed * sec;
    this.y += Math.sin(this.angle) * this.speed * sec;

    // Check max range
    const dx = this.x - this.startX;
    const dy = this.y - this.startY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist >= this.maxRange) {
      this.active = false;
    }

    // Check canvas bounds
    if (this.x < 0 || this.x > 640 || this.y < 0 || this.y > 400) {
      this.active = false;
    }
  }

  draw(ctx) {
    if (!this.active) return;
    ctx.fillStyle = '#ffeb3b';
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
    ctx.fill();
  }

  /**
   * @returns {{x:number,y:number,w:number,h:number}}
   */
  getHitbox() {
    return {
      x: this.x - this.radius,
      y: this.y - this.radius,
      w: this.radius * 2,
      h: this.radius * 2
    };
  }
}

// ---------------------------------------------------------------------------
// Animal Class
// ---------------------------------------------------------------------------
class Animal {
  /**
   * @param {string} type - one of: 'rabbit', 'squirrel', 'deer', 'elk', 'bear', 'buffalo'
   * @param {number} x - starting x position (pixels)
   * @param {number} y - starting y position (pixels)
   */
  constructor(type, x, y) {
    this.type = type;
    const data = ANIMAL_DATA[type];

    this.x = x;
    this.y = y;
    this.speed = data.speed;
    this.hitbox_width = data.hitbox_w;
    this.hitbox_height = data.hitbox_h;
    this.food_yield = data.food;
    this.active = true;
    this.sprite_width = data.sprite_w;
    this.sprite_height = data.sprite_h;
    this.color = data.color;
    this.movementPattern = data.movementPattern;

    // Velocity components for free-roaming movement
    this.vx = 0;
    this.vy = 0;
    this._chooseInitialDirection();

    // Movement pattern timers
    this.directionTimer = 0;
    this.directionChangeInterval = this._getDirectionChangeInterval();

    // Death animation state
    this.dead = false;
    this.deadTimer = 0;
    this.deadDuration = 1000; // ms to show upside-down corpse
  }

  _chooseInitialDirection() {
    const angle = Math.random() * Math.PI * 2;
    this.vx = Math.cos(angle) * this.speed;
    this.vy = Math.sin(angle) * this.speed;
  }

  _getDirectionChangeInterval() {
    switch (this.movementPattern) {
      case 'zigzag':   return 400 + Math.random() * 600;   // 0.4 - 1.0s
      case 'graceful': return 1200 + Math.random() * 1500; // 1.2 - 2.7s
      case 'steady':   return 2000 + Math.random() * 2000; // 2.0 - 4.0s
      case 'wander':   return 1500 + Math.random() * 2000; // 1.5 - 3.5s
      default:         return 1000 + Math.random() * 1000;
    }
  }

  /**
   * Update position and handle boundary / direction logic.
   * @param {number} dt - delta time in milliseconds since last frame
   * @param {number} canvasW - canvas width
   * @param {number} canvasH - canvas height
   */
  update(dt, canvasW, canvasH) {
    if (!this.active) return;
    if (this.dead) {
      this.deadTimer -= dt;
      if (this.deadTimer <= 0) {
        this.active = false;
      }
      return;
    }

    const sec = dt / 1000;

    // Update direction timer and potentially change direction
    this.directionTimer += dt;
    if (this.directionTimer >= this.directionChangeInterval) {
      this.directionTimer = 0;
      this.directionChangeInterval = this._getDirectionChangeInterval();
      this._changeDirection();
    }

    // Move
    this.x += this.vx * sec * 60; // normalize to ~60fps scale
    this.y += this.vy * sec * 60;

    // Bounce off edges with a slight margin
    const margin = Math.max(this.sprite_width, this.sprite_height);
    if (this.x < margin) {
      this.x = margin;
      this.vx = Math.abs(this.vx);
    } else if (this.x > canvasW - margin) {
      this.x = canvasW - margin;
      this.vx = -Math.abs(this.vx);
    }

    if (this.y < margin) {
      this.y = margin;
      this.vy = Math.abs(this.vy);
    } else if (this.y > canvasH - margin) {
      this.y = canvasH - margin;
      this.vy = -Math.abs(this.vy);
    }
  }

  _changeDirection() {
    let newAngle;
    switch (this.movementPattern) {
      case 'zigzag': {
        // Sharp random turn
        const currentAngle = Math.atan2(this.vy, this.vx);
        const turn = (Math.random() - 0.5) * Math.PI; // +/- 90 degrees
        newAngle = currentAngle + turn;
        break;
      }
      case 'graceful': {
        // Gentle turn
        const currentAngle = Math.atan2(this.vy, this.vx);
        const turn = (Math.random() - 0.5) * Math.PI * 0.5; // +/- 45 degrees
        newAngle = currentAngle + turn;
        break;
      }
      case 'wander': {
        // Random direction, sometimes biased toward center
        newAngle = Math.random() * Math.PI * 2;
        if (Math.random() < 0.3) {
          // 30% chance to wander toward center of screen (320, 200)
          const dx = 320 - this.x;
          const dy = 200 - this.y;
          newAngle = Math.atan2(dy, dx) + (Math.random() - 0.5) * 0.5;
        }
        break;
      }
      case 'steady':
      default: {
        // Small adjustment to current direction
        const currentAngle = Math.atan2(this.vy, this.vx);
        const turn = (Math.random() - 0.5) * Math.PI * 0.3; // +/- 27 degrees
        newAngle = currentAngle + turn;
        break;
      }
    }

    this.vx = Math.cos(newAngle) * this.speed;
    this.vy = Math.sin(newAngle) * this.speed;
  }

  /**
   * Kill the animal, triggering the upside-down death animation.
   */
  kill() {
    if (this.dead) return;
    this.dead = true;
    this.deadTimer = this.deadDuration;
    this.vx = 0;
    this.vy = 0;
  }

  /**
   * Draw the animal (placeholder colored rectangle).
   * If dead, draws upside-down using ctx.scale(1, -1) or rotate 180°.
   * @param {CanvasRenderingContext2D} ctx
   */
  draw(ctx) {
    if (!this.active) return;

    const drawX = this.x - this.sprite_width / 2;
    const drawY = this.y - this.sprite_height / 2;

    ctx.save();

    if (this.dead) {
      // Upside-down flip death animation (faithful to original)
      // Translate to center, flip, translate back
      ctx.translate(this.x, this.y);
      ctx.scale(1, -1);
      ctx.translate(-this.x, -this.y);
    }

    ctx.fillStyle = this.color;
    ctx.fillRect(drawX, drawY, this.sprite_width, this.sprite_height);

    // Subtle outline so animals pop against the black background
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 1;
    ctx.strokeRect(drawX, drawY, this.sprite_width, this.sprite_height);

    ctx.restore();
  }

  /**
   * Return axis-aligned bounding box for collision detection.
   * Dead animals are removed from hit detection immediately.
   * @returns {{x: number, y: number, w: number, h: number}|null}
   */
  getHitbox() {
    if (this.dead) return null;
    return {
      x: this.x - this.hitbox_width / 2,
      y: this.y - this.hitbox_height / 2,
      w: this.hitbox_width,
      h: this.hitbox_height
    };
  }
}

// ---------------------------------------------------------------------------
// Hunter Helper
// ---------------------------------------------------------------------------
class Hunter {
  /**
   * @param {number} x - x position (center)
   * @param {number} y - y position (center)
   */
  constructor(x, y) {
    this.x = x;
    this.y = y;
    this.width = 20;
    this.height = 20;
    this.aimAngle = -Math.PI / 2; // default aiming up
    this.rifleLength = 24;
  }

  /**
   * Update aim angle toward the given target point, snapped to 8 directions.
   * @param {number} targetX
   * @param {number} targetY
   */
  aimAt(targetX, targetY) {
    const dx = targetX - this.x;
    const dy = targetY - this.y;
    const rawAngle = Math.atan2(dy, dx);
    this.aimAngle = snapTo8Direction(rawAngle);
  }

  /**
   * Get the muzzle position (end of rifle line).
   * @returns {{x:number,y:number}}
   */
  getMuzzlePos() {
    return {
      x: this.x + Math.cos(this.aimAngle) * this.rifleLength,
      y: this.y + Math.sin(this.aimAngle) * this.rifleLength
    };
  }

  draw(ctx) {
    // Draw hunter body as simple colored rectangle
    ctx.fillStyle = '#2e7d32'; // greenish pioneer coat
    ctx.fillRect(
      this.x - this.width / 2,
      this.y - this.height / 2,
      this.width,
      this.height
    );

    // Draw rifle direction line
    ctx.strokeStyle = '#5d4037'; // brown rifle
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(this.x, this.y);
    const muzzle = this.getMuzzlePos();
    ctx.lineTo(muzzle.x, muzzle.y);
    ctx.stroke();

    // Draw hat (small rectangle on top)
    ctx.fillStyle = '#8d6e63';
    ctx.fillRect(
      this.x - this.width / 2 - 2,
      this.y - this.height / 2 - 4,
      this.width + 4,
      4
    );
  }
}

// ---------------------------------------------------------------------------
// HuntingGame Class (Game Controller)
// ---------------------------------------------------------------------------
class HuntingGame {
  /**
   * @param {HTMLCanvasElement} canvas - the canvas element to render on
   */
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');

    // Canvas dimensions (fixed 640x400)
    this.width = 640;
    this.height = 400;
    this.canvas.width = this.width;
    this.canvas.height = this.height;

    // Terrain system (authentic 1985 zone-based obstacles)
    this.terrain = new TerrainSystem(this.width, this.height);
    this.terrain.generate();

    // Sprite renderer (Apple II aesthetic pixel art)
    this.spriteRenderer = new SpriteRenderer(this.ctx);

    // Game entities & state
    this.animals = [];
    this.bullets = [];
    this.hunter = new Hunter(this.width / 2, this.height - 40);

    this.score = 0;
    this.totalKilledWeight = 0; // sum of all animal food yields hit
    this.foodCarriedBack = 0;
    this.shotsFired = 0;
    this.shotsHit = 0;
    this.gameTime = 0;
    this.running = false;
    this.ended = false;

    // Hunt timer (daylight) - 30 to 45 seconds
    this.huntDuration = 35000; // ms (35s default)
    this.huntTimer = this.huntDuration;

    // Terrain zone
    this.currentZone = null;
    this.zoneAnimalTypes = null; // subset of animals for current zone

    // Spawning state
    this.spawnTimer = 0;
    this.baseSpawnInterval = 1200; // ms

    // Crosshair state (modern QoL, kept alongside hunter aim)
    this.crosshair = { x: this.width / 2, y: this.height / 2 };
    this.crosshairSize = 12;

    // Muzzle flash state
    this.flash = {
      active: false,
      timer: 0,
      duration: 80, // ms
      x: 0,
      y: 0
    };

    // Results screen state
    this.showResults = false;
    this.resultsTimer = 0;

    // Timing
    this.lastTimestamp = 0;
    this.rafId = null;

    // Bind input
    this._bindEvents();
  }

  /** Set the terrain zone, which determines eligible animal spawns. */
  setZone(zoneName) {
    this.terrain.setZone(zoneName);
    this.currentZone = zoneName;
    this.zoneAnimalTypes = this.terrain.getEligibleAnimals();
  }

  /** Get the list of animal types that can currently spawn. */
  _getSpawnableAnimalTypes() {
    const fromTerrain = this.terrain.getEligibleAnimals();
    if (fromTerrain && fromTerrain.length > 0) {
      return fromTerrain;
    }
    if (this.zoneAnimalTypes) {
      return this.zoneAnimalTypes;
    }
    return Object.keys(ANIMAL_DATA);
  }

  /** Attach mousemove and click listeners. */
  _bindEvents() {
    this._onMouseMove = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;
      this.crosshair.x = (e.clientX - rect.left) * scaleX;
      this.crosshair.y = (e.clientY - rect.top) * scaleY;
    };

    this._onClick = () => {
      if (!this.running || this.ended) return;
      this._fireShot();
    };

    this.canvas.addEventListener('mousemove', this._onMouseMove);
    this.canvas.addEventListener('click', this._onClick);
  }

  /** Fire a shot, spawn bullet from hunter muzzle toward aim direction, trigger flash. */
  _fireShot() {
    this.shotsFired++;

    // Update hunter aim to current crosshair position
    this.hunter.aimAt(this.crosshair.x, this.crosshair.y);

    // Spawn bullet from muzzle
    const muzzle = this.hunter.getMuzzlePos();
    const bullet = new Bullet(
      muzzle.x,
      muzzle.y,
      this.hunter.aimAngle,
      700, // bullet speed (px/sec)
      550  // max range (px)
    );
    this.bullets.push(bullet);

    // Activate muzzle flash at hunter muzzle position
    this.flash.active = true;
    this.flash.timer = this.flash.duration;
    this.flash.x = muzzle.x;
    this.flash.y = muzzle.y;
  }

  /** Start the game loop. */
  start() {
    if (this.running) return;
    this.running = true;
    this.ended = false;
    this.showResults = false;
    this.huntTimer = this.huntDuration;
    this.lastTimestamp = performance.now();
    this.rafId = requestAnimationFrame((ts) => this.gameLoop(ts));
  }

  /** Stop the game loop. */
  stop() {
    this.running = false;
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  /**
   * Main requestAnimationFrame loop.
   * @param {number} timestamp - high-res time from requestAnimationFrame
   */
  gameLoop(timestamp) {
    if (!this.running) return;

    const dt = timestamp - this.lastTimestamp;
    this.lastTimestamp = timestamp;

    this.update(dt);
    this.draw();

    this.rafId = requestAnimationFrame((ts) => this.gameLoop(ts));
  }

  /**
   * Update all game state.
   * @param {number} dt - delta time in ms
   */
  update(dt) {
    if (this.ended) {
      if (this.showResults) {
        this.resultsTimer -= dt;
        if (this.resultsTimer <= 0) {
          this.showResults = false;
          this.stop();
        }
      }
      return;
    }

    this.gameTime += dt;

    // Update hunt timer
    this.huntTimer -= dt;
    if (this.huntTimer <= 0) {
      this.huntTimer = 0;
      this._endHunt();
      return;
    }

    // Spawn new animals on a randomized timer
    this.spawnTimer -= dt;
    if (this.spawnTimer <= 0) {
      this._spawnAnimal();
      // Spawn rate increases slightly as timer runs low
      const urgency = 1 - (this.huntTimer / this.huntDuration);
      const interval = this.baseSpawnInterval * (1 - urgency * 0.4);
      this.spawnTimer = interval * 0.6 + Math.random() * interval * 0.8;
    }

    // Update hunter aim toward crosshair
    this.hunter.aimAt(this.crosshair.x, this.crosshair.y);

    // Update bullets
    for (const bullet of this.bullets) {
      bullet.update(dt);
    }
    this.bullets = this.bullets.filter(b => b.active);

    // Update animal positions
    for (const animal of this.animals) {
      animal.update(dt, this.width, this.height);
    }

    // Bullet vs Animal hit detection
    this._checkBulletHits();

    // Remove inactive animals (including finished death animations)
    this.animals = this.animals.filter(a => a.active);

    // Decay muzzle flash
    if (this.flash.active) {
      this.flash.timer -= dt;
      if (this.flash.timer <= 0) {
        this.flash.active = false;
      }
    }
  }

  /** Check all active bullets against all live animals for AABB collisions. */
  _checkBulletHits() {
    for (const bullet of this.bullets) {
      if (!bullet.active) continue;

      const bulletBox = bullet.getHitbox();
      for (const animal of this.animals) {
        if (!animal.active || animal.dead) continue;

        const animalBox = animal.getHitbox();
        if (animalBox && aabbIntersect(bulletBox, animalBox)) {
          // Hit!
          bullet.active = false;
          this.shotsHit++;
          this.totalKilledWeight += animal.food_yield;

          // Apply 100 lb carry limit
          const previousCarried = this.foodCarriedBack;
          this.foodCarriedBack = Math.min(this.totalKilledWeight, 100);

          // Score tracks carried food (or could track total kills)
          this.score = this.foodCarriedBack;

          animal.kill();
          break; // bullet can only hit one animal
        }
      }
    }
  }

  /** End the hunt, compute final results, and show results screen. */
  _endHunt() {
    this.ended = true;
    this.showResults = true;
    this.resultsTimer = 4000; // show results for 4 seconds
  }

  /** Create a new animal entering from a random edge. */
  _spawnAnimal() {
    const types = this._getSpawnableAnimalTypes();
    if (types.length === 0) return;

    const type = types[Math.floor(Math.random() * types.length)];
    const data = ANIMAL_DATA[type];
    const margin = Math.max(data.sprite_w, data.hitbox_w);

    // Pick a random edge: 0=top, 1=right, 2=bottom, 3=left
    const edge = Math.floor(Math.random() * 4);
    let x, y;

    switch (edge) {
      case 0: // top
        x = margin + Math.random() * (this.width - margin * 2);
        y = -margin;
        break;
      case 1: // right
        x = this.width + margin;
        y = margin + Math.random() * (this.height - margin * 2);
        break;
      case 2: // bottom
        x = margin + Math.random() * (this.width - margin * 2);
        y = this.height + margin;
        break;
      case 3: // left
      default:
        x = -margin;
        y = margin + Math.random() * (this.height - margin * 2);
        break;
    }

    const animal = new Animal(type, x, y);
    // Aim roughly toward center so animals don't immediately leave
    const dx = (this.width / 2) - x;
    const dy = (this.height / 2) - y;
    const angle = Math.atan2(dy, dx) + (Math.random() - 0.5) * 1.0;
    animal.vx = Math.cos(angle) * animal.speed;
    animal.vy = Math.sin(angle) * animal.speed;

    this.animals.push(animal);
  }

  // -------------------------------------------------------------------------
  // Drawing
  // -------------------------------------------------------------------------

  /** Full frame render. */
  draw() {
    const ctx = this.ctx;

    // Black background (faithful to original)
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, this.width, this.height);

    // Draw terrain objects (procedural pixel-art)
    this.terrain.draw(ctx);

    // Draw animals using pixel-art sprites
    for (const animal of this.animals) {
      const facingRight = animal.vx >= 0;
      this.spriteRenderer.drawAnimal(animal.type, animal.x, animal.y, facingRight, animal.dead);
    }

    // Draw bullets
    for (const bullet of this.bullets) {
      bullet.draw(ctx);
    }

    // Draw hunter sprite (8-directional)
    this.spriteRenderer.drawHunter(this.hunter.x, this.hunter.y, this.hunter.aimAngle, true);

    this._drawCrosshair(ctx);

    if (this.flash.active) {
      this._drawMuzzleFlash(ctx);
    }

    this._drawHUD(ctx);

    if (this.showResults) {
      this._drawResultsScreen(ctx);
    }
  }

  /** Classic yellow crosshair with drop-shadow for visibility. */
  _drawCrosshair(ctx) {
    const { x, y } = this.crosshair;
    const size = this.crosshairSize;

    ctx.strokeStyle = '#ffeb3b';
    ctx.lineWidth = 2;
    ctx.shadowColor = '#000';
    ctx.shadowBlur = 4;

    // Horizontal
    ctx.beginPath();
    ctx.moveTo(x - size, y);
    ctx.lineTo(x + size, y);
    ctx.stroke();

    // Vertical
    ctx.beginPath();
    ctx.moveTo(x, y - size);
    ctx.lineTo(x, y + size);
    ctx.stroke();

    // Outer circle
    ctx.beginPath();
    ctx.arc(x, y, size * 0.6, 0, Math.PI * 2);
    ctx.stroke();

    // Center dot
    ctx.fillStyle = '#ffeb3b';
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fill();

    ctx.shadowBlur = 0;
  }

  /** Expanding orange/yellow flash that fades over its duration. */
  _drawMuzzleFlash(ctx) {
    const { x, y } = this.flash;
    const progress = 1 - this.flash.timer / this.flash.duration;
    const radius = 10 + progress * 30;
    const alpha = 1 - progress;

    ctx.save();
    ctx.globalAlpha = alpha;

    ctx.fillStyle = '#ff9800';
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#fff176';
    ctx.beginPath();
    ctx.arc(x, y, radius * 0.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  /** HUD showing food carried, timer, and shots. */
  _drawHUD(ctx) {
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 14px monospace';
    ctx.textAlign = 'left';
    ctx.shadowColor = '#000';
    ctx.shadowBlur = 3;

    // Food carried (respecting 100 lb limit)
    ctx.fillText(`Food: ${this.foodCarriedBack} / 100 lb`, 10, 22);

    // Timer
    const secondsLeft = Math.ceil(this.huntTimer / 1000);
    ctx.fillText(`Time: ${secondsLeft}s`, 10, 42);

    // Shot accuracy
    ctx.fillText(`Hits: ${this.shotsHit} / ${this.shotsFired}`, 10, 62);

    // Zone name (if set)
    if (this.currentZone) {
      const zoneDisplay = this.currentZone.replace(/_/g, ' ');
      ctx.fillText(`Zone: ${zoneDisplay}`, 10, 82);
    }

    ctx.shadowBlur = 0;
  }

  /** Results screen shown at end of hunt. */
  _drawResultsScreen(ctx) {
    // Dark overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
    ctx.fillRect(0, 0, this.width, this.height);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 20px monospace';
    ctx.textAlign = 'center';
    ctx.shadowColor = '#000';
    ctx.shadowBlur = 4;

    const cx = this.width / 2;
    let y = 140;

    ctx.fillText('Hunt Over', cx, y);
    y += 36;

    ctx.font = '14px monospace';
    ctx.fillText(`Total killed: ${this.totalKilledWeight} lb of meat`, cx, y);
    y += 26;

    ctx.fillText(`Food carried back: ${this.foodCarriedBack} lb`, cx, y);
    y += 26;

    if (this.totalKilledWeight > 100) {
      ctx.fillStyle = '#ffab91';
      ctx.fillText('However, you were only able to carry 100 pounds back to the wagon.', cx, y);
      y += 26;
    }

    ctx.fillStyle = '#ffffff';
    ctx.fillText(`Shots: ${this.shotsHit} / ${this.shotsFired} hit`, cx, y);
    y += 36;

    ctx.fillText('Closing...', cx, y);

    ctx.shadowBlur = 0;
    ctx.textAlign = 'left';
  }

  // -------------------------------------------------------------------------
  // Utility / Teardown
  // -------------------------------------------------------------------------

  /**
   * Return the current session results.
   * @returns {{foodGained: number, totalKilledWeight: number, foodCarriedBack: number, score: number, shotsFired: number, shotsHit: number, accuracy: number, wasted: boolean, zone: string|null}}
   */
  getResults() {
    return {
      foodGained: this.foodCarriedBack,
      totalKilledWeight: this.totalKilledWeight,
      foodCarriedBack: this.foodCarriedBack,
      score: this.score,
      shotsFired: this.shotsFired,
      shotsHit: this.shotsHit,
      accuracy: this.shotsFired > 0 ? this.shotsHit / this.shotsFired : 0,
      wasted: this.totalKilledWeight > 100,
      zone: this.currentZone
    };
  }

  /** Clean up event listeners and stop the loop. */
  destroy() {
    this.stop();
    this.canvas.removeEventListener('mousemove', this._onMouseMove);
    this.canvas.removeEventListener('click', this._onClick);
  }
}

// ---------------------------------------------------------------------------
// Module Exports
// ---------------------------------------------------------------------------
export { HuntingGame, Animal };
