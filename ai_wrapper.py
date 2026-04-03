import torch
import torch.nn as nn
import joblib
import pandas as pd

# Define the Model Architecture (same as in train_model.py) for discord_bot.py
class Model(nn.Module):
    def __init__(self, num_champions):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=num_champions, embedding_dim=16)

        self.net = nn.Sequential(
            nn.Linear(320, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),

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
            'blueADCChamp', 'blueJungleChamp', 'blueMiddleChamp', 'blueSupportChamp', 'blueTopChamp',
            'redADCChamp', 'redJungleChamp', 'redMiddleChamp', 'redSupportChamp', 'redTopChamp',
            'blueBan1', 'blueBan2', 'blueBan3', 'blueBan4', 'blueBan5',
            'redBan1', 'redBan2', 'redBan3', 'redBan4', 'redBan5'
        ]

        df_input = pd.DataFrame([draft_dict])[correct_order]
        for col in df_input.columns:
            df_input[col] = df_input[col].apply(lambda x: x if x in self.le.classes_ else 'Unknown')
            df_input[col] = self.le.transform(df_input[col].astype(str))

        x_tensor = torch.tensor(df_input.values, dtype=torch.long)

        with torch.no_grad():
            red_win_prob = self.model(x_tensor).item()

        blue_win_prob = 1.0 - red_win_prob

        return blue_win_prob, red_win_prob
