# The Oregon Trail (1985/1990s) — Comprehensive Game Mechanics Reference

> Compiled from authoritative sources: R. Philip Bouchard (lead designer) design documents, StrategyWiki, Perfect Pacman deep-dive analysis, MECC original manual, and historical trail records.

---

## 1. LANDMARKS AND TRAIL SEGMENTS

The 1985 Apple II version features **18 landmarks** along a roughly **2,000-mile** route. The game uses 1848 as its setting.

### Complete Landmark List (Game Order)

| # | Landmark | Type | ~Miles from Independence | ~Miles to Next |
|---|----------|------|--------------------------|----------------|
| 1 | **Independence, Missouri** | Start / Town | 0 | 80-100 |
| 2 | **Kansas River Crossing** | River | ~100 | ~80 |
| 3 | **Big Blue River Crossing** | River | ~180 | ~120 |
| 4 | **Fort Kearney** | Fort | ~300 | ~271 |
| 5 | **Chimney Rock** | Landmark | ~571 | ~96 |
| 6 | **Fort Laramie** | Fort | ~667 | ~171 |
| 7 | **Independence Rock** | Landmark | ~838 | ~109 |
| 8 | **South Pass** | Landmark / Branch | ~947 | branch |
| 9a | **Fort Bridger** | Fort (southern) | ~1,070 | ~136 |
| 9b | **Green River Crossing** | River (northern) | ~1,014 | ~192 |
| 10 | **Soda Springs** | Landmark | ~1,206 | ~82 |
| 11 | **Fort Hall** | Fort / Branch | ~1,288 | ~212 |
| 12 | **Snake River Crossing** | River | ~1,500 | ~85 |
| 13 | **Fort Boise** | Fort | ~1,585 | ~151 |
| 14 | **Blue Mountains** | Landmark | ~1,736 | ~64 |
| 15 | **Fort Walla Walla** | Fort | ~1,800 | ~134 |
| 16 | **The Dalles** | Landmark / Endgame | ~1,934 | choice |
| 17 | **Willamette Valley / Oregon City** | End | ~2,094 | 0 |

### Branch Points
- **South Pass**: Choose Fort Bridger route (safer, longer, one extra fort) or Green River cutoff (shorter, riskier, one less river).
- **Fort Hall**: California vs. Oregon split (game assumes Oregon).
- **The Dalles**: Choose **Barlow Toll Road** (pay cash, safer overland) or **raft down Columbia River** (free arcade mini-game, risk of rocks).

### Historical Mileage Reference (Real Trail)
| From Independence To | Miles |
|----------------------|-------|
| Kansas River | ~80-100 |
| Big Blue River | ~150-180 |
| Platte River | ~316 |
| Chimney Rock | ~571 |
| Fort Laramie | ~667 |
| Independence Rock | ~838 |
| South Pass | ~947 |
| Green River | ~1,014 |
| Fort Bridger | ~1,070 |
| Soda Springs | ~1,206 |
| Fort Hall | ~1,288 |
| Fort Boise | ~1,585 |
| The Dalles | ~1,934 |
| Oregon City | ~2,094 |

---

## 2. ITEM PRICES — GENERAL STORE

### Starting Prices (Independence, Missouri — Matt's General Store)

| Item | Unit Price | Notes |
|------|------------|-------|
| **Oxen** |  per ox ( per yoke of 2) | Minimum 1 yoke (2 oxen) required to leave. Max oxen: 20. |
| **Food** | .10 per pound | Wagon max: 2,000 lbs. |
| **Clothing** |  per set | Rec: 10-20 sets for 5-person party. |
| **Ammunition** | .00 per box (20 bullets) | 10 cents per bullet. |
| **Wagon Wheel** |  each | Max spare parts of each type: 3. |
| **Wagon Axle** |  each | Same 3-part cap. |
| **Wagon Tongue** |  each | Same 3-part cap. |

### Price Inflation at Forts
Prices increase the farther west you travel. Rough multipliers:
- **Fort Kearney**: ~1.25x Independence prices
- **Fort Laramie**: ~1.5x Independence prices
- **Fort Bridger**: ~2x Independence prices
- **Fort Hall**: ~2.5x Independence prices
- **Fort Boise**: ~3x+ Independence prices

