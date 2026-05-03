"""Oregon Trail game data: landmarks, prices, events, and mechanics constants."""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum


class Profession(Enum):
    """Starting profession affecting initial money."""
    BANKER = "Banker from Boston"
    CARPENTER = "Carpenter from Ohio"
    FARMER = "Farmer from Illinois"


class Pace(Enum):
    """Travel pace settings."""
    STEADY = "Steady"
    STRENUOUS = "Strenuous"
    GRUELING = "Grueling"


class Rations(Enum):
    """Food ration settings."""
    FILLING = "Filling"
    MEAGER = "Meager"
    BARE_BONES = "Bare Bones"


class Weather(Enum):
    """Weather conditions affecting travel and health."""
    VERY_HOT = "Very Hot"
    HOT = "Hot"
    WARM = "Warm"
    COOL = "Cool"
    COLD = "Cold"
    VERY_COLD = "Very Cold"
    RAIN = "Heavy Rain"
    SNOW = "Snow"


class Terrain(Enum):
    """Terrain types between landmarks."""
    PRAIRIE = "Prairie"
    MOUNTAINS = "Mountains"
    DESERT = "Desert"
    FOREST = "Forest"


class HealthStatus(Enum):
    """Health status for players and overall party."""
    HEALTHY = "Healthy"
    FAIR = "Fair"
    POOR = "Poor"
    VERY_POOR = "Very Poor"
    DEAD = "Dead"


# ---------------------------------------------------------------------------
# Starting conditions by profession
# ---------------------------------------------------------------------------
PROFESSION_STARTING_MONEY: Dict[Profession, int] = {
    Profession.BANKER: 1600,
    Profession.CARPENTER: 800,
    Profession.FARMER: 400,
}

PROFESSION_STARTING_POINTS: Dict[Profession, int] = {
    Profession.BANKER: 1,
    Profession.CARPENTER: 2,
    Profession.FARMER: 3,
}

# ---------------------------------------------------------------------------
# General Store Prices (at Independence, MO)
# ---------------------------------------------------------------------------
STORE_PRICES: Dict[str, float] = {
    "oxen": 40,              # per yoke (2 oxen)
    "food": 0.20,            # per pound (original 1985 price)
    "clothing": 10,          # per set
    "bullets": 2,            # per box (20 bullets)
    "wagon_wheel": 10,
    "wagon_axle": 10,
    "wagon_tongue": 10,
}

# Maximum spare parts of each type (original cap)
MAX_SPARE_PARTS = 3

# Barlow Toll Road cost at The Dalles
BARLOW_TOLL_ROAD_COST = 10

# Fort prices increase as you travel west (multiplier)
FORT_PRICE_MULTIPLIERS: Dict[str, float] = {
    "Fort Kearney": 1.25,
    "Fort Laramie": 1.50,
    "Fort Bridger": 1.75,
    "Fort Hall": 2.00,
    "Fort Boise": 2.25,
    "Fort Walla Walla": 2.50,
}

# ---------------------------------------------------------------------------
# Trail Landmarks
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Landmark:
    name: str
    miles_from_start: int
    is_river: bool = False
    is_fort: bool = False
    description: str = ""


LANDMARKS: List[Landmark] = [
    Landmark("Independence, Missouri", 0, description="The jumping-off place for the Oregon Trail."),
    Landmark("Kansas River Crossing", 102, is_river=True, description="A wide, swift river."),
    Landmark("Big Blue River Crossing", 185, is_river=True, description="Often treacherous after rains."),
    Landmark("Fort Kearney", 304, is_fort=True, description="The first fort on the trail. Supplies available."),
    Landmark("Chimney Rock", 554, description="A towering rock formation visible for miles."),
    Landmark("Fort Laramie", 640, is_fort=True, description="A major trading post and rest stop."),
    Landmark("Independence Rock", 830, description="The halfway point. Reach it by July 4th!"),
    Landmark("South Pass", 932, description="The Continental Divide."),
    Landmark("Fort Bridger", 1069, is_fort=True, description="A small fur-trading post."),
    Landmark("Green River Crossing", 1132, is_river=True, description="Wide and dangerous."),
    Landmark("Soda Springs", 1235, description="Bubbling mineral springs."),
    Landmark("Fort Hall", 1300, is_fort=True, description="A Hudson's Bay Company outpost."),
    Landmark("Snake River Crossing", 1450, is_river=True, description="Many treacherous crossings."),
    Landmark("Fort Boise", 1534, is_fort=True, description="The last fort before the mountains."),
    Landmark("Blue Mountains", 1640, description="Steep, forested mountains."),
    Landmark("Fort Walla Walla", 1710, is_fort=True, description="A small fort in the valley."),
    Landmark("The Dalles", 1930, description="The end of the trail by land."),
    Landmark("Willamette Valley, Oregon", 2094, description="Your journey's end!"),
]

