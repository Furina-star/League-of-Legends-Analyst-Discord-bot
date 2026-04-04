import pandas as pd
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, accuracy_score
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import joblib
import matplotlib.pyplot as plt
import requests

# Load your CUSTOM Mined Data
df = pd.read_csv("data/ranked_drafts.csv")

# Grabbing every single champion out there just to be safe
print("Downloading Master Champion List From Riot...")
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
text_cols = [col for col in df.columns if col != 'blueWin']

print("Translating CSV data...")
for col in text_cols:
    df[col] = df[col].apply(lambda x: x if x in le.classes_ else 'Unknown')
    df[col] = le.transform(df[col].astype(str))

joblib.dump(le, "models/label_encoder.pkl")
num_unique_champions = len(le.classes_)

x = df.drop(columns=['blueWin'])
y = df['blueWin']

# Split
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

# Tensors
x_train_t = torch.tensor(x_train.values, dtype=torch.long)
y_train_t = torch.tensor(y_train.values, dtype=torch.float32).unsqueeze(1)

x_test_t = torch.tensor(x_test.values, dtype=torch.long)
y_test_t = torch.tensor(y_test.values, dtype=torch.float32).unsqueeze(1)

# Create DataLoaders for both Training and Validation
train_dataset = TensorDataset(x_train_t, y_train_t)
train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True, drop_last=True)

test_dataset = TensorDataset(x_test_t, y_test_t)
test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)


# Build Model
class Model(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=num_unique_champions, embedding_dim=16)

        self.net = nn.Sequential(
            nn.Linear(160, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.4),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.4),

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
print(f"Total Unique Champions found: {num_unique_champions}")
print(f"Training on {len(x_train)} matches, Validating on {len(x_test)} matches...\n")

num_epochs = 20
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for batch_x, batch_y in train_loader:
        optimizer.zero_grad()
        loss = criterion(model(batch_x), batch_y)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    avg_train_loss = running_loss / len(train_loader)

    # Catch Overfitting
    model.eval()
    val_loss = 0.0
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            loss = criterion(model(batch_x), batch_y)
            val_loss += loss.item()

    avg_val_loss = val_loss / len(test_loader)

    if (epoch + 1) % 5 == 0 or epoch == 0:
        print(f"Epoch [{epoch + 1}/{num_epochs}]  |  Train Loss: {avg_train_loss:.4f}  |  Val Loss: {avg_val_loss:.4f}")

# Save the Model
torch.save({'model_state_dict': model.state_dict(), 'num_champs': num_unique_champions},
           "models/Lol_draft_predictor.pth")
print("\nModel saved successfully with 10 inputs!")

# Evaluation & Confusion Matrix
model.eval()
with torch.no_grad():
    predictions = model(x_test_t)
    predicted_classes = (predictions >= 0.5).float()

y_true = y_test_t.numpy()
y_pred = predicted_classes.numpy()

# Calculate and print accuracy!
acc = accuracy_score(y_true, y_pred) * 100
print(f"\nFinal Test Accuracy: {acc:.2f}%")

# Draw Confusion Matrix
cm = confusion_matrix(y_true, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Red Win', 'Blue Win'])

fig, ax = plt.subplots(figsize=(8, 6))
disp.plot(cmap=plt.cm.Blues, ax=ax)
plt.title('AI Draft Predictor - Confusion Matrix')
plt.savefig('results/confusion_matrix.png', dpi=300, bbox_inches='tight')
plt.close()

print("Confusion matrix saved as 'confusion_matrix.png'")