### Trade Value Equivalency (NPC trades use roughly this ratio)
The game uses a hidden equivalency table for random trade offers:

`
1 ox          = 2 sets of clothes
              = 2 wagon parts (any type)
              = 200 bullets
              = 100 pounds of food
`

NPC trades usually favor the NPC. Trading costs **1 day** of travel time.

---

## 3. RANDOM EVENTS

### 1985 Version Events (Common)

| # | Event | Typical Effect |
|---|-------|----------------|
| 1 | **Wagon wheel breaks** | Lose 1 wheel. Stranded if no spare. |
| 2 | **Wagon axle breaks** | Lose 1 axle. Stranded if no spare. |
| 3 | **Wagon tongue breaks** | Lose 1 tongue. Stranded if no spare. |
| 4 | **Ox injured / dies** | Lose 1 ox. Stranded if last ox dies. |
| 5 | **Thief in the night** | Lose random food, bullets, or clothes. |
| 6 | **Wagon fire** | Lose random supplies (can be catastrophic). |
| 7 | **Bad water** | Health decline; illness chance. |
| 8 | **No water** | Delay 1 day; health decline. |
| 9 | **No grass for oxen** | Delay; oxen health declines. |
| 10 | **Lost trail** | Lose 1-3 days backtracking. |
| 11 | **Snake bite** | One member injured; may die without rest. |
| 12 | **Member illness** | Dysentery, cholera, measles, typhoid, exhaustion. |
| 13 | **Heavy fog** | Lose 1 day. |
| 14 | **Find wild fruit** | +20 lbs food (free). |
| 15 | **Find abandoned wagon** | Gain random supplies. |
| 16 | **Indians help find food** | +30 lbs food (only when food near 0). |
| - | **Hail storm / blizzard** | Lose days; health drops; winter/mountains. |
| - | **Wrong path / rough terrain** | Lose supplies or days. |

### Event Probabilities (Original 1975 BASIC Logic)
The original text game used minutes-past-the-hour as a random seed base:
- R1 chosen between TIM(0) (minutes past hour) and 100.
- Compared to DATA table: 6, 11, 13, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28
- **Effect**: Later in the hour = harder events more likely.
- The 1985 version replaced this with conventional weighted random, but severe events remain more common in bad terrain/weather.

### Terrain/Event Correlation
- **Prairie**: Balanced events, abundant buffalo.
- **Mountains**: More broken parts, illness, exhaustion, snow in late year.
- **Desert**: No water, no grass, bad water, heat exhaustion.
- **Rivers**: Automatic river crossing events.

---

## 4. HEALTH SYSTEM

### Party Health Levels
Health is tracked as a **party-wide average** and displayed as:

| Level | Score Value | Condition |
|-------|-------------|-----------|
| **Good** | 500 pts/person | Well-fed, rested, good pace. |
| **Fair** | 400 pts/person | Minor deprivation or recent illness. |
| **Poor** | 300 pts/person | Significant hardship or active illness. |
| **Very Poor** | 200 pts/person | Near death, starvation, extreme pace. |
| **Dead** | 0 | Cannot recover. |

### Illness Types

| Illness | Cause / Context | Severity |
|---------|-----------------|----------|
| **Dysentery** | Bad water, low rations | Very high |
| **Cholera** | Bad water, contamination | Very high |
| **Measles** | Crowded conditions | Moderate-High |
| **Typhoid** | Bad water, poor sanitation | High |
| **Exhaustion** | Grueling pace, no rest | Moderate |
| **Fever** | Infection, weather extremes | Moderate |
| **Snake bite** | Random travel event | Moderate-High |
| **Broken arm/leg** | Random accident | Moderate |

### Health Modifiers
**IMPROVE health:**
- Resting (1-9 days)
- Filling rations
- Adequate clothing (especially cold/mountains)
- Steady pace

