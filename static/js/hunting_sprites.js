/**
 * Oregon Trail Hunting Mini-Game Sprite Renderer
 * Apple II 1985 aesthetic: 6-color palette, pixel-art drawn with fillRect.
 */

// ── Palette ──────────────────────────────────────────────────────────
const PALETTE = {
  ' ': null,              // transparent
  'k': '#0a0a0a',         // background black
  'w': '#ffffff',         // white
  'o': '#ff851b',         // orange
  'g': '#2ecc40',         // green
  'G': '#4af626',         // terminal green
  'p': '#6c2d9f',         // purple
  'b': '#0074d9',         // blue
  'r': '#999999',         // rock grey (extra, used sparingly)
};

// ── Sprite Definitions (arrays of strings, top-to-bottom) ────────────

const ANIMALS = {
  // Squirrel (12×8) — orange with fluffy tail
  squirrel: [
    '  ooo       ',
    ' ooooo      ',
    ' ooooo      ',
    '  ooo  oo   ',
    '   o   oo   ',
    '       o    ',
    '      oo    ',
    '            ',
  ],

  // Rabbit (14×10) — white with long ears
  rabbit: [
    '    ww        ',
    '    ww        ',
    '    ww        ',
    '   wwww  ww   ',
    '   wwww  ww   ',
    '   wwwwwwww   ',
    '    wwwwww    ',
    '    wwwwww    ',
    '     w  w     ',
    '     w  w     ',
  ],

  // Deer (32×20) — graceful orange with tiny antlers
  deer: [
    '                               ',
    '           oo  oo              ',
    '           oooooo              ',
    '           oooooo              ',
    '            oooo               ',
    '            oooo               ',
    '           oooooo              ',
    '           oooooo              ',
    '            oooo               ',
    '            oooo               ',
    '            oooo        ooo    ',
    '           oooooo     oooooo   ',
    '          oooooooo   oooooooo  ',
    '         oooooooooo oooooooooo ',
    '        ooooooooooooooooooooooo',
    '       oooooooooooooooooooooooo',
    '      ooooooooooooooooooooooooo',
    '     oooooooooooooooooooooooooo',
    '    oooo      oooo      oooo   ',
    '    oo        oo        oo     ',
  ],

  // Elk (40×24) — larger, heavier antlers
  elk: [
    '                                        ',
    '              oooo    oooo              ',
    '              oooo    oooo              ',
    '             oooooo  oooooo             ',
    '             oooooo  oooooo             ',
    '            oooooooooooooooo            ',
    '            oooooooooooooooo            ',
    '             oooooooooooooo             ',
    '             oooooooooooooo             ',
    '              oooooooooooo              ',
    '               oooooooooo               ',
    '               oooooooooo               ',
    '               oooooooooo               ',
    '              oooooooooooo              ',
    '             oooooooooooooo             ',
    '            oooooooooooooooo            ',
    '           oooooooooooooooooo           ',
    '          oooooooooooooooooooo          ',
    '         oooooooooooooooooooooo         ',
    '        oooooooooooooooooooooooo        ',
    '       oooooooooooooooooooooooooo       ',
    '      oooooooooooooooooooooooooooo      ',
    '     oooo      oooooooo      oooo     ',
    '     oooo      oooooooo      oooo     ',
  ],

  // Bear (38×26) — bulky orange-brown
  bear: [
    '                                      ',
    '        oooooo     oooooo             ',
    '       oooooooo   oooooooo            ',
    '       oooooooo   oooooooo            ',
    '        oooooo     oooooo             ',
    '         oooo       oooo              ',
    '         oooo       oooo              ',
    '        oooooo     oooooo             ',
    '       oooooooo   oooooooo            ',
    '      oooooooooo oooooooooo           ',
    '     ooooooooooooooooooooooo          ',
    '    ooooooooooooooooooooooooo         ',
    '   ooooooooooooooooooooooooooo        ',
    '  ooooooooooooooooooooooooooooo       ',
    ' ooooooooooooooooooooooooooooooo      ',
    ' ooooooooooooooooooooooooooooooo      ',
    ' ooooooooooooooooooooooooooooooo      ',
    '  ooooooooooooooooooooooooooooo       ',
    '   ooooooooooooooooooooooooooo        ',
    '    ooooooooooooooooooooooooo         ',
    '     ooooooooooooooooooooooo          ',
    '      ooooooooooooooooooooo           ',
    '       ooooooooooooooooooo            ',
    '       oooo          oooo             ',
    '       oooo          oooo             ',
    '       oooo          oooo             ',
  ],

  // Buffalo (48×28) — massive hump, dark brown/orange
  buffalo: [
    '                                                ',
    '                                                ',
    '                  oooooooo                      ',
    '                 oooooooooo                     ',
    '                oooooooooooo                    ',
    '               oooooooooooooo                   ',
    '              oooooooooooooooo                  ',
    '             oooooooooooooooooo                 ',
    '            oooooooooooooooooooo                ',
    '           oooooooooooooooooooooo               ',
    '          oooooooooooooooooooooooo              ',
    '         oooooooooooooooooooooooooo             ',
    '        oooooooooooooooooooooooooooo            ',
    '       oooooooooooooooooooooooooooooo           ',
    '      oooooooooooooooooooooooooooooooo          ',
    '     oooooooooooooooooooooooooooooooooo         ',
    '    oooooooooooooooooooooooooooooooooooo        ',
    '   oooooooooooooooooooooooooooooooooooooo       ',
    '  oooooooooooooooooooooooooooooooooooooooo      ',
    ' oooooooooooooooooooooooooooooooooooooooooo     ',
    ' oooooooooooooooooooooooooooooooooooooooooo     ',
    ' oooooooooooooooooooooooooooooooooooooooooo     ',
    ' oooooooo  oooooooooooooooooooo  oooooooo     ',
    ' oooooo    oooooooooooooooooooo    oooooo     ',
    ' oooo      oooooooooooooooooooo      oooo     ',
    ' oooo      oooooooooooooooooooo      oooo     ',
    ' oooo      oooooooooooooooooooo      oooo     ',
    ' oooo      oooooooooooooooooooo      oooo     ',
  ],
};

