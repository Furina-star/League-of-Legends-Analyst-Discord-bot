# League Analyst Discord Bot

A modular, object-oriented Discord application powered by the Riot Games API and PyTorch. Furina acts as a real-time Solo Queue analyst, calculating live match win conditions and aggregating enemy player statistics into clean dossiers.

## ✨ Features

* **AI Match Prediction (`f predict`):** Uses a trained PyTorch Neural Network to evaluate a live 5v5 draft and calculate the win probability for both the Blue and Red teams based on team composition.
* **Live Scouting (`f scout`):** Automatically detects which team the user is on and generates a detailed dossier of the enemy team, including Champion Mastery points and current Solo/Duo Queue ranks.

## 🚀 Installation & Setup

If you want to run your own instance of Furina, follow these steps:

### 1. Clone the Repository
\`\`\`bash
git clone https://github.com/Furina-star/Furina-League-of-Legends-Analyst-Discord-bot.git
cd Furina-League-Bot
\`\`\`

### 2. Set Up the Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.
\`\`\`bash
## Create the environment
python -m venv .venv

## Activate the environment (Windows)
.venv\Scripts\activate

## Activate the environment (Mac/Linux)
source .venv/bin/activate
\`\`\`

### 3. Install Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 4. Environment Variables
Create a file named exactly `.env` in the root folder of the project. You will need to supply your own Discord Bot Token and Riot Games Developer Key.
\`\`\`env
DISCORD_TOKEN=your_discord_bot_token_here
RIOT_API_KEY=your_riot_api_key_here
\`\`\`

### 5. Run the Bot
\`\`\`bash
discord_bot.py
\`\`\`

## 📖 Command List

Furina uses the prefix `f ` or `furina `.

* `f help` - Displays the interactive help menu.
* `f ping` - Checks the bot's latency and online status.
* `f predict RiotName#Tag` - Fetches the live game for the specified user and runs the draft through the PyTorch model to predict the winner.
* `f scout RiotName#Tag` - Finds the live game, determines the enemy team, and pulls their current Ranks and Champion Mastery for their locked-in champions.

## ⚠️ Disclaimer
Furina League Analyst Bot isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc. League of Legends © Riot Games, Inc.
