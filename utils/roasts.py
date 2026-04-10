"""
This is just a dictionary for post match review roasts.
It is used in the post_match_review function in discord_bot.py.
The keys are the roast types and the values are lists of roasts.
The roasts can contain {champion} which will be replaced with the champion name of the player being roasted.
"""

import random

# Roast and Praise dictionary
# The rules are organized into categories: Champion-Specific, Tragedy, Economy, Role-Specific, and Praise.
class ParsedStats:
    def __init__(self, stats: dict):
        self.champ = stats.get('championName', '')
        self.kills = stats.get('kills', 0)
        self.deaths = stats.get('deaths', 0)
        self.assists = stats.get('assists', 0)
        self.damage = stats.get('totalDamageDealtToChampions', 0)
        self.damage_taken = stats.get('totalDamageTaken', 0)
        self.vision_wards = stats.get('visionWardsBoughtInGame', 0)
        self.role = stats.get('teamPosition', '')
        self.win = stats.get('win', False)
        self.time = stats.get('gameDuration', 0)
        self.cs = stats.get('totalMinionsKilled', 0) + stats.get('neutralMinionsKilled', 0)
        self.gold = stats.get('goldEarned', 0)
        self.vision_score = stats.get('visionScore', 0)
        self.turrets = stats.get('turretTakedowns', 0)
        self.dmg_taken = stats.get('totalDamageTaken', 0)
        self.healing = stats.get('totalHealsOnTeammates', 0)
        self.fb = stats.get('firstBloodKill', False)