// Hunter 16×16 for 8 compass directions (0=E, 1=SE, 2=S, 3=SW, 4=W, 5=NW, 6=N, 7=NE)
// Characters: w=white, o=orange, G=terminal green, b=blue (rifle barrel)
const HUNTERS = [
  // 0 — facing RIGHT (east)
  [
    '                ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '     oooooo     ',
    '      oooo      ',
    '      oooo      ',
    '    bbbbbbbb    ',
    '      oooo      ',
    '      oooo      ',
  ],
  // 1 — facing DOWN-RIGHT (south-east)
  [
    '                ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '      oooo      ',
    '      oooo      ',
    '       oo       ',
    '       oo  bb   ',
    '       oo   bb  ',
    '       oo       ',
  ],
  // 2 — facing DOWN (south)
  [
    '                ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '     oooooo     ',
    '      oooo      ',
    '      oooo      ',
    '      oooo      ',
    '      oooo      ',
    '      oooo      ',
  ],
  // 3 — facing DOWN-LEFT (south-west)
  [
    '                ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '      oooo      ',
    '      oooo      ',
    '       oo       ',
    '   bb  oo       ',
    '  bb   oo       ',
    '       oo       ',
  ],
  // 4 — facing LEFT (west)  — mirror of 0
  [
    '                ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '     oooooo     ',
    '      oooo      ',
    '      oooo      ',
    '    bbbbbbbb    ',
    '      oooo      ',
    '      oooo      ',
  ],
  // 5 — facing UP-LEFT (north-west)
  [
    '       oo       ',
    '   bb  oo       ',
    '  bb   oo       ',
    '       oo       ',
    '      oooo      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '      oooo      ',
    '      oooo      ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
  ],
  // 6 — facing UP (north)
  [
    '      oooo      ',
    '      oooo      ',
    '      oooo      ',
    '      oooo      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '     oooooo     ',
    '      oooo      ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
    '                ',
  ],
  // 7 — facing UP-RIGHT (north-east)
  [
    '       oo       ',
    '       oo  bb   ',
    '       oo   bb  ',
    '       oo       ',
    '      oooo      ',
    '      oooo      ',
    '     oooooo     ',
    '    oooooooo    ',
    '    oooooooo    ',
    '     oooooo     ',
    '      oooo      ',
    '      oooo      ',
    '      wwww      ',
    '     wwwwww     ',
    '     wwwwww     ',
    '      wwww      ',
  ],
];