# Total trail distance
TOTAL_DISTANCE = LANDMARKS[-1].miles_from_start

# ---------------------------------------------------------------------------
# Scoring Constants
# ---------------------------------------------------------------------------
SCORE_SURVIVOR = 500
SCORE_OXEN = 4
SCORE_SPARE_PART = 2
SCORE_PER_5_DOLLARS = 1
SCORE_PER_50_FOOD = 1
SCORE_PER_CLOTHING = 2
SCORE_PER_BULLET = 0.1

# ---------------------------------------------------------------------------
# River Depth Thresholds (feet)
# ---------------------------------------------------------------------------
RIVER_FORD_SAFE_MAX = 2.5      # Safe to ford
RIVER_FORD_RISKY_MAX = 3.0     # Risky but possible
RIVER_CAULK_MAX = 8.0          # Caulking works up to this

# ---------------------------------------------------------------------------
# Ferry Cost (per person + per oxen)
# ---------------------------------------------------------------------------
FERRY_COST_PER_PERSON = 5
FERRY_COST_PER_OXEN = 3

# ---------------------------------------------------------------------------
# Pace Mechanics
# ---------------------------------------------------------------------------
PACE_MILES_PER_DAY: Dict[Pace, int] = {
    Pace.STEADY: 12,
    Pace.STRENUOUS: 16,
    Pace.GRUELING: 20,
}

PACE_HEALTH_IMPACT: Dict[Pace, int] = {
    Pace.STEADY: 0,
    Pace.STRENUOUS: -1,
    Pace.GRUELING: -3,
}

PACE_OXEN_WEAR: Dict[Pace, float] = {
    Pace.STEADY: 1.0,
    Pace.STRENUOUS: 1.5,
    Pace.GRUELING: 2.0,
}

# ---------------------------------------------------------------------------
# Rations Mechanics
# ---------------------------------------------------------------------------
RATIONS_FOOD_PER_PERSON_PER_DAY: Dict[Rations, int] = {
    Rations.FILLING: 3,
    Rations.MEAGER: 2,
    Rations.BARE_BONES: 1,
}

RATIONS_HEALTH_IMPACT: Dict[Rations, int] = {
    Rations.FILLING: 1,
    Rations.MEAGER: 0,
    Rations.BARE_BONES: -2,
}

# ---------------------------------------------------------------------------
# Weather Effects
# ---------------------------------------------------------------------------
WEATHER_SPEED_MODIFIER: Dict[Weather, float] = {
    Weather.VERY_HOT: 0.7,
    Weather.HOT: 0.9,
    Weather.WARM: 1.0,
    Weather.COOL: 1.0,
    Weather.COLD: 0.8,
    Weather.VERY_COLD: 0.6,
    Weather.RAIN: 0.7,
    Weather.SNOW: 0.4,
}

WEATHER_HEALTH_IMPACT: Dict[Weather, int] = {
    Weather.VERY_HOT: -1,
    Weather.HOT: 0,
    Weather.WARM: 0,
    Weather.COOL: 0,
    Weather.COLD: -1,
    Weather.VERY_COLD: -2,
    Weather.RAIN: 0,
    Weather.SNOW: -1,
}

