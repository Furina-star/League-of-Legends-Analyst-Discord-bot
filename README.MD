# Furina — League Analyst

A modular, object-oriented Discord bot powered by the Riot Games API and PyTorch. Calculates live match win conditions and aggregates enemy player statistics into clean dossiers.

## Stack

| | |
|---|---|
| Runtime | Python |
| ML | PyTorch |
| Bot framework | discord.py |
| Data source | Riot Games API |

## Features

### `f predict` — AI match prediction
Evaluates a live 5v5 draft using a trained PyTorch neural network and outputs win probability for both blue and red side.

### `f scout` — Live scouting dossier
Detects which team the user is on and pulls champion mastery and Solo/Duo queue ranks for every enemy player.

## Installation

### 1 — Clone
```bash
git clone https://github.com/Furina-star/Furina-League-of-Legends-Analyst-Discord-bot.git
cd Furina-League-Bot
```

### 2 — Virtual environment
```bash
python -m venv .venv

# windows
.venv\Scripts\activate

# mac / linux
source .venv/bin/activate
```

### 3 — Dependencies
```bash
pip install -r requirements.txt
```

### 4 — Environment variables
Create a `.env` file in the project root:
```env
DISCORD_TOKEN=your_discord_bot_token_here
RIOT_API_KEY=your_riot_api_key_here
```

### 5 — Run
```bash
python discord_bot.py
```

## Command reference

Prefix: `f ` or `furina `

| Command | Description |
|---|---|
| `f help` | Displays the interactive help menu |
| `f ping` | Checks bot latency and online status |
| `f predict RiotName#Tag` | Runs the live draft through the PyTorch model and outputs win probability per side |
| `f scout RiotName#Tag` | Generates an enemy team dossier with ranks and champion mastery |

---

*Not endorsed by Riot Games. League of Legends and Riot Games are trademarks of Riot Games, Inc.*