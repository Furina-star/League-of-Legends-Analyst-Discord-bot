"""
This is where Tags is stored, which is the system we use to assign tags to players based on their match history and current inferred position.
This is crucial for the bot's ability to detect autofill situations and provide accurate role-based recommendations.
The functions in this file are designed to be reusable across different parts of the bot, ensuring consistent data handling and improving code maintainability.
"""

import re

# Tags that are used during live game
def get_pregame_tags(mastery: int, is_otp: bool, is_duo: bool, is_autofilled: bool, meta_wr: float,rank_str: str) -> str:
    tags = []

    # State Flags (Instant boolean checks)
    state_rules = [
        (lambda: is_duo, "❤ **DUO**"),
        (lambda: is_otp, "👑 **TRUE OTP**"),
        (lambda: is_autofilled, "❓ **AUTOFILLED**")
    ]
    for condition, tag in state_rules:
        if condition(): tags.append(tag)

    # Mastery Rules
    if mastery >= 1000000 and not is_otp:
        tags.append("🦄 **OTP WARNING**")
    elif mastery >= 500000:
        tags.append("🛡️ **Main**")
    elif mastery < 10000:
        tags.append("🔰 **First Time / Very New**")

    # Meta Rules
    if meta_wr >= 0.525:
        tags.append("🎯 **Meta Abuser**")
    elif meta_wr <= 0.48:
        tags.append("🤡 **Off-Meta / Troll**")

    # Tactical Winrate Analysis
    if "Unranked" not in rank_str:
        match = re.search(r"\*\*([\d.]+)%\s*WR\*\*\s*\((\d+)\s*games\)", rank_str)
        if match:
            wr = float(match.group(1))
            games = int(match.group(2))

            # Dynamic Rule Engine for Winrates
            wr_rules = [
                (lambda: wr >= 70.0, "🕵️ **SUSPECTED SMURF**"),
                (lambda: wr >= 60.0 and games >= 40, "🔥 **1v9 Machine**"),
                (lambda: wr <= 45.0 and games >= 30, "🥶 **Tilted**"),
                (lambda: games >= 500 and 49.0 <= wr <= 51.0, "🧱 **Hardstuck**")
            ]

            for condition, tag in wr_rules:
                if condition(): tags.append(tag)

    return " | ".join(tags) if tags else ""

# Tags that are meant for post games or after a game ended
def get_performance_tags(stats: dict) -> str:
    tags = []

    # Dynamic Rule Engine for Match Performance
    perf_rules = [
        (lambda: stats.get('firstBloodKill', False), "🩸 **First Blood**"),
        (lambda: stats.get('pentaKills', 0) > 0, "🌟 **PENTA KILL**"),
        (lambda: stats.get('pentaKills', 0) == 0 and stats.get('quadraKills', 0) > 0, "✨ **Quadra Kill**"),
        (lambda: stats.get('kills', 0) == 0 and stats.get('deaths', 0) == 0 and stats.get('assists', 0) == 0,"👻 **Ghost**"),
        (lambda: stats.get('totalDamageTaken', 0) > 40000 and stats.get('deaths', 0) < 5, "🧱 **Concrete Wall**"),
        (lambda: stats.get('objectivesStolen', 0) > 0, "🥷 **Objective Thief**")
    ]

    for condition, tag in perf_rules:
        if condition():
            tags.append(tag)

    return " | ".join(tags) if tags else ""