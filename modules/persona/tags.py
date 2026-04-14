"""
This is where Tags is stored, which is the system we use to assign tags to players based on their match history and current inferred position.
This is crucial for the bot's ability to detect autofill situations and provide accurate role-based recommendations.
The functions in this file are designed to be reusable across different parts of the bot, ensuring consistent data handling and improving code maintainability.
"""

import re
from modules.utils.parsers import ParsedStats

# The pregame tag dictionary for live games
class PregameTagEngine:
    def __init__(self, mastery: int, is_otp: bool, is_duo: bool, is_autofilled: bool, meta_wr: float, rank_str: str):
        self.mastery = mastery
        self.is_otp = is_otp
        self.is_duo = is_duo
        self.is_autofilled = is_autofilled
        self.meta_wr = meta_wr

        # Pre-parse winrate stats to keep the logic clean
        self.wr = 50.0
        self.games = 0
        if "Unranked" not in rank_str:
            match = re.search(r"\*\*([\d.]+)%\s*WR\*\*\s*\((\d+)\s*games\)", rank_str)
            if match:
                self.wr = float(match.group(1))
                self.games = int(match.group(2))

    def _state_rules(self) -> list:
        return [
            (lambda: self.is_duo, "❤ **DUO**"),
            (lambda: self.is_otp, "👑 **TRUE OTP**"),
            (lambda: self.is_autofilled, "❓ **AUTOFILLED**")
        ]

    def _mastery_rules(self) -> list:
        # Replicated your if/elif logic using mutually exclusive lambda math!
        return [
            (lambda: self.mastery >= 1000000 and not self.is_otp, "🦄 **OTP WARNING**"),
            (lambda: 500000 <= self.mastery < 1000000 or (self.mastery >= 1000000 and self.is_otp), "🛡️ **Main**"),
            (lambda: self.mastery < 10000, "🔰 **First Time / Very New**")
        ]

    def _meta_rules(self) -> list:
        return [
            (lambda: self.meta_wr >= 0.525, "🎯 **Meta Abuser**"),
            (lambda: self.meta_wr <= 0.48, "🤡 **Off-Meta / Troll**")
        ]

    def _winrate_rules(self) -> list:
        return [
            (lambda: self.games > 0 and self.wr >= 70.0, "🕵️ **SUSPECTED SMURF**"),
            (lambda: self.games >= 40 and self.wr >= 60.0, "🔥 **1v9 Machine**"),
            (lambda: self.games >= 30 and self.wr <= 45.0, "🥶 **Tilted**"),
            (lambda: self.games >= 500 and 49.0 <= self.wr <= 51.0, "🧱 **Hardstuck**")
        ]

    def get_all_rules(self) -> list:
        return self._state_rules() + self._mastery_rules() + self._meta_rules() + self._winrate_rules()

    def generate_tags(self) -> str:
        tags = [tag for condition, tag in self.get_all_rules() if condition()]
        return " | ".join(tags) if tags else ""