**DECLINE health:**
- Grueling pace
- Bare Bones rations
- Winter / snow / extreme heat
- Mountains or desert travel
- River crossing failures
- Bad water / no water / no grass
- Each active illness drags average down

### Death Conditions
1. Health drops to Very Poor + another negative event hits.
2. Specific fatal events while already ill (dysentery + no rest).
3. Drowning during river crossing.
4. Starvation: food = 0 for approximately **20+ days** causes deaths.
5. The **wagon leader** only becomes vulnerable after ALL other 4 members die.
6. When someone dies, the player can write a **tombstone epitaph**.

---

## 5. PACE AND RATIONS

### Pace Settings

| Pace | ~Miles/Day | Health Impact | Oxen Impact | Use Case |
|------|------------|---------------|-------------|----------|
| **Steady** | ~8-12 | Minimal | Minimal | Recovering health, bad terrain, few oxen. |
| **Strenuous** | ~12-18 | Moderate | Moderate | Default balanced choice. |
| **Grueling** | ~18-25 | Severe | High | Good weather, good health, racing winter. |

> Exact miles vary by terrain, oxen count, and weather.

### Rations Settings

| Rations | Food/Person/Day | Health Impact | Strategy |
|---------|-----------------|---------------|----------|
| **Filling** | 3 lbs | Improves/maintains | Best for recovery. Burns food fast. |
| **Meager** | 2 lbs | Neutral/slight decline | Balanced. 5 people = 10 lbs/day. |
| **Bare Bones** | 1 lb | Gradual decline | Emergency. 5 people = 5 lbs/day. |

### Combined Strategy Notes
- **Strenuous + Meager** = standard balanced approach.
- **Grueling + Filling** = fastest travel while maintaining health (burns food).
- **Steady + Filling** = best for recovering sick party members.
- **Never do Grueling + Bare Bones** unless desperate — health will crater.

### Starting Month Recommendations
- **March/April**: Earlier, more time, risk spring storms and high rivers.
- **May**: Ideal balance. Grass available, rivers manageable.
- **June**: Good. Hotter, but comfortable.
- **July**: Late. Less time before winter; mountains may have snow.
- **August+**: Very difficult. High chance of winter storms in mountains.

---

## 6. HUNTING MECHANICS

### Hunting Rules
- Takes **1 full day** of travel time.
- Cannot hunt at landmarks, forts, or populated areas.
- Player controls a hunter that can move and aim in **8 directions**.
- Bullet hitboxes map to actual sprite graphics (precise collision).

### Animals (1985 Apple II — 6 Types)

| Animal | Shots | Attacks? | Food Yield | Habitat |
|--------|-------|----------|------------|---------|
| **Squirrel** | 1 | No | ~2-5 lbs | All |
| **Rabbit** | 1 | No | ~5-10 lbs | All |
| **Deer** | 1 | No | ~50-80 lbs | Eastern/forests |
| **Elk** | 1 | No | ~80-100 lbs | Western plains |
| **Bear** | 2 | No (runs) | ~100 lbs | Mountains |
| **Bison** | 3 | No (unless shot) | ~100 lbs | Great Plains |

> Earlier design considered 11 animals but Apple II memory limits forced 6.

### Hunting Limits
- **Carry limit**: 100 lbs per trip (Apple II). Later versions: 200 lbs.
- Intentional design: prevents single hunt from filling wagon; teaches waste management.
- If you shoot 400 lbs of bison, you can only carry 100 lbs back.

### Bullet Economics
- Each bullet costs **.10** (box of 20 = .00).
- One bullet can yield up to 100 lbs of food (bison/elk/bear).
- Hunting is **extremely cost-effective** vs. buying food at forts.

### Terrain Affects Hunting
The original manual states: *The type and abundance of animals relates to the terrain.*
- **Prairie/Plains**: Bison, elk, deer abundant.
- **Mountains**: Bear, elk, deer, small game.
- **Desert**: Mostly rabbits and squirrels — large game rare.

---

## 7. RIVER CROSSING

### Rivers in the Game
1. **Kansas River** (early, often has ferry)
2. **Big Blue River** (early-mid, smaller)
3. **Green River** (mid, optional by route)
4. **Snake River** (late, very dangerous)

