"""
@File: config.py
"""
import os
from dotenv import load_dotenv

load_dotenv()
RIOT_KEY = os.getenv("RIOT_API_KEY")
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SENTRY_DSN = os.getenv("SENTRY_DSN")

# The Server Dictionary for RIOT API
PLATFORM_ROUTING = {
    # Americas
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    # Asia
    "kr": "asia", "jp1": "asia",
    # Europe
    "eun1": "europe", "euw1": "europe", "tr1": "europe", "ru": "europe", "me1": "europe",
    # SEA
    "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea"
}

# Riot API Queue ID Mapping
QUEUE_MAP = {
    400: "Normal Draft", 420: "Ranked Solo/Duo", 430: "Normal Blind",
    440: "Ranked Flex", 450: "ARAM", 490: "Quickplay",
    700: "Clash", 900: "URF", 1700: "Arena"
}

# Rank
RANK_WEIGHTS = {
    "IRON": 1, "BRONZE": 2, "SILVER": 3, "GOLD": 4,
    "PLATINUM": 5, "EMERALD": 6, "DIAMOND": 7,
    "MASTER": 8, "GRANDMASTER": 9, "CHALLENGER": 10
}

# The Standard Summoner Spells
SUMMONER_SPELLS = {
    "1": "Cleanse", "3": "Exhaust", "4": "Flash",
    "6": "Ghost", "7": "Heal", "11": "Smite",
    "12": "Teleport", "13": "Clarity", "14": "Ignite",
    "21": "Barrier", "32": "Snowball"
}

# The AI magic numbers
FIRST_TIME_THRESHOLD = 10000
FIRST_TIME_PENALTY = 0.015
OTP_THRESHOLD = 100000
OTP_MAX_CAP = 500000
OTP_BUFF_MULTIPLIER = 0.01
BASE_WINRATE = 0.50

# ML Hyperparameters
EMBEDDING_DIM = 16
DROPOUT_RATE = 0.25

# The Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Models
MODEL_PATH = os.path.join(BASE_DIR, 'data/models', 'Lol_draft_predictor.safetensors')
ENCODER_PATH = os.path.join(BASE_DIR, 'data/models', 'champion_encoder.json')
SCALER_PATH = os.path.join(BASE_DIR, 'data', 'models', 'scaler.pkl')

# External Factor
SYNERGY_PATH    = os.path.join(BASE_DIR, 'data', 'static', 'Synergy_Matrix.json')
META_PATH       = os.path.join(BASE_DIR, 'data', 'static', 'Meta_Champions.json')
ROLES_PATH      = os.path.join(BASE_DIR, 'data', 'static', 'Champion_Roles.json')

# RIOT Data Caches
CHAMP_DICT_PATH = os.path.join(BASE_DIR, 'data', 'training', 'champion_cache.json')
KEYSTONE_RUNES_PATH = os.path.join(BASE_DIR, 'data', 'static', 'Keystone_Runes.json')
ITEM_DICT_PATH  = os.path.join(BASE_DIR, 'data', 'static', 'Item_Dictionary.json')