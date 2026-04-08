"""
@File: config.py
"""
import os

# The Server Dictionary for RIOT API
SERVER_TO_REGION = {
    "na1": "americas", "br1": "americas", "lan1": "americas", "las1": "americas", "oc1": "americas",
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
    "kr": "asia", "jp1": "asia", "sg2": "asia", "tw2": "asia", "vn2": "asia", "th2": "asia", "ph2": "asia"
}

# The AI magic numbers
FIRST_TIME_THRESHOLD = 10000
FIRST_TIME_PENALTY = 0.015
OTP_THRESHOLD = 100000
OTP_MAX_CAP = 500000
OTP_BUFF_MULTIPLIER = 0.01
BASE_WINRATE = 0.50

# The Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'Lol_draft_predictor.pth')
ENCODER_PATH = os.path.join(BASE_DIR, 'models', 'label_encoder.pkl')
SYNERGY_PATH = os.path.join(BASE_DIR, 'data', 'Synergy_Matrix.json')
META_PATH = os.path.join(BASE_DIR, 'data', 'Meta_Champions.json')
CHAMP_DICT_PATH = os.path.join(BASE_DIR, 'data', 'champion_dict.json')