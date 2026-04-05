import torch
import torch.nn as nn
import joblib
import pandas as pd

# Define the Model Architecture
class Model(nn.Module):
    def __init__(self, num_champions):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=num_champions, embedding_dim=16)

        self.net = nn.Sequential(
            nn.Linear(160, 256),
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

    def forward(self, x):
        embedded = self.embedding(x)
        flattened = embedded.view(x.size(0), -1)
        return self.net(flattened)

# Wrapper Class
class LeagueAI:
    # This function set up and load Label encoder and the model
    def __init__(self, model_path = 'models/Lol_draft_predictor.pth', encoder_path='models/label_encoder.pkl'):
        print("Loading AI Model and Label Encoder...")

        # Load the Label encoder
        self.le = joblib.load(encoder_path)

        # Load the torch model
        checkpoint = torch.load(model_path, weights_only=True)
        self.model = Model(checkpoint['num_champs'])
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()

        print("AI Model and Label Encoder loaded successfully.")

    # This function takes in a draft dictionary, preprocesses it, and returns the predicted win probability for the blue team
    def predict_match(self, draft_dict):
        correct_order = [
            'blueTopChamp', 'blueJungleChamp', 'blueMiddleChamp', 'blueADCChamp', 'blueSupportChamp',
            'redTopChamp', 'redJungleChamp', 'redMiddleChamp', 'redADCChamp', 'redSupportChamp'
        ]

        df_input = pd.DataFrame([draft_dict])[correct_order]

        for col in df_input.columns:
            df_input[col] = df_input[col].apply(lambda x: x if x in self.le.classes_ else 'Unknown')
            df_input[col] = self.le.transform(df_input[col].astype(str))

        x_tensor = torch.tensor(df_input.values, dtype=torch.long)

        with torch.no_grad():
            prediction = self.model(x_tensor).item()

        blue_win_prob = prediction
        red_win_prob = 1.0 - blue_win_prob

        return blue_win_prob, red_win_prob

    def apply_hybrid_algorithm(self, base_blue_prob, blue_winrates, red_winrates):
        # Calculate the average team winrate
        avg_blue = sum(blue_winrates) / len(blue_winrates) if blue_winrates else 50.0
        avg_red = sum(red_winrates) / len(red_winrates) if red_winrates else 50.0

        # Find the skill gap
        winrate_gap = avg_blue - avg_red

        # Don't want player winrates to completely override the AI.
        skill_weight = 0.5
        modifier = (winrate_gap * skill_weight) / 100.0

        final_blue_prob = base_blue_prob + modifier

        # Clamp the results so we never get mathematically impossible numbers like 105%
        final_blue_prob = max(0.01, min(0.99, final_blue_prob))
        final_red_prob = 1.0 - final_blue_prob

        return final_blue_prob, final_red_prob
