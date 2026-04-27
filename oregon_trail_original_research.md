# Original Oregon Trail Hunting Mini-Game: Research Compilation

> Primary-source research for accurately modeling the 1985/1990 hunting mini-game in a modern remake.
> Compiled from original designer writings, manuals, disk images, and technical breakdowns.

---

## 1. Which Version Should You Emulate?

The **1985 Apple II version** (ported to DOS in 1990) is the iconic design that created nearly all the memes and mechanics people associate with *The Oregon Trail*. It was designed by **R. Philip Bouchard** at MECC.

- **1985 Apple IIe**: 6-color graphics, 280×192 resolution (effective), keyboard-only input
- **1990 DOS**: Gameplay-identical to Apple II; slightly different color rendering (CGA/EGA)
- **1992 Deluxe / 1991 Mac**: Mouse support added; otherwise the same core design

**Verdict**: Emulate the **1985 Apple II / 1990 DOS** hunting mechanics and aesthetic.

---

## 2. Core Hunting Mechanics (From Primary Sources)

### 2.1 The 100-Pound Carry Limit
> *"You go out hunting, and you shoot a bison. Maybe you shoot two or three bison. As the hunting session comes to an end, the screen tells you how many pounds of animals you have just killed. Then you see 'However, you were only able carry 100 pounds back to the wagon.'"*
> — R. Philip Bouchard, lead designer

- **Hard cap**: A hunter can carry **100 lbs** of meat back to the wagon per hunting trip.
- **Waste mechanic**: If you kill more than 100 lbs total, the excess is wasted. This was an intentional educational design choice to teach players about wastefulness.
- **Later versions** (Deluxe, etc.) increased this to 200 lbs, but the classic limit is **100**.

### 2.2 Time Cost
> *"whether it's a two-pound rabbit on the prairie or a 400-pound bear in the mountains, hunting takes a day away from the trail."*
> — 1985 Apple II Instructional Manual

- Every hunting session costs **exactly 1 day** of travel time.
- There is a **timer** during the hunt (implied by "nightfall" in analysis). The session ends automatically when time runs out.

### 2.3 Aiming & Shooting (1985 Design)
- **Third-person perspective**: A small hunter character appears on screen carrying a rifle.
- **8-directional aiming**: Up, down, left, right, and 4 diagonals.
- **8-directional movement**: The hunter can walk and shoot in 8 directions.
- **Single shot per keypress**: Press a key (or button) to fire one bullet in the currently aimed direction.
- **No mouse in original**: Apple II had no mouse; everything was keyboard-controlled. (Mouse support came in 1991 Mac / 1992 Deluxe versions.)

### 2.4 Difficulty
- Bouchard intentionally kept hunting **difficult**.
- Adults complained it was too hard; kids mastered it in 3–4 hunting trips.
- Animals move at varied angles (not just 8 directions), requiring positioning and prediction.
- Terrain obstacles (trees, rocks) block movement and line-of-sight.

---

## 3. Animals in the Original Game

### 3.1 Final 6 Animals (1985)
Originally 11 species were researched and planned:
Bear, Raccoon, Fox, Coyote, Rabbit, Elk, Deer, Moose, Pronghorn, Bison, Squirrel

Due to Apple II memory constraints (each animal needed 8–10 graphic states), the list was cut to **6**:

| Animal | Typical Weight (from Bouchard's research) | Notes |
|--------|-------------------------------------------|-------|
| **Squirrel** | ~1–2 lbs | Smallest animal |
| **Rabbit** | ~2–5 lbs | Manual explicitly mentions "two-pound rabbit" |
| **Deer** | ~100–200 lbs | Common everywhere |
| **Elk** | ~200–400 lbs | Larger than deer |
| **Bear** | ~200–600 lbs | Manual mentions "400-pound bear" |
| **Bison / Buffalo** | ~400–1,000+ lbs | Manual: "weigh a lot more than the hundred pounds" |

### 3.2 Animal Behavior (from designer notes)
- Animals can move in **all directions** (not restricted to 8-way like the player).
- Animals move at **different speeds**.
- Speed and direction changes are triggered by algorithms (not purely random).
- Animals are selected based on **terrain zone** (e.g., bison on plains, bear in mountains).

### 3.3 Death Animation
> *"When Charolyn first delivered the animal graphics to Roger, she did not include the 'dead state' graphics... Roger simply flipped the animal graphic upside-down to indicate that it had been shot... Then Charolyn delivered the dead-state graphics... the collapsed buffalo was pretty effective, but all of the other dead animals looked like lumps. Of course the solution was immediately obvious – we went back to flipping over the graphic whenever an animal was shot."*
> — R. Philip Bouchard

- **Classic death animation**: The sprite is **flipped upside-down**.
- This was kept because "kids loved it" and "there was never any doubt as to when an animal had been killed."

---

## 4. Terrain & Environment System

### 4.1 Five Terrain Zones
The Oregon Trail was divided into 5 zones, each affecting what landscape objects and animals appear:

| Zone | Eligible Objects | Animals Likely |
|------|------------------|----------------|
| **Eastern Forest** | Deciduous trees, tufts of grass | Deer, rabbit, squirrel |
| **Plains** | Tufts of grass | Bison, pronghorn, rabbit |
| **Rocky Mountains** | Coniferous trees, rocks | Bear, elk, deer |
| **Desert** | Cacti, desert shrubs, rocks | Rabbit, coyote (cut from final) |
| **Western Forest** | Coniferous trees | Deer, elk, bear |

### 4.2 Landscape Objects
- **6 object types**: Deciduous trees, coniferous trees, tufts of grass, desert shrubs, cacti, rocks
- **3 distinct images per type** = 18 total landscape graphics
- **4–6 objects** are randomly placed on screen per hunt
- Objects are **obstacles**: the player must walk around them; cannot walk through them
- Black background: "Much of the screen is black, but scattered around the screen are objects"

---

## 5. Visual & Technical Specs (Apple II 1985)

### 5.1 Display
- **Resolution**: 280×192 (Apple II lo-res or hi-res graphics mode)
- **Colors**: **6 colors** total (Apple II hardware limitation)
  - Black, white, purple, green, blue, orange (or similar depending on mode)
  - In practice, hunting screen was mostly **black** with colored objects scattered on it
- **No scrolling background**: Static black playfield with scattered terrain sprites

### 5.2 Sprite Animation
- **3-phase running animation** per animal (reduced from 4 due to memory)
- **Dead state**: upside-down flip (not a separate frame in the final design)
- **Left and right facing**: All animations mirrored for both directions
- **48 animal images** loaded into memory total (6 animals × 8 states each)

### 5.3 Hunter Character
- Small human figure holding a rifle
- 8 directional poses for aiming
- 8 directional poses for walking
- Monochrome concept art shows a simple stick-figure-like hunter

---

## 6. Original Asset Archives & Playable Versions

### 6.1 Disk Images (Apple II)
| Source | URL / Location | Contents |
|--------|---------------|----------|
| **Apple II Software Mirrors** | `https://mirrors.apple2.org.za/ftp.apple.asimov.net/images/educational/mecc/` | Original `.dsk` and `.nib` disk images for Oregon Trail 1.1, 1.4 |
| **MECC-A157** | `MECC-A157 The Oregon Trail v1.1 (4am crack).zip` | Apple II disk image |
| **MECC Hard Disk Collection** | `MECC_Hard_Disk.zip` (11.77 MB) | 150+ MECC titles including Oregon Trail, installable to hard drive |

### 6.2 Playable Online
| Site | URL | Notes |
|------|-----|-------|
| **Died of Dysentery** | `https://www.died-of-dysentery.com/resources.html` | Play 1985 Apple II, 1990 DOS, 1980 Apple II, and 1978 text versions in browser emulators |
| **Virtual Apple II** | Various | Browser-based Apple II emulator loading Oregon Trail disks |

### 6.3 Manuals & Documentation
| Document | URL | Notes |
|----------|-----|-------|
| **1985 Apple II Manual (PDF)** | `https://mirrors.apple2.org.za/ftp.apple.asimov.net/images/educational/mecc/documentation/MECC-A157%20The%20Oregon%20Trail%20manual.pdf` | Official MECC instructional manual; describes hunting rules |
| **Alternative PDF Host** | `https://media.the-learning-agency.com/wp-content/uploads/2025/02/28110545/mecc_a-157_oregon_trail.pdf` | Same manual, different mirror |
| **Old Games Download** | `https://oldgamesdownload.com/wp-content/uploads/The_Oregon_Trail_AppleII_Manual_EN.pdf` | Another PDF mirror |

### 6.4 Designer Source Articles
| Article | Author | URL |
|---------|--------|-----|
| **The Hunting Activity** | R. Philip Bouchard | `https://www.philipbouchard.com/oregon-trail/hunting.html` |
| **The Travel Screen** | R. Philip Bouchard | `https://www.philipbouchard.com/oregon-trail/travel-screen.html` |

---

## 7. Source Code & Reverse Engineering Repos

| Repo | URL | Description |
|------|-----|-------------|
| **1978 BASIC Source** | `https://github.com/clintmoyer/oregon-trail` | Original source code from Creative Computing May-June 1978 issue (BASIC 3.1 for CDC Cyber 70) |
| **1978 Python Port** | `https://github.com/philjonas/oregon-trail-1978-python` | The 1978 BASIC code ported to Python 3.7 |
| **Java Remake (1990s)** | `https://github.com/hlpdev/OregonTrail` | Recreation of the 1990s version in Java (terminal UI). Archived read-only. |
| **Oregon Trail II Reverse Engineering** | `https://github.com/katstasaph/otii` | Decompiled C++ from Oregon Trail II executable |
| **Fortran 77 Port** | `https://github.com/topics/oregon-trail` | Various ports including Fortran 77 |
| **P5.js Apple II Version** | Various on GitHub Topics | Browser-based Apple II recreations |

> **Note**: The 1985 Apple II assembly source code for the hunting module has **never been officially released**. The only available source is the 1978 text-based BASIC version. The 1985 hunting module was written in 6502 assembly by Roger Shimada.

---

## 8. Key Differences: 1985 Classic vs. Later Versions

| Feature | 1985 Apple II / 1990 DOS | 1992 Deluxe+ |
|---------|--------------------------|--------------|
| Carry limit | **100 lbs** | 200 lbs |
| Input | Keyboard only | Mouse supported |
| Animals | 6 species | More species added |
| Death anim | Upside-down flip | Upside-down flip |
| Background | Black + scattered objects | Enhanced terrain graphics |
| Hunter view | Third-person character | Third-person character |

---

## 9. Recommendations for Your Remake

### 9.1 Mechanics to Port Faithfully
1. **100 lb carry limit** with waste messaging ("However, you were only able to carry 100 pounds back to the wagon.")
2. **1 day cost** per hunt
3. **Timer** limiting hunt duration (representing daylight/nightfall)
4. **Terrain zones** affecting which animals spawn
5. **Obstacles** blocking player movement and line-of-sight
6. **8-directional** aiming and movement
7. **Upside-down flip** death animation (iconic!)
8. **Different animal speeds** and AI behavior per species

### 9.2 Visual Style to Port
1. **Black background** with scattered terrain objects (not a full landscape)
2. **6-color or limited palette** aesthetic
3. **Pixel-art sprites** with 3-frame run cycles
4. **Small hunter character** visible on screen (third-person)
5. **No crosshair** in the original — the hunter character aims in 8 directions. (However, a mouse-driven remake could reasonably use a crosshair as a modern QoL feature.)

### 9.3 Food Yield Table (Recommended for Remake)
Based on the manual and designer notes:

| Animal | Food Yield (lbs) | Original Source |
|--------|-----------------|-----------------|
| Squirrel | 2 | Inferred (small game) |
| Rabbit | 2–5 | Manual says "two-pound rabbit" |
| Deer | 50–100 | Realistic dressed weight |
| Elk | 75–150 | Realistic dressed weight |
| Bear | 100–400 | Manual says "400-pound bear"; cap at carry limit |
| Buffalo | 100–1000+ | Manual says "weigh a lot more than 100 pounds"; cap at 100 lbs carried |

**Important**: In the original, the food yield is the **actual animal weight**, but the player only receives `min(total_killed, 100)` lbs. So Buffalo might yield 800 lbs but the player only gets 100.

---

## 10. Screenshot References

The following URLs host original screenshots (access may vary):

- **MobyGames Apple II Gallery**: `https://www.mobygames.com/game/746/the-oregon-trail/screenshots/apple2/`
- **MobyGames DOS Gallery**: `https://www.mobygames.com/game/746/the-oregon-trail/screenshots/dos/`
- **Philip Bouchard's article** includes embedded screenshots of the hunting screen for both Apple II and DOS versions.

---

*Compiled from primary sources including the original lead designer's writings, 1985 MECC instructional manuals, and software preservation archives.*