### River Conditions
Each river has four modeled factors:
- **Depth** (feet): Changes with recent rainfall.
- **Width** (feet): Affects crossing time.
- **Swiftness** (current): Affects danger.
- **Bottom Type**: Smooth/firm, muddy, or rocky/uneven.

River depth depends on **recent weather**: rainy days before arrival = deeper, swifter rivers.

### Crossing Methods

| Method | Cost | When to Use | Risk |
|--------|------|-------------|------|
| **Ford** | Free | River <= 2.5 ft deep, slow current | Low at shallow. Catastrophic if > 3 ft. |
| **Caulk** | Free | River 2.5-4 ft, no ferry | Moderate. Wagon floats; can tip. |
| **Ferry** | -10 per person + oxen | Always if available and cash | Lowest risk. Rare accidents. |
| **Indian Guide** | Trade/fee (Snake River) | Reduces risk by **80%** | Guide picks best method, crosses immediately. |
| **Wait** | 1+ days | River too deep/swift | River may improve or worsen. |

### Fording Algorithm (Designer Notes)
- **< 2.5 ft**: Generally safe. Low chance minor losses.
- **2.5-3.0 ft**: Swamping — wagon gets wet. Lose 1 day drying. No supply/oxen loss.
- **> 3.0 ft**: Dangerous. Risk of tipping, supplies lost, oxen drowning, people drowning.
- **> 5.0 ft** (original draft): Catastrophic failure guaranteed. Revised to linear sliding scale.

### Failure Outcomes (Worst to Best)
1. **Total disaster**: Wagon overturns, multiple deaths, major supply loss.
2. **Major loss**: Some injuries, some oxen lost, significant supply loss.
3. **Minor loss**: Few supplies soaked/washed away, no deaths.
4. **Delay**: Crossing succeeds but costs extra time.
5. **Success**: Clean crossing.

### The Dalles / Endgame River
- **Barlow Toll Road**: Pay money, no mini-game, safer overland.
- **Raft Columbia River**: Free arcade-style mini-game dodging rocks. Hitting rocks = injuries/supply loss.

---

## 8. WEATHER / SEASON EFFECTS

### Seasonal Progression
The game tracks calendar month and computes weather daily.

| Season | Months | Effects |
|--------|--------|---------|
| **Spring** | Mar-May | Occasional rain, moderate temps, rivers high from snowmelt. |
| **Summer** | Jun-Aug | Hot in plains. Less rain. Rivers lower. Grass abundant. |
| **Autumn** | Sep-Nov | Cooling. Early snow in mountains. Grass diminishing. |
| **Winter** | Dec-Feb | Cold/snow in mountains/high plains. Travel slows. Health drops without clothes. Rivers may freeze. |

### Weather Conditions and Effects

| Weather | Travel Speed | Health | Rivers | Hunting |
|---------|-------------|--------|--------|---------|
| **Heavy Rain** | -20% | Slight decline | Depth+, Swiftness+ | Harder |
| **Snow** | -40% | Decline (w/o clothes) | May freeze/shallow | Very hard |
| **Blizzard** | Halt or -60% | Severe decline | — | Impossible |
| **Very Hot** | -10% | Decline (exhaustion) | — | Less active animals |
| **Very Cold** | -20% | Severe (w/o clothes) | Ice possible | Hard |
| **Cool/Warm** | Normal | Neutral | Normal | Normal |

### Clothing Importance
- Adequate clothing mitigates cold-weather health penalties.
- In winter/mountains, insufficient clothing causes rapid health drops.
- No explicit cold counter — baked into daily health calc in cold zones.

---

## 9. WIN / LOSE CONDITIONS

### Win Conditions
1. **Primary Win**: At least one living party member reaches **Willamette Valley / Oregon City**.
2. Game ends immediately upon arrival at final landmark.
3. In multiplayer, first arrival = winner; subsequent = survivors.

