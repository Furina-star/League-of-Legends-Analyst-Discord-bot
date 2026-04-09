"""
This is where AI logic functions are stored, such as loading the model, preprocessing the input, and calculating the win probabilities.
"""

import torch
import torch.nn as nn
import skops.io as sio  # 🛡️ SECURE: Replaces joblib!
from safetensors.torch import load_model  # 🛡️ SECURE: Replaces torch.load!
import json
from itertools import combinations
import logging
from typing import List, Tuple, Dict, Any
import config

# Get the logging system
logger = logging.getLogger(__name__)

# Define the Model Architecture
class Model(nn.Module):
    def __init__(self, num_champions):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=num_champions, embedding_dim=16)

        self.net = nn.Sequential(
            nn.Linear(172, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.25),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.25),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.25),

            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x, synergy_scores, meta_rates):
        embedded = self.embedding(x)
        flattened = embedded.view(x.size(0), -1)
        combined = torch.cat((flattened, synergy_scores, meta_rates), dim=1)
        return self.net(combined)

def calculate_team_synergy(team_champs: List[str], synergy_matrix: Dict[str, Any]) -> float:
    score = 0.0
    for duo in combinations(sorted(team_champs), 2):
        pair_key = f"{duo[0]}-{duo[1]}"

        if pair_key in synergy_matrix:
            # If the pair has a 54% winrate, (0.54 - 0.50) = +0.04 points
            # If the pair has a 45% winrate, (0.45 - 0.50) = -0.05 points
            score += (synergy_matrix[pair_key]["winrate"] - config.BASE_WINRATE)

    return score

# Wrapper Class
class LeagueAI:
    # This function set up and load Label encoder and the model
    def __init__(self,
                 model_path: str = "models/league_model.safetensors",
                 encoder_path: str = "models/encoder.skops",
                 synergy_path: str = config.SYNERGY_PATH,
                 meta_path: str = config.META_PATH):

        logger.info("Loading AI Model, Label Encoder, Synergy Matrix, and Meta DB...")

        # Load the Label encoder using skops (Blocks malicious code execution)
        self.le = sio.load(encoder_path, trusted=True)

        # Convert classes to a Python set once for O(1) lightning-fast lookups
        self.known_classes = set(self.le.classes_)

        # Load the JSON databases
        with open(synergy_path, "r") as f:
            self.synergy_matrix = json.load(f)
        with open(meta_path, "r") as f:
            self.meta_db = json.load(f)

        # Load PyTorch using safetensors
        # We calculate num_champs dynamically from the LabelEncoder length so we don't need the unsafe .pth dict!
        num_champs = len(self.le.classes_)
        self.model = Model(num_champs)
        load_model(self.model, model_path)
        self.model.eval()

        logger.info("AI Model and Label Encoder loaded successfully.")

    # This function takes in a draft dictionary, preprocesses it, and returns the predicted win probability for the blue team
    def predict_match(self, draft_dict: Dict[str, str]) -> Tuple[float, float, float, float]:
        correct_order = [
            'blueTopChamp', 'blueJungleChamp', 'blueMiddleChamp', 'blueADCChamp', 'blueSupportChamp',
            'redTopChamp', 'redJungleChamp', 'redMiddleChamp', 'redADCChamp', 'redSupportChamp'
        ]

        raw_champs = [draft_dict[col] for col in correct_order]
        processed_champs = [champ if champ in self.known_classes else 'Unknown' for champ in raw_champs]
        encoded_champs = self.le.transform(processed_champs)

        # Extract the raw champion names from the dictionary to calculate synergy.
        blue_champs = raw_champs[:5]
        red_champs = raw_champs[5:]

        # Calculate synergy scores for both teams using the synergy matrix
        blue_synergy = calculate_team_synergy(blue_champs, self.synergy_matrix)
        red_synergy = calculate_team_synergy(red_champs, self.synergy_matrix)

        meta_list = [self.meta_db.get(champ, config.BASE_WINRATE) for champ in raw_champs]

        # Convert everything to tensors
        x_tensor = torch.tensor([encoded_champs], dtype=torch.long)  # Notice the extra [] to make it a batch of 1
        synergy_tensor = torch.tensor([[blue_synergy, red_synergy]], dtype=torch.float32)
        meta_tensor = torch.tensor([meta_list], dtype=torch.float32)

        with torch.no_grad():
            prediction = self.model(x_tensor, synergy_tensor, meta_tensor).item()

        return prediction, 1.0 - prediction, blue_synergy, red_synergy

    # This function calculates the winrates
    def apply_hybrid_algorithm(self, base_blue_prob: float, blue_winrates: List[float],
                               red_winrates: List[float], blue_masteries: List[int],
                               red_masteries: List[int]) -> Tuple[float, float]:

        avg_blue = sum(blue_winrates) / len(blue_winrates) if blue_winrates else 50.0
        avg_red = sum(red_winrates) / len(red_winrates) if red_winrates else 50.0

        skill_modifier = ((avg_blue - avg_red) * 0.5) / 100.0

        # Use the Constants here!
        def calculate_mastery_modifier(masteries: List[int]) -> float:
            team_mod = 0.0
            for points in masteries:
                if points < config.FIRST_TIME_THRESHOLD:
                    team_mod -= config.FIRST_TIME_PENALTY
                elif points > config.OTP_THRESHOLD:
                    extra_points = min(points, config.OTP_MAX_CAP) - config.OTP_THRESHOLD
                    team_mod += (extra_points / 100000) * config.OTP_BUFF_MULTIPLIER
            return team_mod

        blue_x_factor = calculate_mastery_modifier(blue_masteries)
        red_x_factor = calculate_mastery_modifier(red_masteries)

        final_blue_prob = base_blue_prob + skill_modifier + blue_x_factor - red_x_factor
        final_blue_prob = max(0.01, min(0.99, final_blue_prob))

        return final_blue_prob, 1.0 - final_blue_prob