const TERRAIN = {
  // Deciduous Tree (24×32) — rounded green canopy, orange trunk
  deciduous: [
    '                        ',
    '         gggg           ',
    '       gggggggg         ',
    '      gggggggggg        ',
    '     gggggggggggg       ',
    '    gggggggggggggg      ',
    '   gggggggggggggggg     ',
    '   gggggggggggggggg     ',
    '  gggggggggggggggggg    ',
    '  gggggggggggggggggg    ',
    '  gggggggggggggggggg    ',
    ' gggggggggggggggggggg   ',
    ' gggggggggggggggggggg   ',
    ' gggggggggggggggggggg   ',
    ' gggggggggggggggggggg   ',
    '  gggggggggggggggggg    ',
    '  gggggggggggggggggg    ',
    '   gggggggggggggggg     ',
    '    gggggggggggggg      ',
    '     gggggggggggg       ',
    '       gggggggg         ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '         oooo           ',
    '                        ',
  ],

  // Coniferous Tree (20×36) — triangular pine
  coniferous: [
    '                    ',
    '         G          ',
    '        GGG         ',
    '       GGGGG        ',
    '      GGGGGGG       ',
    '       GGGGG        ',
    '      GGGGGGG       ',
    '     GGGGGGGGG      ',
    '      GGGGGGG       ',
    '     GGGGGGGGG      ',
    '    GGGGGGGGGGG     ',
    '     GGGGGGGGG      ',
    '    GGGGGGGGGGG     ',
    '   GGGGGGGGGGGGG    ',
    '    GGGGGGGGGGG     ',
    '   GGGGGGGGGGGGG    ',
    '  GGGGGGGGGGGGGGG   ',
    '   GGGGGGGGGGGGG    ',
    '  GGGGGGGGGGGGGGG   ',
    ' GGGGGGGGGGGGGGGGG  ',
    '  GGGGGGGGGGGGGGG   ',
    ' GGGGGGGGGGGGGGGGG  ',
    'GGGGGGGGGGGGGGGGGGG ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '        oo          ',
    '                    ',
    '                    ',
  ],

  // Grass Tuft (12×8) — jagged green clump
  grass: [
    '            ',
    '    gg      ',
    '   gggg  gg ',
    '  gggggggggg',
    ' ggggggggggg',
    ' ggggggggggg',
    '  ggggggggg ',
    '            ',
  ],

  // Desert Shrub (16×12) — sparse wiry branches
  shrub: [
    '                ',
    '   o       o    ',
    '   oo     oo    ',
    '    o     o     ',
    '    oo   oo     ',
    '     o   o      ',
    '     oo oo      ',
    '      ooo       ',
    '      ooo       ',
    '       o        ',
    '       o        ',
    '                ',
  ],

  // Cactus (10×24) — saguaro shape
  cactus: [
    '          ',
    '    gg    ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    'gggggggggg',
    'gggggggggg',
    'gggggggggg',
    'gggggggggg',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '   gggg   ',
    '          ',
  ],

  // Rock (14×10) — grey irregular lump
  rock: [
    '              ',
    '   rrrrrr     ',
    '  rrrrrrrr    ',
    ' rrrrrrrrrr   ',
    ' rrrrrrrrrrr  ',
    ' rrrrrrrrrrrr ',
    ' rrrrrrrrrrr  ',
    '  rrrrrrrrr   ',
    '   rrrrrr     ',
    '              ',
  ],
};

// ── Helpers ──────────────────────────────────────────────────────────

function drawGrid(ctx, grid, x, y, scale = 1) {
  for (let row = 0; row < grid.length; row++) {
    const line = grid[row];
    for (let col = 0; col < line.length; col++) {
      const ch = line[col];
      const color = PALETTE[ch];
      if (color) {
        ctx.fillStyle = color;
        ctx.fillRect(x + col * scale, y + row * scale, scale, scale);
      }
    }
  }
}

function gridSize(grid) {
  return {
    w: grid[0]?.length || 0,
    h: grid.length,
  };
}

// ── Pre-render cache ─────────────────────────────────────────────────

class SpriteCache {
  constructor() {
    this._cache = new Map();
  }

  _key(type, facingRight, dead, frame = 0) {
    return `${type}|${facingRight}|${dead}|${frame}`;
  }

  _renderToCanvas(grid, facingRight, dead) {
    const { w, h } = gridSize(grid);
    const canvas = document.createElement('canvas');
    const scale = 1;
    canvas.width = w * scale;
    canvas.height = h * scale;
    const ctx = canvas.getContext('2d');

    ctx.save();
    if (!facingRight) {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    if (dead) {
      ctx.translate(0, canvas.height);
      ctx.scale(1, -1);
    }
    drawGrid(ctx, grid, 0, 0, scale);
    ctx.restore();
    return canvas;
  }

  get(grid, facingRight = true, dead = false) {
    const key = this._key(grid, facingRight, dead);
    if (!this._cache.has(key)) {
      this._cache.set(key, this._renderToCanvas(grid, facingRight, dead));
    }
    return this._cache.get(key);
  }
}

const CACHE = new SpriteCache();

// ── Public API ───────────────────────────────────────────────────────

export class SpriteRenderer {
  constructor(ctx) {
    this.ctx = ctx;
    this.scale = 2; // default pixel scale
  }

