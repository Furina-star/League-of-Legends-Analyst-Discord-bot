# Discord League Analyst Bot

A modular, object-oriented Discord bot powered by the Riot Games API and PyTorch. Calculates live match win conditions and aggregates enemy player statistics into clean dossiers.

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

### Static Localization (i18n)
Automatically detects the user's Discord client language and natively translates command outputs into 12 different languages.

### Secure & Optimized Inference
Machine Learning models are serialized using HuggingFace's `safetensors` and `skops.io` to guarantee zero arbitrary code execution. Inference is fully optimized using pure NumPy/PyTorch native arrays for sub-millisecond execution.

### Smart Caching Architecture
Utilizes a persistent `aiosqlite` connection to cache heavy Riot API endpoints locally, respecting API rate limits and vastly accelerating subsequent commands.

## Installation

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

| Command                           | Description                                                                        |
|-----------------------------------|------------------------------------------------------------------------------------|
| `/ help`                          | Displays the interactive help menu                                                 |
| `/ ping`                          | Checks bot latency, and status                                                     |
| `/ predict <server> RiotName#Tag` | Runs the live draft through the PyTorch model and outputs win probability per side |
| `/ scout <server> RiotName#Tag`   | Generates an enemy team dossier with ranks and champion mastery                    |

---

*Not endorsed by Riot Games. League of Legends and Riot Games are trademarks of Riot Games, Inc.*