# The dictionary containing all roasts and praises
class RoastGenerator:
    def __init__(self, stats: dict):
        self.p = ParsedStats(stats)

    def _champion_rules(self) -> list:
        p = self.p
        champ_map = {
            "Yasuo": [(lambda: p.deaths >= 10, "Ah, the legendary 0/10 Yasuo powerspike. Truly a masterclass in absolute predictability.")],
            "Yuumi": [(lambda: p.damage < 3000, "You played Yuumi. I hope whatever movie you were watching on your second monitor was entertaining.")],
            "Teemo": [(lambda: True, "You played Teemo. You have already sacrificed your dignity and the respect of your peers.")],
            "Garen": [(lambda: p.win, "Spin. Win. The limits of your intellectual capacity are truly inspiring. How hard was it to press E?")],
            "Vayne": [(lambda: p.deaths >= 8, "Tumbling forward into five enemies and instantly dying does not make you 'mechanically gifted'.")],
            "Volibear": [(lambda: True, "You played Volibear. I assume your strategy consisted of turning your brain completely off and mashing your keyboard with a closed fist.")],
            "Mordekaiser": [(lambda: True, "Ah, Mordekaiser. You missed your pull, you missed your slam, but your passive aura killed them anyway while you stood completely still.")],
            "Sett": [(lambda: True, "You played Sett. You absorbed 5,000 damage to the face simply because you lack the mechanics to dodge, and then pressed a single button to win the fight.")],
            "Riven": [(lambda: True, "You picked Riven. I'm sure you spent hours in the practice tool perfecting your 'animation cancels,' only to break your fingers in a real match.")],
            "Samira": [(lambda: p.deaths >= 8, "Let me guess: you dashed into five people, mashed all your buttons trying to get an S rank, and instantly died to a single stun.")],
            "Gangplank": [(lambda: True, "Ah, Gangplank. You spent 30 minutes playing a fruit-eating barrel minigame only to completely panic and miss your one important combo in the final team fight.")],
            "Viego": [(lambda: True, "Viego. How pathetic that you can only secure kills by stealing the identities of players who are actually better than you.")],
            "Yone": [(lambda: p.deaths >= 10, "Yone. You missed your ultimate, missed your Q3, snapped back to your E, and still somehow managed to die. The wind brothers truly are a plague upon this game.")],
            "Lee Sin": [(lambda: p.damage < 15000, "A blind monk played by a blind summoner. Your 'Insec' attempts were closer to an acrobatic suicide routine than an actual gank.")],
            "Lux": [(lambda: p.role == "UTILITY" and p.vision_score < 15, "A Lux 'Support' who builds full AP, misses every binding, and refuses to ward. You are not a support, you are a failed Mid Laner in denial.")],
            "Briar": [(lambda: p.deaths >= 10, "You pressed W and went completely AFK while your champion sprinted directly into the enemy fountain. Truly, the pinnacle of interactive gameplay.")],
            "Katarina": [(lambda: p.assists == 0 and p.kills > 0 and not p.win, "You mashed your forehead on the keyboard, got a few resets, and still lost the game. Your mechanics are as hollow as your macro.")],
            "Zed": [(lambda: p.kills < 10, "Ah, Zed. You pressed R, missed all three of your shurikens, and swapped back to your shadow to watch your target walk away completely unharmed. So much edge, yet entirely dull.")],
            "Sylas": [(lambda: not p.win, "Sylas. You stole the enemy's ultimate because you lack an identity of your own, and then you completely missed it. A plagiarist and a failure.")],
            "Irelia": [(lambda: p.deaths >= 8, "Ah, Irelia. You dashed through five minions, missed your stun, and immediately died under the enemy tower. Truly a mechanical prodigy trapped in a tragic reality.")],
            "Dr. Mundo": [(lambda: True, "You played Dr. Mundo. You turned your brain completely off, pressed your ultimate, and simply walked in a straight line. I am amazed you remembered to plug your keyboard in today.")],
            "Shen": [(lambda: not p.win, "You played Shen. You spent the entire game staring at your team's health bars instead of your own screen, only to ultimate the 0/10 ADC. A truly noble, completely useless sacrifice.")],
            "K'Sante": [(lambda: p.deaths >= 8, "You played K'Sante. You have a shield, a dash, unstoppable frames, true damage, and a kidnapping tool, yet you still managed to feed. Did you forget to read your champion's 40-page essay of a kit?")],
            "Darius": [(lambda: p.time > 1800 and not p.win, "You played Darius. Let me guess: you won your lane by pressing Q, then spent the next 20 minutes getting kited to death by the ADC because you don't know what a flank is. A classic tale.")],
            "Seraphine": [(lambda: True, "You picked Seraphine. I assume you spent the entire game sitting three screens away, missing your ultimate on a stationary target, and stealing your ADC's farm. A performance to truly silence the crowd.")],
            "Sona": [(lambda: p.deaths >= 8, "You played Sona. You are essentially a highly musical caster minion. I hope rolling your face across Q, W, and E was mentally stimulating enough for you before you inevitably exploded.")],
            "Singed": [(lambda: True, "You locked in Singed. You didn't log in to play League of Legends, you logged in to run in circles and farm proxy waves while everyone else played a completely different video game. Absolute sociopathic behavior.")],
            "Aurelion Sol": [(lambda: p.time < 1500 and not p.win, "You picked Aurelion Sol and the game ended before 25 minutes. A majestic, cosmic dragon reduced to a glorified lizard who couldn't scale fast enough to matter.")],
            "Mel": [(lambda: not p.win, "You played Mel. You tried to play politics and manipulate the board, only to realize that a fed enemy Top Laner simply does not care about your diplomatic immunity. A tragic miscalculation.")],
            "Ambessa": [(lambda: p.deaths >= 8, "Ambessa Medarda. You charged in screaming about Noxian superiority, only to be immediately crowd-controlled and swatted like a fly. Truly a terrifying warlord.")],
            "Jinx": [(lambda: p.deaths >= 10, "You picked Jinx. You clearly watched the show and thought you could replicate the magic. Instead, you just gave the enemy team 300 gold repeatedly. Stick to Netflix.")],
            "Vi": [(lambda: p.deaths > p.kills, "Vi stands for 'Violence', not 'Victim'. You punched exactly one person, got instantly deleted, and left your team in a 4v5. Brilliant police work.")],
            "Caitlyn": [(lambda: p.damage < 15000, "A sniper with the longest range in the game, and yet you dealt absolutely zero damage. Were your bullets made of foam, or did you simply forget to pull the trigger?")],
            "Hwei": [(lambda: p.damage < 15000, "Ah, Hwei. You spent the entire game mixing paints and calculating the perfect combination of 10 different spells, just to deal absolutely zero damage. A true starving artist.")],
            "Smolder": [(lambda: p.time < 1500 and not p.win, "You picked a late-game baby dragon and lost before you could even learn how to breathe fire. A tragic reptilian failure.")],
            "Shaco": [(lambda: True, "You picked Shaco. You didn't log in to win, you logged in to make nine other people utterly miserable. I respect the pure malice.")],
            "Master Yi": [(lambda: p.kills >= 15, "Ah, a fed Master Yi. You pressed Q repeatedly and the enemy team fell over. Shall we throw a parade for such unparalleled mechanical brilliance?")],
            "Tryndamere": [(lambda: p.turrets == 0, "You played Tryndamere and took zero towers. Your one job—your singular purpose in this universe—is to hit stationary buildings, and you failed. Utterly embarrassing.")],
            "Bel'Veth": [(lambda: p.time > 1800 and not p.win, "You are the Empress of the Void. You are meant to swallow the world. Instead, you slapped people at mach speed for 30 minutes and lost. A rather underwhelming apocalypse.")]
        }

        return champ_map.get(p.champ, [])

    def _tragedy_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.deaths >= 15, f"{p.deaths} deaths. Were you trying to break a world record, or did you just forget that your monitor was turned on? Absolutely tragic."),
            (lambda: p.kills == 0 and p.deaths >= 10, "Zero kills. Double-digit deaths. I am genuinely impressed by your ability to serve as a walking, breathing ATM for the enemy team."),
            (lambda: p.win and p.deaths >= 10 and p.kills < 4, "You won... but let us not pretend you had anything to do with it. You were merely a heavy backpack for your team to carry."),
            (lambda: p.fb and not p.win and p.deaths >= 8, "You secured First Blood! ...And then proceeded to feed for the rest of the game. You peaked at minute three."),
            (lambda: p.kills > 12 and p.turrets == 0 and not p.win, f"You had {p.kills} kills and didn't touch a single tower. The Nexus is the objective, darling, not your KDA. Enjoy the defeat screen."),
            (lambda: p.damage_taken > 50000 and p.deaths >= 10, f"You took {p.dmg_taken:,} damage. You weren't a tank, you were a piñata. And the enemy team beat the absolute candy out of you."),
            (lambda: p.deaths <= 10 and p.kills <= 1, "At what point during your tenth trip back to the fountain did you realize that the enemy team was farming you like a cannon minion?",)
        ]

    def _economy_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.gold > 20000 and p.damage < 15000, "Over 20,000 gold and less than 15k damage. What, did you open a high-yield savings account on the Rift? Spend your gold and actually fight!"),
            (lambda: p.gold < 6000 and p.time > 1500, f"Under 6k gold in a {p.time // 60}-minute game? You weren't playing a champion, you were playing a medieval peasant."),
            (lambda: p.gold > 18000 and not p.win and p.kills < 5, "18,000 gold in your pockets, and yet you still lost while getting barely any kills. You are the definitive proof that money simply cannot buy talent."),
            (lambda: p.gold > 15000 and p.deaths >= 10 and p.kills >= 10, "Ah, the classic 'Robin Hood' playstyle. Amass a massive fortune through kills, only to immediately die and donate all your shutdown gold to the poor enemy team."),
            (lambda: p.gold > 16000 and p.turrets == 0 and (p.kills + p.assists) <= 3, "You farmed over 16,000 gold, ignored every team fight, and touched exactly zero towers. Are you playing a competitive MOBA, or a farming simulator? Go plant some crops.")
        ]

    def _role_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.role == "UTILITY" and p.vision_wards < 2 and p.time > 1200, "You played Support and bought fewer than 2 Control Wards. That isn't a strategy, that is a crime against your ADC. Disgusting."),
            (lambda: p.role == "UTILITY" and p.cs > 80 and p.gold > 11000, "A 'Support' with over 80 CS and a massive bank account? You weren't supporting your ADC, you were violently taxing them into poverty."),
            (lambda: p.vision_score < 5 and p.time > 1500, "A vision score of less than 5 in a 25-minute game? Do you play with your monitor turned off, or do you just enjoy the element of surprise when the enemy Jungler kills you?"),
            (lambda: p.turrets >= 4 and p.win, "Four towers destroyed! You didn't play a MOBA, you played a demolition simulator. The enemy base is in absolute ruins because of you.")
        ]

    def _praise_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.kills >= 15 and p.deaths <= 3 and p.win, "Incredible carry. Your back must be absolutely aching from dragging those four heavy weights to the finish line. A flawless performance!"),
            (lambda: p.kills >= 15 and p.damage > 35000 and not p.win, "You fought valiantly. You dealt the damage. You secured the kills. And yet... your Nexus still exploded. What a beautiful, heartbreaking tragedy."),
            (lambda: p.assists >= 25 and p.deaths < 5 and p.win, f"{p.assists} assists and barely a scratch on you. You are the invisible maestro orchestrating this victory. I tip my hat to you, unsung hero."),
            (lambda: p.damage > 40000 and p.gold < 11000, "Over 40,000 damage on less than 11k gold? Truly the pinnacle of budget-friendly efficiency. You did more with pocket change than most players do with a full six-item build.")
        ]

    def _mediocre_rules(self) -> list:
        p = self.p
        loss_quotes = [
            "You weren't the carry, but you weren't the feeder either. You simply existed as a background character in someone else's tragedy. How incredibly boring.",
            "A perfectly average defeat. You did nothing special, you fed no one special. You are the human equivalent of plain oatmeal.",
            "I would roast you, but your performance was so painfully average that I cannot even find the motivation. Please, do something interesting next time.",
            "You were essentially a highly realistic NPC. The enemy team barely registered your existence as they destroyed your Nexus.",
            "An aggressively mediocre performance. You didn't lose the game for your team, but you certainly didn't fight to win it, either.",
            "You participated in this defeat with all the enthusiasm of a soggy piece of bread. Absolutely nothing to write home about.",
            "A masterclass in sheer adequacy! You managed to achieve absolutely nothing of note while your Nexus crumbled around you.",
            "I suppose someone has to play the role of 'Extra #4' in this tragedy. Congratulations on hitting your marks before the curtain fell.",
            "You did not shine, nor did you burn. You merely flickered out quietly, like a damp candle in a drafty room.",
            "I have seen more passion from caster minions. You were a perfectly gray smudge on an otherwise colorful canvas of failure.",
            "You rode the coattails of your superiors with remarkable grace. Make sure to polish their boots as a thank you for the LP.",
            "A victory! How lovely for you. Please do not delude yourself into thinking you were anything more than a glorified spectator with a front-row seat.",
            "You contributed just enough to avoid an AFK penalty, and for that, the system has rewarded you. How inspiring.",
            "You are the living embodiment of a participation trophy. Take your LP and quietly exit the stage before someone asks what you actually did.",
            "A win is a win, I suppose. Even the stowaway gets to claim they crossed the ocean."
        ]
        win_quotes = [
            "A completely unremarkable performance. You merely showed up, coasted on the achievements of your betters, and claimed the LP.",
            "You won! ...And yet, the statistics imply you spent the entire game spectating your own team. A brilliant strategy of doing absolutely nothing.",
            "Congratulations on being successfully carried. I hope you thanked your teammates for tucking you comfortably into their backpacks.",
            "An incredibly forgettable victory. You were there, buttons were pressed, the game ended. Truly thrilling.",
            "You secured the victory by simply not feeding. Sometimes, being incredibly boring is the best strategy of all.",
            "Are you attempting a pacifist speedrun of League of Legends? Because dealing this little damage is practically an art form.",
            "I must commend your commitment to non-violence. Unfortunately, this is a competitive arena, not a wellness retreat. Wake up.",
            "Did your mouse disconnect, or did you simply take a vow of peace? Your lack of presence in this match is genuinely breathtaking.",
            "You avoided conflict so thoroughly that I am surprised the enemy team didn't forget you were logged in. A ghost in the machine.",
            "Your damage numbers are so astronomically low, I am forced to assume you were aggressively apologizing to the enemy every time you clicked."
        ]
        afk_quotes = [
            "Are you absolutely certain you were playing League of Legends? Your stats suggest you were merely on a leisurely stroll through the jungle while your team fought a war.",
            "Look at this damage chart. Were you aggressively farming the Krugs while your team fought for their lives? A masterclass in pacifism.",
            "You dealt less damage than an angry cannon minion. I am genuinely curious what you were doing for the past 30 minutes.",
            "A completely victimless game from you. You refused to hurt anyone. How noble, and how utterly useless."
        ]

        return [
            # random.choice() will pick a different sentence every single time this runs
            (lambda: 3 <= p.kills <= 7 and 3 <= p.deaths <= 7 and not p.win, random.choice(loss_quotes)),
            (lambda: 3 <= p.kills <= 7 and 3 <= p.deaths <= 7 and p.win, random.choice(win_quotes)),
            (lambda: p.kills < 4 and p.deaths < 4 and p.damage < 12000, random.choice(afk_quotes))
        ]

    def _macro_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.time > 2100 and p.turrets == 0, "A 35-minute game and you didn't destroy a single tower. Were you under the impression that the enemy Nexus would simply collapse out of sheer boredom?"),
            (lambda: p.damage > 40000 and p.turrets == 0 and not p.win, "All that damage, yet you refused to hit a stationary building. League of Legends is a game of real estate, darling, not a gladiatorial arena. Hold this well-deserved loss."),
            (lambda: p.cs > 350 and p.turrets == 0 and p.assists < 5, "You hit minions for 40 minutes, ignored every team fight, and took zero towers. Your dedication to PVE is inspiring. Have you considered playing Minecraft instead?"),
            (lambda: p.role == "JUNGLE" and p.turrets == 0 and p.damage < 10000, "A Jungler who deals no damage and takes no towers. I assume you spent the entire game reading a book while mindlessly clicking on Gromp?")
        ]

    def _coward_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.deaths == 0 and p.damage < 10000 and p.time > 1500, "Zero deaths? How wonderful! It is quite easy to survive when you spend the entire match hiding two screens behind your team, watching them die. A true coward."),
            (lambda: p.kills >= 10 and p.damage < 15000 and p.time > 1500, "Ten kills with less than 15,000 damage. You are not a carry, you are simply a vulture swooping in to steal the glory from your starving team."),
            (lambda: p.healing == 0 and p.role == "UTILITY" and p.deaths == 0 and not p.win, "You played Support, healed no one, and never died while your team lost. Let me guess: you abandoned your ADC at minute five to preserve your precious KDA?")
        ]

    def _anomaly_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.kills == 0 and p.deaths == 0 and p.assists == 0 and p.time > 900, "0 kills. 0 deaths. 0 assists. Did your internet disconnect, or did you achieve true enlightenment and transcend the need to actually play the game?"),
            (lambda: not p.fb and p.deaths >= 13 and p.time < 1500, "Dying 13 times in 25 minutes? You were not simply beaten; you were relentlessly bullied. I would sincerely suggest finding a new hobby. Perhaps gardening?"),
            (lambda: p.vision_score > 100, "A vision score over 100! You were not playing a MOBA, you were operating a state-of-the-art surveillance network. Paranoia suits you, detective.")
        ]

    def get_all_rules(self) -> list:
        # Order matters! Priority cascades from Top to Bottom.
        return (
            self._champion_rules() +
            self._tragedy_rules() +
            self._economy_rules() +
            self._role_rules() +
            self._praise_rules() +
            self._mediocre_rules() +
            self._macro_rules() +
            self._coward_rules() +
            self._anomaly_rules()
        )