  /**
   * Set global pixel scale (default 2). All sprites are drawn at this multiplier.
   */
  setScale(scale) {
    this.scale = Math.max(1, Math.floor(scale));
  }

  /**
   * Draw an animal sprite centered on (x, y).
   * @param {string} type  — 'squirrel'|'rabbit'|'deer'|'elk'|'bear'|'buffalo'
   * @param {number} x     — center x
   * @param {number} y     — center y
   * @param {boolean} facingRight
   * @param {boolean} dead
   */
  drawAnimal(type, x, y, facingRight = true, dead = false) {
    const grid = ANIMALS[type];
    if (!grid) return;
    const { w, h } = gridSize(grid);
    const s = this.scale;
    const drawX = x - (w * s) / 2;
    const drawY = y - (h * s) / 2;

    const cached = CACHE.get(grid, facingRight, dead);
    this.ctx.drawImage(cached, drawX, drawY, w * s, h * s);
  }

  /**
   * Draw the hunter centered on (x, y) facing a compass angle.
   * @param {number} x      — center x
   * @param {number} y      — center y
   * @param {number} angle  — radians, 0 = east, PI/2 = south, etc.
   * @param {boolean} isAiming — if true, tint rifle blue
   */
  drawHunter(x, y, angle, isAiming = false) {
    // Map angle to one of 8 directions
    const dir = (Math.round((angle / (Math.PI * 2)) * 8) + 8) % 8;
    const grid = HUNTERS[dir];
    const { w, h } = gridSize(grid);
    const s = this.scale;
    const drawX = x - (w * s) / 2;
    const drawY = y - (h * s) / 2;

    this.ctx.save();
    this.ctx.translate(drawX, drawY);
    this.ctx.scale(s, s);

    for (let row = 0; row < grid.length; row++) {
      const line = grid[row];
      for (let col = 0; col < line.length; col++) {
        const ch = line[col];
        let color = PALETTE[ch];
        if (!color) continue;
        // Aiming highlight: swap blue barrel to bright blue, else keep
        if (isAiming && ch === 'b') {
          color = '#00ccff';
        }
        this.ctx.fillStyle = color;
        this.ctx.fillRect(col, row, 1, 1);
      }
    }
    this.ctx.restore();
  }

  /**
   * Draw a terrain object with its top-left at (x, y).
   * @param {string} type — 'deciduous'|'coniferous'|'grass'|'shrub'|'cactus'|'rock'
   * @param {number} x
   * @param {number} y
   */
  drawTerrain(type, x, y) {
    const grid = TERRAIN[type];
    if (!grid) return;
    const { w, h } = gridSize(grid);
    const s = this.scale;

    const cached = CACHE.get(grid, true, false);
    this.ctx.drawImage(cached, x, y, w * s, h * s);
  }

  /**
   * Low-level helper: draw a raw string-grid directly.
   * @param {string[]} grid
   * @param {number} x
   * @param {number} y
   */
  drawRaw(grid, x, y) {
    drawGrid(this.ctx, grid, x, y, this.scale);
  }
}

// ── Standalone exports (convenience) ─────────────────────────────────

export function drawSquirrel(ctx, x, y, facingRight, dead) {
  const r = new SpriteRenderer(ctx);
  r.drawAnimal('squirrel', x, y, facingRight, dead);
}

export function drawRabbit(ctx, x, y, facingRight, dead) {
  const r = new SpriteRenderer(ctx);
  r.drawAnimal('rabbit', x, y, facingRight, dead);
}

export function drawDeer(ctx, x, y, facingRight, dead) {
  const r = new SpriteRenderer(ctx);
  r.drawAnimal('deer', x, y, facingRight, dead);
}

export function drawElk(ctx, x, y, facingRight, dead) {
  const r = new SpriteRenderer(ctx);
  r.drawAnimal('elk', x, y, facingRight, dead);
}

export function drawBear(ctx, x, y, facingRight, dead) {
  const r = new SpriteRenderer(ctx);
  r.drawAnimal('bear', x, y, facingRight, dead);
}

export function drawBuffalo(ctx, x, y, facingRight, dead) {
  const r = new SpriteRenderer(ctx);
  r.drawAnimal('buffalo', x, y, facingRight, dead);
}

export function drawHunter(ctx, x, y, angle, isAiming) {
  const r = new SpriteRenderer(ctx);
  r.drawHunter(x, y, angle, isAiming);
}

export function drawTerrain(ctx, type, x, y) {
  const r = new SpriteRenderer(ctx);
  r.drawTerrain(type, x, y);
}
