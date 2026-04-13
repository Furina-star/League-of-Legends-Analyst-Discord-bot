"""
This is where AI logic functions are stored, such as loading the model, preprocessing the input, and calculating the win probabilities.
"""

import torch
import torch.nn as nn
import skops.io as sio
from safetensors.torch import load_model
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
                 model_path: str = "models/Lol_draft_predictor.safetensors",
                 encoder_path: str = "models/label_encoder.skops",
                 synergy_path: str = config.SYNERGY_PATH,
                 meta_path: str = config.META_PATH):

        logger.info("Loading AI Model, Label Encoder, Synergy Matrix, and Meta DB...")

        # Load the Label encoder using skops (Blocks malicious code execution)
        safe_types = sio.get_untrusted_types(file=encoder_path)
        self.le = sio.load(encoder_path, trusted=safe_types)

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

        # Safe encoding that never crashes on 'unknown'
        encoded_list = [
            self.le.transform([champ])[0] if champ in self.known_classes else 0
            for champ in raw_champs
        ]

        processed_champs = [champ if champ in self.known_classes else 'Unknown' for champ in raw_champs]
        self.le.transform(processed_champs)

        # Extract the raw champion names from the dictionary to calculate synergy.
        blue_champs = raw_champs[:5]
        red_champs = raw_champs[5:]

        # Calculate synergy scores for both teams using the synergy matrix
        blue_synergy = calculate_team_synergy(blue_champs, self.synergy_matrix)
        red_synergy = calculate_team_synergy(red_champs, self.synergy_matrix)

        meta_list = [self.meta_db.get(champ, config.BASE_WINRATE) for champ in raw_champs]

        # Convert everything to tensors
        x_tensor = torch.tensor([encoded_list], dtype=torch.long)
        synergy_tensor = torch.tensor([[blue_synergy, red_synergy]], dtype=torch.float32)
        meta_tensor = torch.tensor([meta_list], dtype=torch.float32)

        with torch.no_grad():
            prediction = self.model(x_tensor, synergy_tensor, meta_tensor).item()

        return prediction, 1.0 - prediction, blue_synergy, red_synergy

    # This function calculates the winrates
    @staticmethod
    def apply_hybrid_algorithm(base_blue_prob: float, blue_winrates: List[float],
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

    # Sorts a list of champion names into standard [Top, Jgl, Mid, ADC, Sup] order
    @staticmethod
    def sort_draft_strings(draft_list: list, role_db: dict) -> list:
        positions = ['top', 'jungle', 'mid', 'adc', 'support']
        sorted_draft = ["Unknown"] * 5
        champ_roles = LeagueAI.get_champ_roles(role_db)

        # Keep track of champions that need flexible placement
        flex_champs = []

        #Strict one-role champions ONLY
        for champ in draft_list:
            roles = [r for r in champ_roles.get(champ, []) if r in positions]

            # If they only have 1 valid role and the slot is empty, lock them in
            if len(roles) == 1 and sorted_draft[positions.index(roles[0])] == "Unknown":
                sorted_draft[positions.index(roles[0])] = champ
            else:
                flex_champs.append((champ, roles))

        # Greedily assign flexible champions
        for champ, roles in flex_champs:
            placed = False
            for role in roles:
                idx = positions.index(role)
                if sorted_draft[idx] == "Unknown":
                    sorted_draft[idx] = champ
                    placed = True
                    break

            # True fallback (if team comp is completely chaotic/off-meta)
            if not placed and "Unknown" in sorted_draft:
                empty_idx = sorted_draft.index("Unknown")
                sorted_draft[empty_idx] = champ

        return sorted_draft

    # Rapidly simulates the current draft state against all valid champions for a target role,
    def suggest_champion(self, target_role: str, user_team: str, blue_dict: dict, red_dict: dict, role_db: dict):
        target_role = target_role.lower()
        champ_roles = self.get_champ_roles(role_db)

        # Filter the role database to get valid champions for the target role
        valid_champions = [
            champ for champ, roles in champ_roles.items()
            if target_role in roles
        ]
        results = []

        for champ in valid_champions:
            # Prevent suggesting a champion that is already picked
            if champ in blue_dict.values() or champ in red_dict.values():
                continue

            test_blue = blue_dict.copy()
            test_red = red_dict.copy()

            # Inject the test champion directly into the target dictionary slot
            if user_team.lower() == 'blue':
                test_blue[target_role] = champ
            else:
                test_red[target_role] = champ

            try:
                # Format exactly as the PyTorch model expects
                draft_dict = {
                    'blueTopChamp': test_blue.get('top', 'Unknown'),
                    'blueJungleChamp': test_blue.get('jungle', 'Unknown'),
                    'blueMiddleChamp': test_blue.get('mid', 'Unknown'),
                    'blueADCChamp': test_blue.get('adc', 'Unknown'),
                    'blueSupportChamp': test_blue.get('support', 'Unknown'),
                    'redTopChamp': test_red.get('top', 'Unknown'),
                    'redJungleChamp': test_red.get('jungle', 'Unknown'),
                    'redMiddleChamp': test_red.get('mid', 'Unknown'),
                    'redADCChamp': test_red.get('adc', 'Unknown'),
                    'redSupportChamp': test_red.get('support', 'Unknown')
                }

                prediction = self.predict_match(draft_dict)
                win_prob = prediction[0] if user_team.lower() == 'blue' else prediction[1]
                results.append((champ, win_prob))
            except Exception as e:
                logger.error(f"AI Coach Simulation failed for {champ}: {e}")
                continue

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:3]

    # Translates the Riot Category DB into a Champion-First DB
    @staticmethod
    def get_champ_roles(role_db: dict) -> dict:
        inverted = {}
        mapping = {
            "top": ["KNOWN_TOPS"],
            "jungle": ["KNOWN_JUNGLES"],
            "mid": ["KNOWN_MIDS"],
            "adc": ["PURE_ADCS", "FLEX_BOTS"],
            "support": ["PURE_SUPPORTS", "FLEX_SUPPORTS"]
        }
        for standard_role, categories in mapping.items():
            for cat in categories:
                for champ in role_db.get(cat, []):
                    if champ not in inverted:
                        inverted[champ] = []
                    inverted[champ].append(standard_role)
        return inverted