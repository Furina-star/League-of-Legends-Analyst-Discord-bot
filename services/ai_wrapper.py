"""
This is where AI logic functions are stored, such as loading the model, preprocessing the input, and calculating the win probabilities.
"""

import torch
import torch.nn as nn
from safetensors.torch import load_model
import json
from itertools import combinations
import logging
from typing import List, Tuple, Dict, Any
from config import MODEL_PATH, ENCODER_PATH, SCALER_PATH
import joblib
import warnings

# Get the logging system
logger = logging.getLogger(__name__)

# Suppress sklearn feature name warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# Define the Model Architecture
class Model(nn.Module):
    # num_extra_features is now 32
    def __init__(self, num_champions, embedding_dim=16, num_champs_in_match=10,
                 num_extra_features=32, dropout_rate=0.25):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=num_champions, embedding_dim=embedding_dim)

        input_size = (num_champs_in_match * embedding_dim) + num_extra_features

        self.net = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x, synergy_scores, meta_rates, masteries, ranks):
        embedded = self.embedding(x)
        flattened = embedded.view(x.size(0), -1)
        # Concatenate all 5 features
        combined = torch.cat((flattened, synergy_scores, meta_rates, masteries, ranks), dim=1)
        return self.net(combined)

def calculate_team_synergy(team_champs: List[str], synergy_matrix: Dict[str, Any], base_winrate: float) -> float:
    score = 0.0
    for duo in combinations(sorted(team_champs), 2):
        pair_key = f"{duo[0]}-{duo[1]}"

        if pair_key in synergy_matrix:
            score += (synergy_matrix[pair_key]["winrate"] - base_winrate)

    return score