# Season-based weather probabilities (by month)
# Each month has weighted choices for weather
MONTHLY_WEATHER_WEIGHTS: Dict[int, List[Tuple[Weather, int]]] = {
    3: [(Weather.COLD, 3), (Weather.COOL, 5), (Weather.WARM, 2)],          # March
    4: [(Weather.COLD, 1), (Weather.COOL, 5), (Weather.WARM, 3), (Weather.RAIN, 1)],
    5: [(Weather.COOL, 2), (Weather.WARM, 5), (Weather.HOT, 2), (Weather.RAIN, 1)],
    6: [(Weather.WARM, 3), (Weather.HOT, 4), (Weather.VERY_HOT, 2), (Weather.RAIN, 1)],
    7: [(Weather.HOT, 4), (Weather.VERY_HOT, 4), (Weather.WARM, 2)],
    8: [(Weather.HOT, 5), (Weather.VERY_HOT, 3), (Weather.WARM, 2)],
    9: [(Weather.WARM, 4), (Weather.COOL, 3), (Weather.HOT, 2), (Weather.RAIN, 1)],
    10: [(Weather.COOL, 4), (Weather.COLD, 3), (Weather.WARM, 2), (Weather.RAIN, 1)],
    11: [(Weather.COLD, 5), (Weather.VERY_COLD, 3), (Weather.COOL, 1), (Weather.SNOW, 1)],
    12: [(Weather.VERY_COLD, 5), (Weather.COLD, 4), (Weather.SNOW, 1)],
}

# ---------------------------------------------------------------------------
# Terrain between landmarks
# ---------------------------------------------------------------------------
TERRAIN_SEGMENTS: List[Tuple[int, int, Terrain]] = [
    (0, 304, Terrain.PRAIRIE),       # Independence to Fort Kearney
    (304, 640, Terrain.PRAIRIE),     # Fort Kearney to Fort Laramie
    (640, 932, Terrain.MOUNTAINS),   # Fort Laramie to South Pass
    (932, 1132, Terrain.DESERT),     # South Pass to Green River
    (1132, 1300, Terrain.MOUNTAINS), # Green River to Fort Hall
    (1300, 1534, Terrain.DESERT),    # Fort Hall to Fort Boise
    (1534, 1710, Terrain.MOUNTAINS), # Fort Boise to Fort Walla Walla
    (1710, 1830, Terrain.FOREST),    # Fort Walla Walla to The Dalles
    (1830, 2040, Terrain.MOUNTAINS), # The Dalles to Willamette Valley
]

# ---------------------------------------------------------------------------
# Random Trail Events
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TrailEvent:
    id: str
    description: str
    base_probability: float  # per day, 0.0-1.0
    terrain_multipliers: Dict[Terrain, float]
    weather_multipliers: Dict[Weather, float]
    requires_supplies: bool = False  # Can be mitigated by having spare parts


