import pandas as pd
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import joblib
import matplotlib.pyplot as plt
import numpy as np
import requests

# Load Data
df = pd.read_csv("data/Modern_LoL_Data.csv")

# Synthetic Data Injection for No bans or something this part is so pain in the ass because in the dataset there is "No Bans"
print("Injecting synthetic 'None', bans")
ban_columns = [
    'blueBan1', 'blueBan2', 'blueBan3', 'blueBan4', 'blueBan5',
    'redBan1', 'redBan2', 'redBan3', 'redBan4', 'redBan5'
]

# Randomly replace 15% of all bans in the dataset with 'None'
for col in ban_columns:
    mask = np.random.rand(len(df)) < 0.15
    df.loc[mask, col] = 'None'

# Grabbing every single champions out there just to be safe, because the dataset i choose is tournament based sometimes a certain champion is not picked.
print ("Downloading Master Champion List From Riot...")
version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
champ_data = requests.get(f"http://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json").json()

all_champions = []
for champ_id, info in champ_data['data'].items():
    all_champions.append(champ_id)
    all_champions.append(info['name'])

all_champions.extend(['None', 'Unknown'])

# Encode
le = LabelEncoder()
le.fit(all_champions)
text_cols = [col for col in df.columns if col != 'rResult']

print("Translating CSV data...")
for col in text_cols:
    # If there is a weird typo in the CSV, default it to 'Unknown' so it doesn't crash
    df[col] = df[col].apply(lambda x: x if x in le.classes_ else 'Unknown')
    df[col] = le.transform(df[col].astype(str))

joblib.dump(le, "models/label_encoder.pkl")
num_unique_champions = len(le.classes_) # Get the total number of unique champions

# Setup Features & Target
x = df.drop(columns=['rResult'])
y = df['rResult']

# Split
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

# Tensors
x_train_t = torch.tensor(x_train.values, dtype=torch.long)
y_train_t = torch.tensor(y_train.values, dtype=torch.float32).unsqueeze(1)

x_test_t = torch.tensor(x_test.values, dtype=torch.long)
y_test_t = torch.tensor(y_test.values, dtype=torch.float32).unsqueeze(1)

train_dataset = TensorDataset(x_train_t, y_train_t)
train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True, drop_last=True)

# Build Model
class Model(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=num_unique_champions, embedding_dim=16)

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

# Start Training
model = Model(num_unique_champions)
optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-3)
criterion = nn.BCELoss()

print(f"Number of input columns: {x.shape[1]}")
print(f"Total Unique Champions/Bans found: {num_unique_champions}")
print("Training model with Embeddings...\n")

for epoch in range(20):
    model.train()
    running_loss = 0.0
    for batch_x, batch_y in train_loader:
        optimizer.zero_grad()
        loss = criterion(model(batch_x), batch_y)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    avg_loss = running_loss / len(train_loader)
    if (epoch + 1) % 5 == 0 or epoch == 0:
        print(f"Epoch [{epoch + 1}/50]  |  Loss: {avg_loss:.4f}")

# Save the Model
torch.save({'model_state_dict': model.state_dict(), 'num_champs': num_unique_champions},
           "models/Lol_draft_predictor.pth")
print("\nModel saved successfully with 20 inputs!")

# Evaluation & Confusion Matrix
model.eval()
with torch.no_grad():
    predictions = model(x_test_t)
    predicted_classes = (predictions >= 0.5).float()

y_true = y_test_t.numpy()
y_pred =  predicted_classes.numpy()

# Calculate and print accuracy!
acc = accuracy_score(y_true, y_pred) * 100
print(f"\nFinal Test Accuracy: {acc:.2f}%")

# Draw Confusion Matrix
cm = confusion_matrix(y_true, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Blue Win', 'Red Win'])

fig, ax = plt.subplots(figsize=(8, 6))
disp.plot(cmap = plt.cm.Blues)
plt.title('AI Draft Predictor - Confusion Matrix')
plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight') # Saves the image to your folder!
plt.close()

print("Confusion matrix saved as 'confusion_matrix.png'")