# Wrapper Class
class LeagueAI:
    def __init__(self, bot_config: dict, synergy_matrix: dict, meta_db: dict,
                 model_path: str = MODEL_PATH,
                 encoder_path: str = ENCODER_PATH,
                 scaler_path: str = SCALER_PATH):

        self.config = bot_config
        self.ai_ready = False

        try:
            self.synergy_matrix = synergy_matrix
            self.meta_db = meta_db

            with open(encoder_path, "r") as f:
                self.champion_mapping = json.load(f)
            self.known_classes = list(self.champion_mapping.keys())

            self.scaler = joblib.load(scaler_path)

            num_champs = len(self.known_classes)
            self.model = Model(num_champions=num_champs, embedding_dim=self.config.get('EMBEDDING_DIM', 16),
                               dropout_rate=self.config.get('DROPOUT_RATE', 0.25))
            load_model(self.model, model_path)
            self.model.eval()
            self.ai_ready = True

        except Exception as e:
            logger.error(f"Failed to load AI Model or Encoders: {e}")

    # This function takes in a draft dictionary, preprocesses it, and returns the predicted win probability for the blue team
    def predict_match(self, draft_dict: Dict[str, str]) -> Tuple[float, float, float, float]:
        if not self.ai_ready:
            logger.warning("AI Model not ready. Returning default 50/50 prediction.")
            return 0.5, 0.5, 0.0, 0.0

        correct_order = [
            'blueTopChamp', 'blueJungleChamp', 'blueMiddleChamp', 'blueADCChamp', 'blueSupportChamp',
            'redTopChamp', 'redJungleChamp', 'redMiddleChamp', 'redADCChamp', 'redSupportChamp'
        ]

        raw_champs = [draft_dict[col] for col in correct_order]

        # Safe encoding that never crashes on 'unknown'
        encoded_list = [
            self.champion_mapping.get(champ, 0)
            for champ in raw_champs
        ]

        # Extract the raw champion names from the dictionary to calculate synergy.
        blue_champs = raw_champs[:5]
        red_champs = raw_champs[5:]

        # Calculate synergy scores for both teams using the synergy matrix
        blue_synergy = calculate_team_synergy(blue_champs, self.synergy_matrix, self.config['BASE_WINRATE'])
        red_synergy = calculate_team_synergy(red_champs, self.synergy_matrix, self.config['BASE_WINRATE'])

        meta_list = [self.meta_db.get(champ, self.config['BASE_WINRATE']) for champ in raw_champs]
        mastery_list = [draft_dict.get(f'mastery_{i}', 0) for i in range(10)]
        rank_list = [draft_dict.get(f'rank_{i}', 3) for i in range(10)]

        # Convert everything to tensors
        scaled_stats = self.scaler.transform([mastery_list + rank_list])[0]
        scaled_masteries = scaled_stats[:10].tolist()
        scaled_ranks = scaled_stats[10:].tolist()

        x_tensor = torch.tensor([encoded_list], dtype=torch.long)
        synergy_tensor = torch.tensor([[blue_synergy, red_synergy]], dtype=torch.float32)
        meta_tensor = torch.tensor([meta_list], dtype=torch.float32)
        mastery_tensor = torch.tensor([scaled_masteries], dtype=torch.float32)
        rank_tensor = torch.tensor([scaled_ranks], dtype=torch.float32)

        with torch.no_grad():
            prediction = self.model(x_tensor, synergy_tensor, meta_tensor, mastery_tensor, rank_tensor).item()

        return prediction, 1.0 - prediction, blue_synergy, red_synergy

    # Bridge for the /predict command to use the updated ML logic
    @staticmethod
    def apply_hybrid_algorithm(base_blue_prob: float, blue_winrates: list, red_winrates: list) -> Tuple[float, float]:

        # Default fallback if Riot API failed to pull stats
        if not blue_winrates or not red_winrates:
            logger.warning("Riot API failed to fetch live stats. Defaulting to pure ML base prediction.")
            return base_blue_prob, 1.0 - base_blue_prob

        # Calculate average winrates. If they are in 0-100 format, normalize to 0.0-1.0
        avg_blue_wr = float(sum(blue_winrates) / len(blue_winrates))
        if avg_blue_wr > 1.0: avg_blue_wr /= 100.0

        avg_red_wr = sum(red_winrates) / len(red_winrates)
        if avg_red_wr > 1.0: avg_red_wr /= 100.0

        # Calculate a winrate shift (allowing player skill to swing the ML prediction by up to 25%)
        skill_diff = avg_blue_wr - avg_red_wr
        final_blue_prob = base_blue_prob + (skill_diff * 0.25)

        # Clamp the results to valid probabilities (1% to 99%)
        final_blue_prob = max(0.01, min(0.99, final_blue_prob))

        return final_blue_prob, 1.0 - final_blue_prob

    # Bridge for the Live Tracker to use the updated ML logic
    def predict_live_match(self, draft_dict: Dict[str, Any]) -> Tuple[float, float, float, float]:
        return self.predict_match(draft_dict)

    # This function batch 50 drafts and send it through the model exactly once
    def predict_batch(self, draft_batch: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        if not self.ai_ready or not draft_batch:
            return [(0.5, 0.5) for _ in draft_batch]

        x_list, synergy_list, meta_list, mastery_list, rank_list = [], [], [], [], []

        for draft in draft_batch:
            # Champions
            encoded = []
            for i in range(10):
                champ_name = draft.get(f'champ_{i}', 'Unknown')
                encoded.append(self.champion_mapping.get(champ_name, self.champion_mapping.get('Unknown', 0)))
            x_list.append(encoded)

            # Synergy
            synergy_list.append([draft.get('blue_synergy', 0.5), draft.get('red_synergy', 0.5)])

            # Meta Rates
            meta_list.append([draft.get(f'meta_{i}', 0.5) for i in range(10)])

            # Masteries & Ranks (Default to 0 mastery, Gold/3 rank)
            m_row = [draft.get(f'mastery_{i}', 0) for i in range(10)]
            r_row = [draft.get(f'rank_{i}', 3) for i in range(10)]

            # Normalize the massive numbers just like in predict_match
            scaled_stats = self.scaler.transform([m_row + r_row])[0]
            mastery_list.append(scaled_stats[:10].tolist())
            rank_list.append(scaled_stats[10:].tolist())

        # Convert everything to PyTorch Tensors
        x_tensor = torch.tensor(x_list, dtype=torch.long)
        syn_tensor = torch.tensor(synergy_list, dtype=torch.float32)
        meta_tensor = torch.tensor(meta_list, dtype=torch.float32)
        mas_tensor = torch.tensor(mastery_list, dtype=torch.float32)
        rnk_tensor = torch.tensor(rank_list, dtype=torch.float32)

        with torch.no_grad():
            predictions = self.model(x_tensor, syn_tensor, meta_tensor, mas_tensor, rnk_tensor).squeeze().tolist()

        # single-item batches return a float, multi-item batches return a list
        if isinstance(predictions, float):
            predictions = [predictions]

        return [(p, 1.0 - p) for p in predictions]

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

    # Filters out invalid roles, picked champions, and banned champions
    @staticmethod
    def _get_valid_available_champions(target_role: str, role_db: dict, blue_dict: dict, red_dict: dict, banned_champs: list) -> list:
        champ_roles = LeagueAI.get_champ_roles(role_db)

        # Convert lists to a Set for lightning-fast O(1) lookups
        unavailable = set(blue_dict.values()) | set(red_dict.values()) | set(banned_champs)

        return [
            champ for champ, roles in champ_roles.items()
            if target_role in roles and champ not in unavailable
        ]

    # Constructs the exact dictionary format expected by the ML Model from the current draft state
    @staticmethod
    def _build_draft_input(blue_dict: dict, red_dict: dict) -> dict:
        return {
            'blueTopChamp': blue_dict.get('top', 'Unknown'),
            'blueJungleChamp': blue_dict.get('jungle', 'Unknown'),
            'blueMiddleChamp': blue_dict.get('mid', 'Unknown'),
            'blueADCChamp': blue_dict.get('adc', 'Unknown'),
            'blueSupportChamp': blue_dict.get('support', 'Unknown'),
            'redTopChamp': red_dict.get('top', 'Unknown'),
            'redJungleChamp': red_dict.get('jungle', 'Unknown'),
            'redMiddleChamp': red_dict.get('mid', 'Unknown'),
            'redADCChamp': red_dict.get('adc', 'Unknown'),
            'redSupportChamp': red_dict.get('support', 'Unknown')
        }

    # Calculates synergy and meta winrates to explain the decision.
    def _determine_pick_reason(self, champ: str, allies: List[str]) -> str:
        best_syn_score = 0.0
        best_ally = ""

        # Extract base winrate once and cast to float to satisfy the IDE
        base_wr = float(self.config.get('BASE_WINRATE', 0.50))

        # Check for high synergy with currently locked-in allies
        for ally in allies:
            pair = sorted([champ, ally])
            pair_key = f"{pair[0]}-{pair[1]}"
            if pair_key in self.synergy_matrix:
                # Safely extract and calculate float values
                syn_score = float(self.synergy_matrix[pair_key].get("winrate", base_wr)) - base_wr
                if syn_score > best_syn_score:
                    best_syn_score = syn_score
                    best_ally = ally

        if best_syn_score >= 0.015:
            return f"High synergy with {best_ally}."

        # Check if it's just a raw meta monster right now
        meta_wr = float(self.meta_db.get(champ, base_wr))
        if meta_wr >= 0.515:
            return f"Strong current meta pick ({meta_wr * 100:.1f}% WR)."

        return "Solid balanced addition."

    # The main function called by the draft coach command to get the top 3 champion suggestions for a given role and draft state.
    # Rapidly simulates the current draft state against all valid champions for a target role.
    def suggest_champion(self, target_role: str, user_team: str, blue_dict: dict, red_dict: dict, role_db: dict,
                         banned_champs: list = None):
        target_role = target_role.lower()
        is_blue = (user_team.lower() == 'blue')

        valid_champions = self._get_valid_available_champions(
            target_role, role_db, blue_dict, red_dict, banned_champs or []
        )

        allies = [c for c in (blue_dict.values() if is_blue else red_dict.values()) if c != "Unknown"]

        # Build the batch of drafts
        draft_batch = []
        for champ in valid_champions:
            test_blue, test_red = blue_dict.copy(), red_dict.copy()
            if is_blue:
                test_blue[target_role] = champ
            else:
                test_red[target_role] = champ
            draft_batch.append(self._build_draft_input(test_blue, test_red))

        if not draft_batch:
            return []

        # Send the entire batch to PyTorch at once
        try:
            batch_predictions = self.predict_batch(draft_batch)
        except Exception as e:
            logger.error(f"Batch AI Coach Simulation failed: {e}")
            return []

        # Process the results natively
        results = []
        for champ, prediction in zip(valid_champions, batch_predictions):
            win_prob = prediction[0] if is_blue else prediction[1]
            reason = self._determine_pick_reason(champ, allies)
            results.append((champ, win_prob, reason))

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