# The performance tag dictionary meant for post games or after the game ended
class PerformanceTagEngine:
    def __init__(self, stats: dict):
        self.p = ParsedStats(stats)

    def _carry_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.pentas > 0, "🌟 **PENTA KILL**"),
            (lambda: p.pentas == 0 and p.quadras > 0, "✨ **Quadra Kill**"),
            (lambda: p.kills >= 20, "🗡️ **1v9 Machine**"),
            (lambda: p.kp_percent >= 80.0, "🤝 **Omnipresent**"),
            (lambda: p.damage > 50000, "💥 **Nuke**"),
            (lambda: p.deaths == 0 and p.kills >= 5, "🛡️ **Flawless**"),
            (lambda: p.kills >= 10 and p.damage < 15000, "🥷 **The Finisher (KS)**"),
            (lambda: p.role == 'UTILITY' and p.damage > 30000, "🔥 **Fine, I'll Do It Myself**"),
            (lambda: p.kp_percent > 60.0 and p.deaths == 0, "👻 **Untouchable**"),
            (lambda: p.kp_percent >= 80.0 and p.assists >= 10, "🤝 **Team Player**"),
            (lambda: p.win and p.deaths == 0 and p.kp_percent >= 30.0, "👑 **Unkillable Demon King**")
        ]

    def _macro_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.first_blood and not p.win, "🩸 **False Hope**"),
            (lambda: p.first_blood and p.win, "🩸 **The Opening Act**"),
            (lambda: p.cs_per_min >= 9.0, "🚜 **Farmer**"),
            (lambda: p.cs_per_min >= 10.0 and p.cs >= 250, "🔥 **Flame Horizon**"),
            (lambda: 8.5 <= p.cs_per_min < 10.0, "🌾 **Agricultural Prodigy**"),
            (lambda: p.turrets >= 3, "🪓 **Lumberjack**"),
            (lambda: p.turrets == 4 or p.turrets == 5, "🏗️ **Aggressive Urban Renewal**"),
            (lambda: p.turrets >= 6, "💣 **One-Man Siege Engine (6+ Turrets)**"),
            (lambda: p.turrets == 0 and p.role in ['TOP', 'MIDDLE', 'BOTTOM'] and p.minutes > 25,"🏢 **Allergic to Real Estate**"),
            (lambda: p.stolen_objs >= 2, "🦅 **Grand Theft Objective**"),
            (lambda: p.stolen_objs == 1, "🥷 **Opportunistic Thief**"),
            (lambda: p.dragons >= 3, "🐉 **Dragon Slayer**"),
            (lambda: p.dragons >= 4, "🐉 **Soul Collector**"),
            (lambda: p.dragons == 0 and p.role == 'JUNGLE' and p.minutes > 20, "🦎 **Reptile Phobia**"),
            (lambda: p.turrets == 0 and p.dragons == 0 and p.stolen_objs == 0 and p.minutes > 20 and p.role != 'UTILITY', "🤪 **Zero Macro**"),
        ]

    def _utility_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.vision_score > 80, "👁️ **All-Seeing Eye**"),
            (lambda: p.damage_taken > 40000 and p.deaths < 6, "🧱 **Concrete Wall**"),
            (lambda: p.healing > 20000, "🚑 **Ambulance**"),
            (lambda: p.damage_taken > 60000, "🛡️ **Raid Boss**"),
            (lambda: p.damage_taken >= 50000 and p.deaths < 8, "🧽 **Damage Sponge**"),
            (lambda: p.vision_score < 10 and p.minutes > 25, "🦇 **Echolocation Only**"),
            (lambda: p.vision_wards >= 15, "🔦 **Paranoid**"),
        ]

    def _roast_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.kills == 0 and p.deaths == 0 and p.assists == 0, "👻 **Ghost**"),
            (lambda: p.deaths >= 15, "🍔 **Happy Meal**"),
            (lambda: p.vision_wards == 0 and p.role == 'UTILITY', "🕶️ **Blind**"),
            (lambda: p.damage < 5000 and p.minutes > 20, "💤 **Pacifist**"),
            (lambda: p.kp_percent < 15.0 and p.minutes > 20, "🏝️ **Isolated**"),
            (lambda: p.damage_taken < 15000 and p.minutes > 30 and p.role in ['TOP', 'JUNGLE'], "🫣 **Allergic to Combat**"),
            (lambda: p.role == 'UTILITY' and p.cs > 100, "🛑 **Minion Tax Collector**"),
            (lambda: p.kp_percent < 20.0 and p.cs_per_min > 8.0, "🧑‍🌾 **Basic Farmer**"),
        ]

    def _anomaly_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.win and p.damage < 5000 and p.kp_percent < 20.0, "🎒 **Heavy Backpack**"),
            (lambda: not p.win and p.damage > 45000 and p.kp_percent > 60.0, "🪨 **Sisyphus (1v9 Loss)**"),
            (lambda: p.deaths >= 10 and p.kills <= 2, "👨‍🍳 **Master Chef (Feeding)**"),
            (lambda: p.kills >= 10 and p.deaths >= 10, "🎲 **Coinflip Player**"),
            (lambda: p.damage_taken > 50000 and p.deaths > 12, "🥊 **Punching Bag**"),
            (lambda: p.deaths >= 12 and p.turrets >= 4 and p.win, "🧟 **Tactical Feeder**"),
            (lambda: p.win and p.minutes < 20.0, "⏱️ **Speedrunner**"),
            (lambda: p.minutes > 45.0, "🏃 **Marathon Gamer**"),
            (lambda: p.gold > 18000 and p.damage < 12000, "💳 **All Gear, No Idea**"),
            (lambda: p.kp_percent > 70.0 and p.cs_per_min < 4.0 and p.role != 'UTILITY', "⚔️ **Team Deathmatch**"),
        ]

    def _economy_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.gold > 15000 and p.damage < 10000 and p.role != "UTILITY", "💰 **Trust Fund Baby**"),
            (lambda: p.gold >= 20000, "🏦 **The Bank**"),
            (lambda: p.cs_per_min < 4.0 and p.role in ["TOP", "MIDDLE", "BOTTOM"], "🛑 **Minion Pacifist**"),
            (lambda: p.vision_score < 15 and p.minutes > 30, "🦯 **Legally Blind**"),
            (lambda: p.cs > 300 and p.kp_percent < 30.0, "🧑‍🌾 **Stardew Valley Player**")
        ]

    def _support_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.assists >= 25 and p.deaths <= 3, "👼 **Guardian Angel**"),
            (lambda: p.vision_wards >= 10, "🔦 **Lighthouse Keeper**"),
            (lambda: p.role == "UTILITY" and p.kills > p.assists, "⚔️ **Bloodthirsty Support**"),
            (lambda: p.healing > 30000, "💖 **Walking Fountain**")
        ]

    def _jungle_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.role == 'JUNGLE' and p.stolen_objs >= 2, "🦅 **Elder Thief**"),
            (lambda: p.role == 'JUNGLE' and p.cs_per_min < 3.0 and p.minutes > 20,
             "🗺️ **Full Clear? Never Heard Of It**"),
            (lambda: p.role == 'JUNGLE' and p.kills + p.assists >= 20 and p.deaths <= 3, "🌪️ **Ganking Machine**"),
            (lambda: p.role == 'JUNGLE' and p.damage < 8000 and p.minutes > 25, "🌿 **Pve Enjoyer**"),
        ]

    def _comeback_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.win and p.deaths >= 8 and p.kills >= 10, "🔄 **Redemption Arc**"),
            (lambda: p.win and p.minutes > 40.0 and p.kp_percent >= 50.0, "🏋️ **Late Game Monster**"),
            (lambda: not p.win and p.kills >= 15 and p.kp_percent >= 60.0, "🕯️ **Tried So Hard**"),
            (lambda: p.win and p.damage > 35000 and p.deaths <= 2, "🎯 **Clinical**"),
            (lambda: p.deaths >= 5 and p.win and p.kp_percent >= 70.0, "🧯 **Crisis Manager**"),
        ]

    def _streak_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.kills >= 5 and p.deaths == 0, "🔥 **On Fire**"),
            (lambda: p.pentas == 0 and p.quadras == 0 and p.kills >= 3 and p.deaths == 0 and p.minutes < 15,
             "⚡ **Early Menace**"),
            (lambda: p.cs >= 400, "🌾 **Infinite Farm**"),
            (lambda: p.gold >= 22000, "💎 **Gold Hoarder**"),
            (lambda: p.vision_wards >= 20, "🔭 **Surveillance State**"),
        ]

    def _dodging_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.skillshots_dodged >= 50, "🕊️ **Touhou Player**"),
            (lambda: p.skillshots_dodged >= 40, "🕺 **Untouchable**"),
            (lambda: p.dodge_streak >= 15, "💨 **The Wind**"),
            (lambda: p.dodge_streak >= 10, "⚡ **Ultra Instinct**"),
            (lambda: p.skillshots_dodged < 5 and p.deaths >= 8, "🧲 **Skillshot Magnet**"),
            (lambda: p.skillshots_dodged == 0 and p.damage_taken > 30000, "🎯 **Stationary Target**")
        ]

    def _solo_kill_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.solo_kills >= 7, "🥊 **Undisputed Champion**"),
            (lambda: p.solo_kills >= 5, "⚔️ **Grand Duelist**"),
            (lambda: p.solo_kills >= 2 and p.role == 'UTILITY', "🔪 **Support Assassin**"),
            (lambda: p.solo_kills == 0 and p.kills >= 10 and not p.win, "🦅 **Vulture (No Solo Kills)**"),
            (lambda: p.solo_kills == 0 and p.deaths >= 8, "🐑 **Helpless Prey**")
        ]

    def _kda_extreme_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.kda >= 15.0, "👑 **Untouchable Royalty**"),
            (lambda: p.kda >= 10.0, "📐 **Surgically Precise**"),
            (lambda: 0 < p.kda <= 0.5 and p.minutes > 15, "🤡 **Circus Performer**"),
            (lambda: p.kda < 1.0 and p.minutes > 15, "🏧 **Walking ATM**"),
            (lambda: (p.kills + p.assists) == 0 and p.deaths >= 5, "📉 **Absolute Zero**")
        ]

    def _lane_dominance_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.cs_advantage >= 75 and p.role in ['TOP', 'MIDDLE', 'BOTTOM'], "🏰 **Evicted Opponent**"),
            (lambda: p.cs_advantage <= -75 and p.role in ['TOP', 'MIDDLE', 'BOTTOM'], "🎒 **Lunch Money Stolen**"),
            (lambda: p.plates >= 12, "🧨 **Armor Breaker**"),
            (lambda: p.plates == 0 and p.cs_advantage <= -40 and p.role in ['TOP', 'MIDDLE'] and p.minutes > 15, "🛡️ **Pathological Coward**")
        ]

    def _combat_output_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.team_damage_pct >= 0.40 and p.win, "🌋 **Atlas (Carrying the World)**"),
            (lambda: p.team_damage_pct <= 0.10 and p.role not in ['UTILITY', 'JUNGLE'] and p.minutes > 20, "💤 **Statistically Irrelevant**"),
            (lambda: p.dpm >= 1000.0, "☄️ **Calamity Level Threat**"),
            (lambda: p.dpm <= 250.0 and p.role not in ['UTILITY'] and p.minutes > 20, "🧘 **Aggressive Pacifist**")
        ]

    def _clutch_factor_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.lucky_survivals >= 3, "✨ **Protagonist Plot Armor**"),
            (lambda: p.lucky_survivals == 0 and p.deaths >= 12, "🪦 **Speedrunning the Grey Screen**"),
            (lambda: p.outnumbered_kills >= 4, "🎬 **Action Movie Star**")
        ]

    def _theatrical_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.win and p.deaths == 0 and p.team_damage_pct <= 0.08 and p.kp_percent < 20.0,"👑 **Masquerade of the Guilty**"),
            (lambda: p.assists >= 25 and p.kp_percent >= 80.0 and p.kills <= 3, "🌊 **Director of the Salon**"),
            (lambda: p.first_blood and not p.win and p.deaths >= 10, "⚖️ **Condemned by the Oratrice**"),
            (lambda: p.damage_taken >= 50000 and p.deaths <= 3 and p.lucky_survivals >= 4, "🎭 **The Show Must Go On!**"),
            (lambda: p.vision_score >= 120, "🗞️ **The Steambird's Lead Reporter**"),
            (lambda: p.healing >= 30000 and p.damage >= 40000, "💧 **Perfect Pneuma/Ousia Alignment**"),
            (lambda: p.win and p.deaths == 0 and p.kills >= 15 and p.kp_percent >= 60.0,"👏 **Furina Applauds**"),
        ]

    def get_all_rules(self) -> list:
        return (
                self._carry_rules() +
                self._macro_rules() +
                self._jungle_rules() +
                self._utility_rules() +
                self._comeback_rules() +
                self._streak_rules() +
                self._roast_rules() +
                self._anomaly_rules() +
                self._economy_rules() +
                self._support_rules() +
                self._dodging_rules() +
                self._solo_kill_rules() +
                self._kda_extreme_rules() +
                self._combat_output_rules() +
                self._lane_dominance_rules() +
                self._clutch_factor_rules() +
                self._theatrical_rules()
        )

    # Format and generate the final tag string based on the rules
    def generate_tags(self) -> str:
        tags = [tag for condition, tag in self.get_all_rules() if condition()]

        if not tags:
            return ""

        chunked_tags = [tags[i:i + 3] for i in range(0, len(tags), 3)]
        return "\n".join([" | ".join(row) for row in chunked_tags])

