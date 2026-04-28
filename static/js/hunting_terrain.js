/**
 * hunting_terrain.js
 *
 * Terrain and obstacle system for the Oregon Trail hunting mini-game.
 * Procedurally draws 4-6 terrain objects per hunt based on the active zone.
 * Objects act as obstacles (AABB collision) and optionally block line-of-sight.
 *
 * Zones and eligible objects/animals are faithful to the original 1985 design.
 */

// ---------------------------------------------------------------------------
// Zone definitions
// ---------------------------------------------------------------------------
export const ZONES = {
  eastern_forest: {
    objects: ["deciduous_tree", "grass_tuft"],
    animals: ["squirrel", "rabbit", "deer"]
  },
  plains: {
    objects: ["grass_tuft"],
    animals: ["rabbit", "deer", "buffalo"]
  },
  rocky_mountains: {
    objects: ["coniferous_tree", "rock"],
    animals: ["deer", "elk", "bear"]
  },
  desert: {
    objects: ["cactus", "desert_shrub", "rock"],
    animals: ["rabbit", "squirrel"]
  },
  western_forest: {
    objects: ["coniferous_tree"],
    animals: ["deer", "elk", "bear"]
  }
};

// ---------------------------------------------------------------------------
// Drawing helpers (procedural Canvas 2D graphics)
// ---------------------------------------------------------------------------

/**
 * Draw a deciduous tree: brown trunk with a rounded green canopy.
 */
