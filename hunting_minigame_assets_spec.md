# Hunting Mini-Game: 8-Bit Pixel Art Asset Specification

## 1. Sprite Dimensions Table

All sprites are designed for a **640×400** game canvas. Dimensions follow clean 8-pixel grid multiples (or powers-of-two where practical) to maintain crisp scaling and authentic 8-bit sprite-sheet alignment.

| Asset | Canvas (W×H) | Justification |
|---|---|---|
| Squirrel | **16 × 16** | Smallest game sprite. 16×16 is the classic 8-bit tile size; fits a scurrying silhouette without wasting sheet space. |
| Rabbit | **16 × 16** | Only slightly larger than a squirrel in pixel-art scale. 16×16 keeps memory/sheet usage minimal; distinguishable by long-ear silhouette and color. |
| Deer | **32 × 24** | Medium ungulate. 32×24 gives enough width for graceful legs/neck while keeping height proportional to the 400 px play-field. |
| Elk | **48 × 32** | Large herd animal with antlers. 48 px width accommodates rack silhouette; 32 px height matches the 8-pixel grid. |
| Bear | **48 × 32** | Bulky predator. Same footprint as elk but with a heavier, boxier silhouette to communicate mass. |
| Buffalo | **64 × 32** | Largest animal. 64×32 (power-of-two width) provides the iconic humped silhouette and visual weight befitting 150 lbs of food. |
| Crosshair (Reticle) | **32 × 32** | UI element. 32×32 is large enough for precise aim visibility on a 640×400 canvas without obscuring targets. |
| Muzzle Flash | **16 × 16** | Transient VFX. Compact 16×16 bloom frame keeps the effect punchy and avoids overdrawing large screen areas. |

> **Grid Rule:** All dimensions are multiples of 8, ensuring clean sprite-sheet packing and hardware-accelerated rendering without sub-pixel blur.

---

## 2. Food Yield Table

Values match the classic *Oregon Trail* hunting yields and map directly to the `food_yield` game-data field.

| Animal | `food_yield` (lbs) |
|---|---|
| Squirrel | 1 |
| Rabbit | 2 |
| Deer | 50 |
| Elk | 75 |
| Bear | 100 |
| Buffalo | 150 |

---

## 3. Animation Frame Guidelines

Sprite sheets should lay out frames **horizontally** (left-to-right) with each frame equal to the base canvas size defined above.

| Asset | Frames | Description | Recommended Sheet Size (W×H) |
|---|---|---|---|
| Squirrel | **4** | 3-frame scurry cycle + 1 death/flop frame | 64 × 16 |
| Rabbit | **4** | 3-frame hop cycle + 1 death/frame (on back) | 64 × 16 |
| Deer | **4** | 3-frame gallop cycle + 1 hit/death frame | 128 × 24 |
| Elk | **4** | 3-frame run cycle + 1 hit/death frame | 192 × 32 |
| Bear | **3** | 2-frame lumbering run + 1 rearing hit/death frame | 144 × 32 |
| Buffalo | **3** | 2-frame heavy trot + 1 collapse/death frame | 192 × 32 |
| Crosshair | **2** | 1 idle reticle + 1 "locked-on" highlight frame | 64 × 32 |
| Muzzle Flash | **3** | Frame 1: white core; Frame 2: yellow bloom; Frame 3: orange fade | 48 × 16 |

### Frame Timing Notes
- **Animal run cycles:** 100–150 ms per frame (squirrel/rabbit faster at ~100 ms; buffalo slower at ~150 ms).
- **Death frames:** Hold for 300 ms then trigger despawn or convert to a static food-bag icon.
- **Muzzle flash:** Rapid 50 ms sequence (frame 1 → 2 → 3) then remove.
- **Crosshair:** Toggle between frames based on aim-overlap state (no auto-play).

---

## 4. Color Count Recommendation

To preserve an authentic 8-bit aesthetic, enforce a strict per-sprite palette limit. Use the NES/APFG-inspired rule of **one transparent color + N opaque colors**.

| Asset | Max Opaque Colors | Notes |
|---|---|---|
| Squirrel | **3** | Brown body, lighter belly, dark tail/eye. |
| Rabbit | **3** | Grey/brown body, white tail, pink ear interior. |
| Deer | **4** | Tan body, white underside, dark hooves/nose, antler beige. |
| Elk | **5** | Dark brown body, lighter mane, tan antlers, black hooves/nose, rump patch. |
| Bear | **4** | Dark brown/black body, lighter muzzle, red tongue (optional hit frame), claws. |
| Buffalo | **5** | Dark brown body, black head/horns, tan hump, brown shag, hooves. |
| Crosshair | **2** | Bright white (or neon green) + red "locked" highlight. |
| Muzzle Flash | **3** | White (#FFFFFF), yellow (#FFDD00), orange (#FF6600). |

### Global Palette Guidelines
- **Total unique colors across all hunting sprites:** ≤ 32 (including crosshair and VFX). This allows the entire mini-game to fit in a single indexed 8-bit palette texture if desired.
- **Avoid alpha blending** for opaque pixels; use 1-bit transparency (fully opaque or fully transparent) to preserve sharp pixel edges.
- **Outline:** 1-pixel black or darkest-color outline on animals for contrast against grass/sky backgrounds.
