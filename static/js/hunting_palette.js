/**
 * Oregon Trail: Hunting Mini-Game Color Palette
 * A cohesive 8-bit palette anchored on Terminal Green (#4af626)
 */

const PALETTE = {
  // Primary
  terminalGreen: 'hsl(110, 92%, 55%)',
  terminalDark: 'hsl(110, 60%, 8%)',
  retroAmber: 'hsl(48, 100%, 58%)',

  // Terrain
  sky: 'hsl(195, 35%, 72%)',
  grass: 'hsl(105, 50%, 38%)',
  dirt: 'hsl(32, 42%, 42%)',
  treeDark: 'hsl(120, 35%, 16%)',

  // Animals — Rabbit
  rabbitLight: 'hsl(28, 48%, 62%)',
  rabbitDark: 'hsl(28, 45%, 48%)',
  rabbitBelly: 'hsl(28, 40%, 78%)',

  // Animals — Deer
  deerCoat: 'hsl(36, 46%, 52%)',
  deerDark: 'hsl(30, 40%, 36%)',
  deerBelly: 'hsl(36, 40%, 68%)',

  // Animals — Elk
  elkCoat: 'hsl(30, 38%, 42%)',
  elkMane: 'hsl(30, 30%, 58%)',
  elkAntler: 'hsl(36, 45%, 72%)',

  // Animals — Bear
  bearFur: 'hsl(220, 12%, 26%)',
  bearSnout: 'hsl(220, 15%, 40%)',
  bearShadow: 'hsl(220, 12%, 16%)',

  // Animals — Buffalo
  buffaloFur: 'hsl(30, 30%, 28%)',
  buffaloHump: 'hsl(36, 35%, 45%)',
  buffaloHoof: 'hsl(30, 20%, 18%)',

  // UI / Game
  crosshair: 'hsl(110, 100%, 88%)',
  muzzleFlash: 'hsl(55, 100%, 78%)',
  hitSuccess: 'hsl(110, 100%, 65%)',
  missFail: 'hsl(355, 55%, 48%)',
  textPrimary: 'hsl(110, 92%, 55%)',
  textSecondary: 'hsl(110, 50%, 70%)',
  panelOverlay: 'hsla(110, 35%, 8%, 0.88)',
};

// Optional CSS custom properties for use in stylesheets
const PALETTE_CSS = `
:root {
  --color-terminal-green: hsl(110, 92%, 55%);
  --color-terminal-dark: hsl(110, 60%, 8%);
  --color-retro-amber: hsl(48, 100%, 58%);

  --color-sky: hsl(195, 35%, 72%);
  --color-grass: hsl(105, 50%, 38%);
  --color-dirt: hsl(32, 42%, 42%);
  --color-tree-dark: hsl(120, 35%, 16%);

  --color-rabbit-light: hsl(28, 48%, 62%);
  --color-rabbit-dark: hsl(28, 45%, 48%);
  --color-rabbit-belly: hsl(28, 40%, 78%);

  --color-deer-coat: hsl(36, 46%, 52%);
  --color-deer-dark: hsl(30, 40%, 36%);
  --color-deer-belly: hsl(36, 40%, 68%);

  --color-elk-coat: hsl(30, 38%, 42%);
  --color-elk-mane: hsl(30, 30%, 58%);
  --color-elk-antler: hsl(36, 45%, 72%);

  --color-bear-fur: hsl(220, 12%, 26%);
  --color-bear-snout: hsl(220, 15%, 40%);
  --color-bear-shadow: hsl(220, 12%, 16%);

  --color-buffalo-fur: hsl(30, 30%, 28%);
  --color-buffalo-hump: hsl(36, 35%, 45%);
  --color-buffalo-hoof: hsl(30, 20%, 18%);

  --color-crosshair: hsl(110, 100%, 88%);
  --color-muzzle-flash: hsl(55, 100%, 78%);
  --color-hit-success: hsl(110, 100%, 65%);
  --color-miss-fail: hsl(355, 55%, 48%);
  --color-text-primary: hsl(110, 92%, 55%);
  --color-text-secondary: hsl(110, 50%, 70%);
  --color-panel-overlay: hsla(110, 35%, 8%, 0.88);
}
`;

export { PALETTE, PALETTE_CSS };