function drawDeciduousTree(ctx, x, y, w, h, variant) {
  const trunkW = w * 0.25;
  const trunkH = h * 0.4;
  const canopyR = Math.max(w, h) * 0.35;

  ctx.save();
  // Trunk
  ctx.fillStyle = "#5C3A1E";
  ctx.fillRect(x + w / 2 - trunkW / 2, y + h - trunkH, trunkW, trunkH);

  // Canopy
  ctx.fillStyle = variant === 1 ? "#4A7A3A" : variant === 2 ? "#6BA855" : "#3E6B30";
  ctx.beginPath();
  ctx.arc(x + w / 2, y + h - trunkH, canopyR, 0, Math.PI * 2);
  ctx.fill();

  // Extra detail: secondary blob for fullness
  ctx.beginPath();
  ctx.arc(x + w / 2 - canopyR * 0.4, y + h - trunkH + canopyR * 0.2, canopyR * 0.7, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(x + w / 2 + canopyR * 0.4, y + h - trunkH + canopyR * 0.2, canopyR * 0.7, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/**
 * Draw a coniferous / pine tree: brown trunk with layered green triangles.
 */
function drawConiferousTree(ctx, x, y, w, h, variant) {
  const trunkW = w * 0.2;
  const trunkH = h * 0.25;
  const layers = variant === 0 ? 3 : variant === 1 ? 4 : 2;
  const baseWidth = w * 0.9;
  const layerHeight = (h - trunkH) / layers;

  ctx.save();
  // Trunk
  ctx.fillStyle = "#4A3020";
  ctx.fillRect(x + w / 2 - trunkW / 2, y + h - trunkH, trunkW, trunkH);

  // Foliage layers
  ctx.fillStyle = variant === 1 ? "#2E5E3E" : variant === 2 ? "#3A7A50" : "#1F4D33";
  for (let i = 0; i < layers; i++) {
    const topY = y + i * layerHeight;
    const bottomY = y + (i + 1) * layerHeight;
    const lw = baseWidth * (1 - i / layers);
    ctx.beginPath();
    ctx.moveTo(x + w / 2, topY);
    ctx.lineTo(x + w / 2 - lw / 2, bottomY);
    ctx.lineTo(x + w / 2 + lw / 2, bottomY);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}

/**
 * Draw a tuft of grass: thin vertical blades.
 */
function drawGrassTuft(ctx, x, y, w, h, variant) {
  const bladeCount = variant === 0 ? 5 : variant === 1 ? 7 : 4;
  const colors = ["#6DA855", "#8FBC65", "#558B40"];

  ctx.save();
  for (let i = 0; i < bladeCount; i++) {
    const bx = x + (w / bladeCount) * i + w / bladeCount / 2;
    const bh = h * (0.6 + Math.random() * 0.5); // slight randomness per draw
    ctx.strokeStyle = colors[variant % colors.length];
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(bx, y + h);
    ctx.quadraticCurveTo(bx + (i % 2 === 0 ? 2 : -2), y + h - bh / 2, bx, y + h - bh);
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * Draw a desert shrub: sparse, scraggly branches.
 */
function drawDesertShrub(ctx, x, y, w, h, variant) {
  const branchCount = variant === 0 ? 4 : variant === 1 ? 6 : 5;
  ctx.save();
  ctx.strokeStyle = variant === 2 ? "#8B7355" : "#7A6545";
  ctx.lineWidth = 2;
  for (let i = 0; i < branchCount; i++) {
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * 1.2;
    const len = (h * 0.4) + Math.random() * (h * 0.5);
    const sx = x + w / 2;
    const sy = y + h;
    const ex = sx + Math.cos(angle) * len;
    const ey = sy + Math.sin(angle) * len;
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(ex, ey);
    ctx.stroke();

    // tiny leaf dots
    ctx.fillStyle = "#A0A060";
    ctx.beginPath();
    ctx.arc(ex, ey, 1.5, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

/**
 * Draw a cactus: upright green column with optional arm.
 */
function drawCactus(ctx, x, y, w, h, variant) {
  const bodyW = w * 0.35;
  const bodyH = h * 0.85;
  const bodyX = x + w / 2 - bodyW / 2;
  const bodyY = y + h - bodyH;

  ctx.save();
  ctx.fillStyle = variant === 1 ? "#6B8E23" : "#4A7A30";

  // Main column
  ctx.beginPath();
  ctx.roundRect(bodyX, bodyY, bodyW, bodyH, bodyW / 2);
  ctx.fill();

  // Arm(s)
  if (variant !== 2) {
    const armW = bodyW * 0.5;
    const armH = bodyH * 0.35;
    const armX = variant === 0 ? bodyX + bodyW - armW / 2 : bodyX - armW / 2;
    const armY = bodyY + bodyH * 0.35;

    // Horizontal stub
    ctx.beginPath();
    ctx.roundRect(armX, armY, armW + bodyW * 0.15, armW, armW / 2);
    ctx.fill();
    // Vertical tip
    ctx.beginPath();
    ctx.roundRect(armX + (variant === 0 ? armW : -armW / 2), armY - armH + armW, armW, armH, armW / 2);
    ctx.fill();
  }

  // Spine dots
  ctx.fillStyle = "#D0D0A0";
  for (let i = 0; i < 6; i++) {
    const sx = bodyX + bodyW * 0.2 + Math.random() * bodyW * 0.6;
    const sy = bodyY + bodyH * 0.1 + Math.random() * bodyH * 0.8;
    ctx.beginPath();
    ctx.arc(sx, sy, 1, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

/**
 * Draw a rock: grey irregular blob.
 */
function drawRock(ctx, x, y, w, h, variant) {
  ctx.save();
  const grey = variant === 0 ? "#888888" : variant === 1 ? "#777777" : "#999999";
  ctx.fillStyle = grey;
  ctx.beginPath();
  ctx.ellipse(x + w / 2, y + h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
  ctx.fill();

  // Highlight
  ctx.fillStyle = "#AAAAAA";
  ctx.beginPath();
  ctx.ellipse(x + w * 0.35, y + h * 0.4, w * 0.2, h * 0.15, -0.3, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/**
 * Dispatch table mapping object type string to drawer function.
 */
const DRAWERS = {
  deciduous_tree: drawDeciduousTree,
  coniferous_tree: drawConiferousTree,
  grass_tuft: drawGrassTuft,
  desert_shrub: drawDesertShrub,
  cactus: drawCactus,
  rock: drawRock
};

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randFloat(min, max) {
  return Math.random() * (max - min) + min;
}

/**
 * Check if two axis-aligned bounding boxes overlap.
 */
function aabbOverlap(x1, y1, w1, h1, x2, y2, w2, h2) {
  return x1 < x2 + w2 && x1 + w1 > x2 && y1 < y2 + h2 && y1 + h1 > y2;
}

/**
 * Check if line segment (x1,y1)-(x2,y2) intersects rectangle (rx,ry,rw,rh).
 * Uses Liang-Barsky parametric clipping.
 */
function lineIntersectsRect(x1, y1, x2, y2, rx, ry, rw, rh) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const p = [-dx, dx, -dy, dy];
  const q = [x1 - rx, rx + rw - x1, y1 - ry, ry + rh - y1];
  let u1 = 0;
  let u2 = 1;

  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) return false;
    } else {
      const t = q[i] / p[i];
      if (p[i] < 0) {
        u1 = Math.max(u1, t);
      } else {
        u2 = Math.min(u2, t);
      }
    }
  }

  return u1 <= u2;
}

// ---------------------------------------------------------------------------
// TerrainSystem class
// ---------------------------------------------------------------------------

export class TerrainSystem {
  /**
   * @param {number} canvasWidth
   * @param {number} canvasHeight
   */
  constructor(canvasWidth, canvasHeight) {
    this.canvasWidth = canvasWidth;
    this.canvasHeight = canvasHeight;
    this.zone = "plains";
    this.objects = [];

    // Hunter spawn safe zone: bottom-center area where objects should not clutter
    this.safeZone = {
      x: canvasWidth * 0.25,
      y: canvasHeight * 0.65,
      w: canvasWidth * 0.5,
      h: canvasHeight * 0.35
    };
  }

  /**
   * Set the active terrain zone.
   * @param {string} zoneName - one of the keys in ZONES
   */
  setZone(zoneName) {
    if (!ZONES[zoneName]) {
      console.warn(`Unknown zone "${zoneName}", defaulting to plains.`);
      this.zone = "plains";
    } else {
      this.zone = zoneName;
    }
  }

  /**
   * Generate 4-6 random terrain objects for a new hunt.
   * Clears existing objects. Objects avoid the hunter safe zone and each other.
   */
  generate() {
    this.objects = [];
    const zoneDef = ZONES[this.zone];
    const eligibleTypes = zoneDef.objects;
    if (!eligibleTypes || eligibleTypes.length === 0) return;

    const count = randInt(4, 6);
    const maxAttempts = 200;

    for (let i = 0; i < count; i++) {
      let placed = false;
      let attempts = 0;

      while (!placed && attempts < maxAttempts) {
        attempts++;
        const type = eligibleTypes[randInt(0, eligibleTypes.length - 1)];
        const obj = this._createObject(type);

        if (this._isValidPosition(obj)) {
          this.objects.push(obj);
          placed = true;
        }
      }
    }
  }

  /**
   * Create a single terrain object descriptor.
   * @param {string} type
   * @returns {Object}
   */
  _createObject(type) {
    let w, h;
    switch (type) {
      case "deciduous_tree":
      case "coniferous_tree":
        w = randInt(30, 50);
        h = randInt(30, 50);
        break;
      case "rock":
        w = randInt(15, 25);
        h = randInt(15, 25);
        break;
      case "grass_tuft":
        w = randInt(10, 15);
        h = randInt(10, 15);
        break;
      case "cactus":
        w = randInt(18, 28);
        h = randInt(35, 50);
        break;
      case "desert_shrub":
        w = randInt(20, 35);
        h = randInt(15, 25);
        break;
      default:
        w = 20;
        h = 20;
    }

    const x = randInt(0, this.canvasWidth - w);
    const y = randInt(0, this.canvasHeight - h);
    const variant = randInt(0, 2); // 3 variants per type

    return { type, x, y, w, h, variant };
  }

  /**
   * Verify that an object does not overlap the hunter safe zone or other objects.
   * @param {Object} obj
   * @returns {boolean}
   */
  _isValidPosition(obj) {
    // Avoid hunter start area (with a small margin)
    const margin = 10;
    if (
      aabbOverlap(
        obj.x - margin,
        obj.y - margin,
        obj.w + margin * 2,
        obj.h + margin * 2,
        this.safeZone.x,
        this.safeZone.y,
        this.safeZone.w,
        this.safeZone.h
      )
    ) {
      return false;
    }

    // Avoid overlapping other objects (with margin)
    for (const other of this.objects) {
      if (
        aabbOverlap(
          obj.x - margin,
          obj.y - margin,
          obj.w + margin * 2,
          obj.h + margin * 2,
          other.x,
          other.y,
          other.w,
          other.h
        )
      ) {
        return false;
      }
    }

    return true;
  }

  /**
   * Draw all terrain objects onto the canvas.
   * @param {CanvasRenderingContext2D} ctx
   */
  draw(ctx) {
    for (const obj of this.objects) {
      const drawer = DRAWERS[obj.type];
      if (drawer) {
        drawer(ctx, obj.x, obj.y, obj.w, obj.h, obj.variant);
      }
    }
  }

  /**
   * Check if the given bounding box collides with any terrain obstacle.
   * @param {number} x
   * @param {number} y
   * @param {number} width
   * @param {number} height
   * @returns {boolean}
   */
  checkCollision(x, y, width, height) {
    for (const obj of this.objects) {
      if (aabbOverlap(x, y, width, height, obj.x, obj.y, obj.w, obj.h)) {
        return true;
      }
    }
    return false;
  }

  /**
   * Return the list of animal names valid for the current zone.
   * @returns {string[]}
   */
  getEligibleAnimals() {
    const zoneDef = ZONES[this.zone];
    return zoneDef ? [...zoneDef.animals] : [];
  }

  /**
   * Check whether the line segment between two points is blocked by any terrain object.
   * Useful for authentic line-of-sight bullet blocking.
   * @param {number} x1
   * @param {number} y1
   * @param {number} x2
   * @param {number} y2
   * @returns {boolean}
   */
  blocksLineOfSight(x1, y1, x2, y2) {
    for (const obj of this.objects) {
      if (lineIntersectsRect(x1, y1, x2, y2, obj.x, obj.y, obj.w, obj.h)) {
        return true;
      }
    }
    return false;
  }
}