### Lose Conditions
1. **Total Party Kill**: All 5 members die.
2. **Stranded**: Wagon breaks + no spare + cannot trade + no money.
3. **Starvation**: Food = 0 for ~20+ days causes deaths.
4. **Winter Trapped**: Still in mountains when deep winter hits.
5. **River Disaster**: Lose all supplies/oxen in catastrophic crossing.

### Special States
- Wagon leader dies but others survive: game continues.
- All oxen die: stranded unless acquire more via trade.

---

## 10. SCORING SYSTEM

### Stage 1: Raw Score (Unscaled)

| Resource | Points |
|----------|--------|
| **Wagon** | 50 |
| **Each surviving ox** | 4 |
| **Each spare wagon part** | 2 |
| **Each set of clothes** | 2 |
| **Bullets** | 1 per 50 (no fractions) |
| **Food** | 1 per 25 lbs (no fractions) |
| **Cash** | 1 per  (no fractions) |
| **Person in Good health** | 500 |
| **Person in Fair health** | 400 |
| **Person in Poor health** | 300 |
| **Person in Very Poor health** | 200 |

### Stage 2: Occupation Multiplier

| Profession | Starting Cash | Multiplier |
|------------|---------------|------------|
| **Banker** | ,600 | x1 |
| **Carpenter** |  | x2 |
| **Farmer** |  | x3 |

### Example Score Calculation
A **Farmer** finishes with:
- 5 people alive in Good health: 5 x 500 = 2,500
- Wagon: 50
- 20 oxen: 20 x 4 = 80
- 9 spare parts: 9 x 2 = 18
- 1,975 lbs food: 1,975 / 25 = 79
- 11,800 bullets: 11,800 / 50 = 236
-  cash: 360 / 5 = 72
- **Raw total**: 3,035
- **Farmer x3**: **9,105 points**

### Maximums & Caps (Apple II Observed)
- **Oxen**: 20 max
- **Spare parts**: 3 of each type (9 total = 18 pts)
- **Food**: 2,000 lbs display cap (can exceed via wild fruit glitch)
- **Clothes**: No hard cap discovered (tested past 300)
- **Bullets**: Display rolls over at 9,999; tracks to ~15,600+; true cap possibly 65,535

---

## APPENDIX A: DAILY FOOD CONSUMPTION TABLE

| Party Size | Filling (3 lb/person) | Meager (2 lb/person) | Bare Bones (1 lb/person) |
|------------|----------------------|----------------------|--------------------------|
| 1 | 3 lbs/day | 2 lbs/day | 1 lb/day |
| 2 | 6 lbs/day | 4 lbs/day | 2 lbs/day |
| 3 | 9 lbs/day | 6 lbs/day | 3 lbs/day |
| 4 | 12 lbs/day | 8 lbs/day | 4 lbs/day |
| 5 | 15 lbs/day | 10 lbs/day | 5 lbs/day |

---

## APPENDIX B: STARTING STRATEGIES BY PROFESSION

### Banker (,600)
- 9 yoke (18 oxen), 2,000 lbs food, 20 clothes, 3 of each part, 20 boxes bullets.
- Strategy: Buy everything. Hunt for fun. Take ferries. Easy mode.

### Carpenter ()
- 5 yoke (10 oxen), 1,000 lbs food, 15 clothes, 2 of each part, 15 boxes bullets.
- Strategy: Balanced. Hunt to supplement. Be careful with ferries.

### Farmer () — Hard Mode / Score Mode
- 3 yoke (6 oxen), **0 food**, 15 clothes, 2 of each part, 20 boxes bullets.
- Strategy: Hunt immediately for food. Trade strategically. Conserve cash.

---

## APPENDIX C: SOURCES

- R. Philip Bouchard (lead designer): https://www.philipbouchard.com/oregon-trail/
- StrategyWiki — The Oregon Trail: https://strategywiki.org/wiki/The_Oregon_Trail
- Perfect Pacman Perfect Score Analysis: https://perfectpacman.com/2025/08/23/oregon-trail/
- MECC Original Manual (Apple II): MECC-A157 documentation
- Historical Trail Records: Oregon-California Trails Association (OCTA)

