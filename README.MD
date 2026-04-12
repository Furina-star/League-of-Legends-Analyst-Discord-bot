# 💧 Furina: League of Legends AI Analyst

Furina is a high-performance Discord bot designed to provide deep analytical insights into your League of Legends matches using the Riot Games API and custom machine learning models.

## Stack

|               |                             |
|---------------|-----------------------------|
| Runtime       | Python (Asyncio)            |
| ML Inference  | PyTorch, Safetensors, Skops |
| Bot framework | discord.py (Slash Commands) |
| Caching       | aiosqlite                   |
| Data source   | Riot Games API              |

## Features

### `/ predict` — AI match prediction
Evaluates a live 5v5 draft using a trained PyTorch neural network and outputs win probability for both blue and red side.

### `/ scout` — Live scouting dossier
Detects which team the user is on and pulls champion mastery and Solo/Duo queue ranks for every enemy player.

### `/ postgame` — Post-game analysis
Ruthless performance reviews with lane rival comparisons and item build verification.

### Static Localization (i18n)
Automatically detects the user's Discord client language and natively translates command outputs into 12 different languages.

### Secure & Optimized Inference
Machine Learning models are serialized using HuggingFace's `safetensors` and `skops.io` to guarantee zero arbitrary code execution. Inference is fully optimized using pure NumPy/PyTorch native arrays for sub-millisecond execution.

### Smart Caching Architecture
Utilizes a persistent `aiosqlite` connection to cache heavy Riot API endpoints locally, respecting API rate limits and vastly accelerating subsequent commands.

## Setup and Installation
* Python 3.10+
* Discord Bot Token (with Message Content Intent enabled)
* Riot Games API Key

### 1. Clone
```bash
git clone https://github.com/Furina-star/League-of-Legends-Analyst-Discord-bot.git
cd League-of-Legends-Analyst-Discord-bot
```

### 2. Virtual environment
```bash
python -m venv .venv

# windows
.venv\Scripts\activate

# mac / linux
source .venv/bin/activate
```

### 3. Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment variables
Create a `.env` file in the project root:
```env
DISCORD_TOKEN=your_discord_bot_token_here
RIOT_API_KEY=your_riot_api_key_here
```

### 5. Run
```bash
python discord_bot.py
```

## Command reference

Prefix: `/` (Slash Commands)

| Command                            | Description                                                                        |
|------------------------------------|------------------------------------------------------------------------------------|
| `/ help`                           | Displays the interactive help menu                                                 |
| `/ ping`                           | Checks bot latency, and status                                                     |
| `/ trial`                          | Drag your duo to court and let the Oratrice decide who truly threw the game.       |
| `/ confess`                        | Take the stand, admit your sins, and await the final verdict of the court.         |
| `/ link <server> RiotName#Tag`     | Link your Riot ID to the Oratrice for Hall of Shame tracking                       |
| `/ unlink`                         | Sever your ties with the Oratrice and wipe your records clean.                     |
| `/ hallofshame`                    | View the server's most tragic League of Legends performers this week.              |
| `/ predict <server> RiotName#Tag`  | Runs the live draft through the PyTorch model and outputs win probability per side |
| `/ scout <server> RiotName#Tag`    | Generates an enemy team dossier with ranks and champion mastery                    |
| `/ postgame <server> RiotName#Tag` | Provides a detailed post-game analysis for the specified match ID                  |

---
*Not endorsed by Riot Games or HoYoverse. League of Legends and Riot Games are trademarks of Riot Games, Inc. Genshin Impact and Furina are trademarks of Cognosphere PTE. LTD. (HoYoverse).*