TRAIL_EVENTS: List[TrailEvent] = [
    TrailEvent(
        id="broken_wheel",
        description="A wagon wheel has broken!",
        base_probability=0.03,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 1.5, Terrain.DESERT: 1.3, Terrain.FOREST: 1.2},
        weather_multipliers={Weather.RAIN: 1.5, Weather.SNOW: 1.8, Weather.HOT: 1.0, Weather.COLD: 1.2},
        requires_supplies=True,
    ),
    TrailEvent(
        id="broken_axle",
        description="A wagon axle has snapped!",
        base_probability=0.02,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 2.0, Terrain.DESERT: 1.5, Terrain.FOREST: 1.3},
        weather_multipliers={Weather.RAIN: 1.3, Weather.SNOW: 1.5, Weather.HOT: 1.0, Weather.COLD: 1.1},
        requires_supplies=True,
    ),
    TrailEvent(
        id="broken_tongue",
        description="The wagon tongue has broken!",
        base_probability=0.02,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 1.8, Terrain.DESERT: 1.4, Terrain.FOREST: 1.2},
        weather_multipliers={Weather.RAIN: 1.2, Weather.SNOW: 1.4, Weather.HOT: 1.0, Weather.COLD: 1.1},
        requires_supplies=True,
    ),
    TrailEvent(
        id="oxen_injured",
        description="One of the oxen has been injured.",
        base_probability=0.02,
        terrain_multipliers={Terrain.PRAIRIE: 0.8, Terrain.MOUNTAINS: 2.0, Terrain.DESERT: 1.5, Terrain.FOREST: 1.3},
        weather_multipliers={Weather.RAIN: 1.3, Weather.SNOW: 1.5, Weather.HOT: 1.2, Weather.COLD: 1.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="oxen_died",
        description="One of the oxen has died!",
        base_probability=0.01,
        terrain_multipliers={Terrain.PRAIRIE: 0.5, Terrain.MOUNTAINS: 2.5, Terrain.DESERT: 2.0, Terrain.FOREST: 1.5},
        weather_multipliers={Weather.RAIN: 1.0, Weather.SNOW: 2.0, Weather.HOT: 1.5, Weather.VERY_COLD: 2.5},
        requires_supplies=False,
    ),
    TrailEvent(
        id="thief",
        description="A thief came in the night and stole supplies!",
        base_probability=0.015,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 0.8, Terrain.DESERT: 1.2, Terrain.FOREST: 1.0},
        weather_multipliers={Weather.RAIN: 1.5, Weather.SNOW: 0.5, Weather.HOT: 0.8, Weather.COLD: 1.2},
        requires_supplies=False,
    ),
    TrailEvent(
        id="bad_water",
        description="The water at this campsite is bad.",
        base_probability=0.03,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 1.2, Terrain.DESERT: 2.0, Terrain.FOREST: 0.8},
        weather_multipliers={Weather.RAIN: 1.5, Weather.SNOW: 0.5, Weather.HOT: 2.0, Weather.COLD: 0.8},
        requires_supplies=False,
    ),
    TrailEvent(
        id="lost_trail",
        description="You have lost the trail and wasted a day searching.",
        base_probability=0.02,
        terrain_multipliers={Terrain.PRAIRIE: 0.5, Terrain.MOUNTAINS: 2.0, Terrain.DESERT: 1.8, Terrain.FOREST: 1.5},
        weather_multipliers={Weather.RAIN: 2.0, Weather.SNOW: 3.0, Weather.HOT: 0.8, Weather.COLD: 1.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="find_wild_fruit",
        description="You found wild fruit and berries.",
        base_probability=0.02,
        terrain_multipliers={Terrain.PRAIRIE: 0.5, Terrain.MOUNTAINS: 1.0, Terrain.DESERT: 0.2, Terrain.FOREST: 3.0},
        weather_multipliers={Weather.RAIN: 1.0, Weather.SNOW: 0.0, Weather.HOT: 1.5, Weather.WARM: 2.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="wrong_path",
        description="You took a wrong path and had to backtrack.",
        base_probability=0.015,
        terrain_multipliers={Terrain.PRAIRIE: 0.5, Terrain.MOUNTAINS: 2.5, Terrain.DESERT: 2.0, Terrain.FOREST: 1.8},
        weather_multipliers={Weather.RAIN: 1.5, Weather.SNOW: 2.5, Weather.HOT: 0.8, Weather.COLD: 1.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="grave_site",
        description="You pass a grave site. 'Here lies someone who didn't make it.'",
        base_probability=0.01,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 1.5, Terrain.DESERT: 1.2, Terrain.FOREST: 1.0},
        weather_multipliers={Weather.RAIN: 1.0, Weather.SNOW: 1.0, Weather.HOT: 1.0, Weather.COLD: 1.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="rough_trail",
        description="The trail ahead is very rough.",
        base_probability=0.03,
        terrain_multipliers={Terrain.PRAIRIE: 0.5, Terrain.MOUNTAINS: 2.0, Terrain.DESERT: 1.5, Terrain.FOREST: 1.5},
        weather_multipliers={Weather.RAIN: 2.0, Weather.SNOW: 2.5, Weather.HOT: 1.0, Weather.COLD: 1.2},
        requires_supplies=False,
    ),
    TrailEvent(
        id="heavy_fog",
        description="Heavy fog rolls in. You can barely see the trail.",
        base_probability=0.02,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 2.0, Terrain.DESERT: 0.3, Terrain.FOREST: 1.5},
        weather_multipliers={Weather.RAIN: 2.0, Weather.SNOW: 0.5, Weather.HOT: 0.2, Weather.COLD: 1.5},
        requires_supplies=False,
    ),
    TrailEvent(
        id="blizzard",
        description="A terrible blizzard strikes!",
        base_probability=0.01,
        terrain_multipliers={Terrain.PRAIRIE: 0.5, Terrain.MOUNTAINS: 3.0, Terrain.DESERT: 0.0, Terrain.FOREST: 1.0},
        weather_multipliers={Weather.RAIN: 0.0, Weather.SNOW: 5.0, Weather.HOT: 0.0, Weather.VERY_COLD: 4.0, Weather.COLD: 2.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="no_grass",
        description="There is no grass for the oxen here.",
        base_probability=0.02,
        terrain_multipliers={Terrain.PRAIRIE: 0.3, Terrain.MOUNTAINS: 1.5, Terrain.DESERT: 3.0, Terrain.FOREST: 0.5},
        weather_multipliers={Weather.RAIN: 0.5, Weather.SNOW: 2.0, Weather.HOT: 2.0, Weather.VERY_HOT: 3.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="abandoned_wagon",
        description="You find an abandoned wagon by the trail.",
        base_probability=0.01,
        terrain_multipliers={Terrain.PRAIRIE: 1.0, Terrain.MOUNTAINS: 1.5, Terrain.DESERT: 2.0, Terrain.FOREST: 0.8},
        weather_multipliers={Weather.RAIN: 1.0, Weather.SNOW: 1.0, Weather.HOT: 1.0, Weather.COLD: 1.0},
        requires_supplies=False,
    ),
    TrailEvent(
        id="npc_trade",
        description="You meet a fellow traveler who wants to trade.",
        base_probability=0.015,
        terrain_multipliers={Terrain.PRAIRIE: 1.5, Terrain.MOUNTAINS: 0.8, Terrain.DESERT: 0.5, Terrain.FOREST: 1.0},
        weather_multipliers={Weather.RAIN: 0.5, Weather.SNOW: 0.3, Weather.HOT: 1.0, Weather.WARM: 1.5},
        requires_supplies=False,
    ),
]

# ---------------------------------------------------------------------------
# Illness Events
# ---------------------------------------------------------------------------
ILLNESS_TYPES = [
    "exhaustion",
    "dysentery",
    "cholera",
    "measles",
    "typhoid",
    "snakebite",
    "broken arm",
    "broken leg",
]

ILLNESS_BASE_PROBABILITY = 0.012  # per person per day

# Health modifiers affecting illness chance
ILLNESS_HEALTH_MULTIPLIERS: Dict[HealthStatus, float] = {
    HealthStatus.HEALTHY: 0.3,
    HealthStatus.FAIR: 0.7,
    HealthStatus.POOR: 1.5,
    HealthStatus.VERY_POOR: 3.0,
    HealthStatus.DEAD: 0.0,
}

# Weather illness multipliers
ILLNESS_WEATHER_MULTIPLIERS: Dict[Weather, float] = {
    Weather.VERY_HOT: 1.5,
    Weather.HOT: 1.2,
    Weather.WARM: 1.0,
    Weather.COOL: 1.0,
    Weather.COLD: 1.5,
    Weather.VERY_COLD: 2.0,
    Weather.RAIN: 1.8,
    Weather.SNOW: 2.2,
}

# ---------------------------------------------------------------------------
# Hunting Mechanics
# ---------------------------------------------------------------------------
HUNTING_BULLETS_PER_SHOT = 1
HUNTING_MAX_FOOD_PER_HUNT = 100  # lbs
HUNTING_ANIMALS: Dict[str, Dict[str, int]] = {
    "rabbit": {"food": 5, "difficulty": 1},
    "squirrel": {"food": 3, "difficulty": 1},
    "deer": {"food": 60, "difficulty": 3},
    "elk": {"food": 90, "difficulty": 4},
    "bear": {"food": 400, "difficulty": 5},
    "buffalo": {"food": 800, "difficulty": 4},
}

# ---------------------------------------------------------------------------
# River Crossing
# ---------------------------------------------------------------------------
class RiverMethod(Enum):
    FORD = "Ford the river"
    CAULK = "Caulk the wagon and float"
    FERRY = "Take a ferry"
    WAIT = "Wait for conditions to improve"


# River depth categories and their base probabilities of mishap
RIVER_DEPTH_RANGES: Dict[str, Tuple[int, int]] = {
    "shallow": (1, 3),      # 1-3 feet
    "moderate": (4, 6),     # 4-6 feet
    "deep": (7, 10),        # 7-10 feet
    "very_deep": (11, 20),  # 11+ feet
}

# Base mishap probabilities by method and depth (chance of something going wrong)
RIVER_MISHAP_CHANCES: Dict[str, Dict[str, float]] = {
    "shallow": {"ford": 0.05, "caulk": 0.02, "ferry": 0.0, "wait": 0.0},
    "moderate": {"ford": 0.20, "caulk": 0.10, "ferry": 0.0, "wait": 0.0},
    "deep": {"ford": 0.50, "caulk": 0.25, "ferry": 0.0, "wait": 0.0},
    "very_deep": {"ford": 0.80, "caulk": 0.40, "ferry": 0.0, "wait": 0.0},
}

# River crossing outcome tier proportions.
# The roll range [0, 1-mishap_chance) is the "good zone" split into Perfect / Successful.
# The roll range [1-mishap_chance, 1] is the "bad zone" split into Difficult / Near Disaster / Disaster.
RIVER_OUTCOME_PROPORTIONS = {
    "perfect": 0.25,       # top fraction of good zone
    "successful": 0.75,    # rest of good zone
    "difficult": 0.375,    # lower fraction of bad zone
    "near_disaster": 0.375,  # middle fraction of bad zone
    "disaster": 0.25,      # worst fraction of bad zone
}



# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
# Points at end of game:
# - For each surviving party member: 500
# - For each oxen: 4
# - For each spare wagon part: 2
# - For every $5 remaining: 1
# - For every 50 lbs food: 1
# - For every set of clothing: 2
# - For every bullet: 0.1
# - Multiplied by profession multiplier (Banker=1, Carpenter=2, Farmer=3)

# ---------------------------------------------------------------------------
# Starting inventory defaults
# ---------------------------------------------------------------------------
STARTING_INVENTORY = {
    "oxen": 0,
    "food": 0,
    "clothing": 0,
    "bullets": 0,
    "wagon_wheels": 0,
    "wagon_axles": 0,
    "wagon_tongues": 0,
    "money": 0,
}

# Recommended starting purchases (for reference / AI hints)
RECOMMENDED_STARTING_PURCHASES = {
    "oxen": 6,           # 3 yokes
    "food": 400,         # lbs
    "clothing": 8,       # sets
    "bullets": 4,        # boxes (80 bullets)
    "wagon_wheels": 1,
    "wagon_axles": 1,
    "wagon_tongues": 1,
}

# ---------------------------------------------------------------------------
# Auto-advance defaults
# ---------------------------------------------------------------------------
DEFAULT_AUTO_ADVANCE_INTERVAL = 15  # seconds
DEFAULT_DECISION_TIMEOUT_AUTO = 45   # seconds when auto-advancing
DEFAULT_DECISION_TIMEOUT_PAUSED = 60  # seconds when host has paused

# ---------------------------------------------------------------------------
# Era-appropriate NPC names (1840s United States)
# ---------------------------------------------------------------------------
NPC_MALE_NAMES = [
    "John", "William", "James", "George", "Charles", "Henry", "Joseph", "Thomas",
    "Samuel", "David", "Benjamin", "Daniel", "Robert", "Edward", "Andrew", "Jacob",
    "Nathaniel", "Elijah", "Isaac", "Abraham", "Joshua", "Matthew", "Christopher",
    "Nathan", "Jonathan", "Noah", "Aaron", "Adam", "Alexander", "Allen", "Ambrose",
    "Amos", "Anthony", "Archibald", "Asa", "Augustus", "Avery", "Barnabas", "Bartholomew",
    "Caleb", "Calvin", "Chester", "Clarence", "Clement", "Cornelius", "Cyrus", "Darius",
    "Dennis", "Dudley", "Eben", "Ebenezer", "Edgar", "Edmund", "Elias", "Ellis",
    "Elmer", "Emmett", "Enoch", "Ephraim", "Erastus", "Ezekiel", "Ezra", "Fletcher",
    "Francis", "Franklin", "Frederick", "Gideon", "Gilbert", "Harrison", "Harvey",
    "Hiram", "Homer", "Horace", "Horatio", "Hosea", "Howard", "Hubert", "Hudson",
    "Hugh", "Hyrum", "Ira", "Irving", "Jasper", "Jedediah", "Jefferson", "Jeremiah",
    "Jesse", "Josiah", "Jotham", "Lafayette", "Lemuel", "Leonard", "Levi", "Lewis",
    "Linus", "Lorenzo", "Luther", "Martin", "Melville", "Merritt", "Micajah", "Miles",
    "Milford", "Milton", "Monroe", "Mordecai", "Moses", "Nehemiah", "Nelson", "Newton",
    "Obadiah", "Oliver", "Orlando", "Orson", "Oscar", "Otis", "Owen", "Parley",
    "Perry", "Phineas", "Reuben", "Roderick", "Roscoe", "Rufus", "Sampson", "Seth",
    "Seymour", "Silas", "Simeon", "Solomon", "Thaddeus", "Theodore", "Titus", "Tobias",
    "Ulysses", "Uriah", "Vernon", "Virgil", "Wallace", "Ward", "Warren", "Washington",
    "Wesley", "Wilbur", "Wiley", "Willard", "Wilson", "Winfield", "Zachariah", "Zebulon",
]

NPC_FEMALE_NAMES = [
    "Mary", "Elizabeth", "Sarah", "Margaret", "Martha", "Catherine", "Ann", "Jane",
    "Emily", "Harriet", "Charlotte", "Frances", "Susan", "Rebecca", "Lucy", "Nancy",
    "Lydia", "Hannah", "Rachel", "Esther", "Abigail", "Ruth", "Alice", "Clara",
    "Ella", "Florence", "Grace", "Helen", "Ida", "Julia", "Laura", "Lillian",
    "Mabel", "Nellie", "Olive", "Pearl", "Rose", "Stella", "Theresa", "Victoria",
    "Ada", "Agnes", "Amanda", "Amelia", "Angeline", "Augusta", "Aurelia", "Belinda",
    "Belle", "Bertha", "Betsy", "Cecilia", "Celia", "Christina", "Cindy", "Clementine",
    "Cordelia", "Cornelia", "Daisy", "Delia", "Della", "Dinah", "Dolly", "Dorcas",
    "Dorothy", "Edith", "Eleanor", "Eliza", "Ellen", "Elsie", "Emeline", "Emma",
    "Emmeline", "Estelle", "Ethel", "Eunice", "Eveline", "Fanny", "Fern", "Geneva",
    "Genevieve", "Georgiana", "Gertrude", "Gladys", "Gloria", "Hattie", "Henrietta",
    "Hester", "Hilda", "Hortense", "Inez", "Irene", "Iris", "Isabella", "Jeanette",
    "Jemima", "Jenny", "Josephine", "Josie", "Juanita", "Katherine", "Keziah", "Lavinia",
    "Leah", "Lena", "Letitia", "Lorena", "Lottie", "Louisa", "Lucretia", "Lydia",
    "Mae", "Mahala", "Malinda", "Marcy", "Maria", "Marion", "Marjorie", "Martha",
    "Mattie", "Melinda", "Melissa", "Melvina", "Minerva", "Minnie", "Miranda", "Myra",
    "Nancy", "Naomi", "Narcissa", "Nettie", "Nora", "Norma", "Octavia", "Ophelia",
    "Orpha", "Pansy", "Patience", "Pauline", "Permelia", "Persis", "Phoebe", "Polly",
    "Priscilla", "Prudence", "Roxana", "Ruth", "Sabrina", "Selma", "Serena", "Sophronia",
    "Submit", "Susanna", "Sybil", "Sylvia", "Tabitha", "Theodora", "Tillie", "Tryphena",
    "Unity", "Ursula", "Veronica", "Vesta", "Violet", "Virginia", "Wilhelmina", "Winifred",
    "Zelda", "Zilpah", "Zina", "Zora",
]

# ---------------------------------------------------------------------------
# Historical Wagon Party Names
# ---------------------------------------------------------------------------
HISTORICAL_WAGON_NAMES = [
    "The Bidwell-Bartleson Party", "The Peoria Party", "The Great Emigration", 
    "The White-Hastings Party", "The Stephens-Townsend-Murphy Party", "The Barlow Road Pioneers", 
    "The Columbia River Company", "The Independent Colony", "The Pioneer Line", 
    "The Peoria Pioneers", "The Oregon Dragoons", "The Western Emigration Society", 
    "The Platte River Travelers", "The Willamette Wayfarers", "The Prairie Schooners", 
    "The Overland Company", "The Frontier Fellowship", "The Pacific Trailblazers", 
    "The Columbia Basin Pioneers", "The Snake River Settlers", "The Applegate Trail Party", 
    "The Green River Company", "The California Bound Company", "The Mormon Battalion", 
    "The Missouri River Emigrants", "The Salt Lake City Pioneers", "The Independence Wayfarers", 
    "The Blue Mountain Travelers", "The Council Bluffs Company", "The St. Joseph Pioneers", 
    "The Sweetwater Company", "The Fort Laramie Travelers", "The Great Plains Emigrants", 
    "The South Pass Wayfarers", "The Rocky Mountain Pioneers", "The Platte Valley Settlers", 
    "The Willamette Settlers", "The Continental Divide Company", "The Fort Hall Emigrants", 
    "The Columbia Gorge Travelers"
]


# ---------------------------------------------------------------------------
# Swear word / profanity filter
# ---------------------------------------------------------------------------
SWEAR_WORDS = {
    "ass", "asshole", "bastard", "bitch", "bullshit", "cock", "crap", "cum", "cunt",
    "damn", "dick", "dildo", "dipshit", "douche", "fag", "faggot", "fuck", "fucked",
    "fucker", "fucking", "goddamn", "hell", "jackass", "jerkoff", "motherfucker",
    "nigger", "piss", "prick", "pussy", "shit", "shitty", "slut", "tits", "twat",
    "whore", "wanker", "retard", "nigga", "chink", "spic", "kike", "wetback",
}

def contains_swear(text: str) -> bool:
    """Check if text contains any swear words (case-insensitive, word-boundary aware)."""
    import re
    lower = text.lower()
    # Also check for common leet substitutions
    normalized = lower.replace("0", "o").replace("1", "i").replace("3", "e").replace("4", "a").replace("5", "s").replace("7", "t").replace("$", "s")
    words = re.findall(r"\b\w+\b", normalized)
    for word in words:
        if word in SWEAR_WORDS:
            return True
        # Check without repeated letters (e.g., "fuuuck" -> "fuck")
        cleaned = re.sub(r"(.)\1+", r"\1", word)
        if cleaned in SWEAR_WORDS:
            return True
    return False

def filter_swear(text: str, replacement: str = "[censored]") -> str:
    """Replace swear words in text with a replacement string."""
    import re
    result = text
    # Normalize leet-speak so replacements catch obfuscated words
    result = result.lower().replace("0", "o").replace("1", "i").replace("3", "e").replace("4", "a").replace("5", "s").replace("7", "t").replace("$", "s")
    for word in SWEAR_WORDS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        result = pattern.sub(replacement, result)
    return result