# The wrapper functions that can be called from other files to get the tags without needing to know about the internal workings of the engines
def get_pregame_tags(mastery: int, is_otp: bool, is_duo: bool, is_autofilled: bool, meta_wr: float, rank_str: str) -> str:
    engine = PregameTagEngine(mastery, is_otp, is_duo, is_autofilled, meta_wr, rank_str)
    return engine.generate_tags()

# The performance tags that calls out pre game tags based on their performance.
def get_performance_tags(stats: dict) -> str:
    engine = PerformanceTagEngine(stats)
    return engine.generate_tags()

# Calculates team composition warnings based on macro tags, used in '/coach'
def get_draft_warnings(locked_champs: list, role_db: dict) -> list[str]:
    if not locked_champs:
        return []

    tags = ["DAMAGE_AD", "DAMAGE_AP", "FRONTLINE", "RANGED", "HARD_CC", "ENGAGE", "WAVECLEAR", "SCALING"]
    counts = {
        tag: sum(1 for c in locked_champs if c in set(role_db.get(tag, [])))
        for tag in tags
    }

    warnings = []

    # Damage Type Warnings
    if counts["DAMAGE_AD"] >= 4:
        warnings.append("⚠️ **Warning: Heavy AD.** Enemy armor stacking will be highly effective.")
    elif counts["DAMAGE_AP"] >= 4:
        warnings.append("⚠️ **Warning: Heavy AP.** Enemy Magic Resist stacking will counter you.")

    # Data-driven Structure Warnings
    if len(locked_champs) >= 4:
        rules = [
            (counts["FRONTLINE"] == 0, "🛡️ **Warning: Glass Cannon Comp.** No dedicated frontline detected. Highly vulnerable to hard engage."),
            (counts["RANGED"] == 0, "🏹 **Warning: Full Melee Comp.** Your team lacks ranged damage and is highly susceptible to kiting."),
            (counts["HARD_CC"] == 0, "🛑 **Warning: No Hard CC.** Your team has extremely limited ways to lock down priority targets."),
            (counts["ENGAGE"] == 0, "🏃 **Warning: No Engage.** Your team lacks reliable tools to force favorable team fights."),
            (counts["WAVECLEAR"] == 0, "🌊 **Warning: No Waveclear.** Your team will struggle to break base sieges or defend inhibitors."),
            (counts["SCALING"] >= 3, "⏳ **Warning: Extreme Scaling.** Very weak early game detected. You will likely concede early objectives.")
        ]
        # A single generator extracts all triggered warnings at once
        warnings.extend(msg for condition, msg in rules if condition)

    return warnings