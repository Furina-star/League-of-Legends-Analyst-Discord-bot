"""
This is just a dictionary for post match review roasts.
It is used in the post_match_review function in discord_bot.py.
The keys are the roast types and the values are lists of roasts.
The roasts can contain {champion} which will be replaced with the champion name of the player being roasted.
"""

import random
from utils.data_loader import ITEM_NAME_TO_ID

# Roast and Praise dictionary
# The rules are organized into categories: Champion-Specific, Tragedy, Economy, Role-Specific, and Praise.
class ParsedStats:
    def __init__(self, stats: dict):
        # Base Stats
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
        self.game_mode = stats.get('gameMode', 'Unknown Mode')
        self.match_id = stats.get('matchId', 'Unknown ID')
        self.cs = stats.get('totalMinionsKilled', 0) + stats.get('neutralMinionsKilled', 0)
        self.gold = stats.get('goldEarned', 0)
        self.vision_score = stats.get('visionScore', 0)
        self.healing = stats.get('totalHeal', 0)

        # Advanced Calculated Stats (For Tags and Roasts!)
        self.minutes = self.time / 60.0 if self.time > 0 else 1.0
        self.cs_per_min = self.cs / self.minutes

        self.team_kills = stats.get('teamKills', 1)
        self.kp_percent = ((self.kills + self.assists) / self.team_kills) * 100 if self.team_kills > 0 else 0.0

        # Objective & Milestone Stats
        self.first_blood = stats.get('firstBloodKill', False)
        self.pentas = stats.get('pentaKills', 0)
        self.quadras = stats.get('quadraKills', 0)
        self.turrets = stats.get('turretKills', 0)
        self.stolen_objs = stats.get('objectivesStolen', 0)
        self.dragons = stats.get('dragonKills', 0)

        # Get the Rival's stats
        self.rival = stats.get('rivalStats', None)
        if self.rival:
            self.r_dmg = self.rival.get('totalDamageDealtToChampions', 0)
            self.r_gold = self.rival.get('goldEarned', 0)
            self.r_cs = self.rival.get('totalMinionsKilled', 0) + self.rival.get('neutralMinionsKilled', 0)
            self.r_champ = self.rival.get('championName', 'your lane opponent')
            self.r_vision = self.rival.get('visionScore', 0)
            self.r_deaths = self.rival.get('deaths', 0)
        else:
            self.r_dmg = self.r_gold = self.r_cs = self.r_vision = self.r_deaths = 0
            self.r_champ = "Unknown"

        # Item Extraction
        self.items = [
            stats.get('item0', 0), stats.get('item1', 0), stats.get('item2', 0),
            stats.get('item3', 0), stats.get('item4', 0), stats.get('item5', 0)
        ]
        self.item_count = sum(1 for i in self.items if i != 0)
        self.trinket = stats.get('item6', 0)

        # Keystone Extraction
        self.keystone_id = None
        try:
            self.keystone_id = str(stats['perks']['styles'][0]['selections'][0]['perk'])
        except (KeyError, IndexError):
            pass

    # Calculates a rough performance letter grade.
    def get_grade(self) -> str:
        score = 0

        # Calculate Score using Boolean Math (True = 1, False = 0)
        # Example: If KP is 70%, it evaluates to (1) + (1) = 2 points!
        score += (self.kp_percent > 45.0) + (self.kp_percent > 65.0)

        if self.role == "UTILITY":
            score += (self.vision_score > self.minutes) + (self.vision_score > self.minutes * 2)
        else:
            score += (self.cs_per_min > 6.0) + (self.cs_per_min > 8.0)

        # Deaths give points for being low, and subtract 2 for feeding
        score += (self.deaths <= 5) + (self.deaths <= 2)
        score -= 2 * (self.deaths >= 10)

        # Convert score to letter grade without massive if/elif chains
        grade_map = [(5, "S+"), (4, "A"), (3, "B"), (1, "C"), (0, "D")]

        # next() searches the map top-to-bottom and returns the first match. Default is "F".
        return next((grade for limit, grade in grade_map if score >= limit), "F")

# Initialized variables for shuffle deck algorithm
last_win_quotes = []
last_loss_quotes = []

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
            (lambda: p.win and p.deaths >= 10 and p.kills < 4, "You won... but let us not pretend you had anything to do with it. You were merely a heavy backpack for your team to carry."),
            (lambda: p.first_blood and not p.win and p.deaths >= 8, "You secured First Blood! ...And then proceeded to feed for the rest of the game. You peaked at minute three."),
            (lambda: p.kills > 12 and p.turrets == 0 and not p.win, f"You had {p.kills} kills and didn't touch a single tower. The Nexus is the objective, darling, not your KDA. Enjoy the defeat screen."),
            (lambda: p.deaths >= 15, f"{p.deaths} deaths. Were you trying to break a world record, or did you just forget that your monitor was turned on? Absolutely tragic."),
            (lambda: p.kills == 0 and p.deaths >= 10, "Zero kills. Double-digit deaths. I am genuinely impressed by your ability to serve as a walking, breathing ATM for the enemy team."),
            (lambda: p.damage_taken > 50000 and p.deaths >= 10, f"You took {p.damage_taken:,} damage. You weren't a tank, you were a piñata. And the enemy team beat the absolute candy out of you."),
            (lambda: p.deaths <= 10 and p.kills <= 1, "At what point during your tenth trip back to the fountain did you realize that the enemy team was farming you like a cannon minion?"),
            (lambda: p.gold > 15000 and p.item_count <= 3 and p.time > 1500, "You finished the game with 15,000 gold and only three items. Are you trying to take that gold with you into the next match? Spend your fortune, you miser!"),
            (lambda: p.rival is not None and p.gold > p.r_gold + 3000 and p.damage < p.r_dmg and not p.win, f"You had a 3,000 gold lead over the {p.r_champ} and still dealt less damage. You are the definitive proof that a large bank account cannot compensate for a lack of mechanical soul."),
            (lambda: p.role in ['MIDDLE', 'BOTTOM'] and p.gold < 8000 and p.time > 1500, "A carry with less than 8k gold at 25 minutes? You weren't a threat; you were a charity case. I've seen more financial stability in a dumpster fire."),
            (lambda: p.gold > 14000 and p.deaths >= 8 and not p.win, "You amassed a fortune and then proceeded to hand it over to the enemy team in 1,000-gold increments. You aren't a player; you're a high-stakes stimulus package for the opposition.")
        ]

    def _economy_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.gold > 18000 and not p.win and p.kills < 5, "18,000 gold in your pockets, and yet you still lost while getting barely any kills. You are the definitive proof that money simply cannot buy talent."),
            (lambda: p.gold > 20000 and p.damage < 15000, "Over 20,000 gold and less than 15k damage. What, did you open a high-yield savings account on the Rift? Spend your gold and actually fight!"),
            (lambda: p.gold < 6000 and p.time > 1500, f"Under 6k gold in a {p.time // 60}-minute game? You weren't playing a champion, you were playing a medieval peasant."),
            (lambda: p.gold > 15000 and p.deaths >= 10 and p.kills >= 10, "Ah, the classic 'Robin Hood' playstyle. Amass a massive fortune through kills, only to immediately die and donate all your shutdown gold to the poor enemy team."),
            (lambda: p.gold > 16000 and p.turrets == 0 and (p.kills + p.assists) <= 3, "You farmed over 16,000 gold, ignored every team fight, and touched exactly zero towers. Are you playing a competitive MOBA, or a farming simulator? Go plant some crops.")
        ]

    def _role_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.role == "UTILITY" and p.vision_wards < 2 and p.time > 1200, "You played Support and bought fewer than 2 Control Wards. That isn't a strategy, that is a crime against your ADC. Disgusting."),
            (lambda: p.role == "UTILITY" and p.cs > 80 and p.gold > 11000, "A 'Support' with over 80 CS and a massive bank account? You weren't supporting your ADC, you were violently taxing them into poverty."),
            (lambda: p.vision_score < 5 and p.time > 1500, "A vision score of less than 5 in a 25-minute game? Do you play with your monitor turned off, or do you just enjoy the element of surprise when the enemy Jungler kills you?"),
            (lambda: p.turrets >= 5 and p.kp_percent < 30.0 and p.win, "Five towers destroyed with almost zero team fight participation. You didn't play a MOBA, you played a single-player demolition simulator while your team fought for their lives. Horrifyingly antisocial, yet effective."),
            (lambda: p.role == 'JUNGLE' and p.stolen_objs == 0 and p.dragons == 0 and p.win, "You won, but let's be clear: the drakes were practically begging to be taken and you ignored them all. Your lanes won despite your total lack of objective control."),
            (lambda: p.role == 'BOTTOM' and p.deaths >= 10 and p.damage > 30000, "A classic ADC performance. You dealt a massive amount of damage, but you also spent half the game looking at a grey screen. Positioning is a skill, bro, try using it next time."),
            (lambda: p.role == 'TOP' and p.kp_percent < 20.0 and p.time > 1800, "The game lasted over 30 minutes and you were involved in less than 20% of the kills. I assume you and the enemy Top laner reached a peace treaty while the rest of the map was at war?"),
            (lambda: p.role == 'MIDDLE' and p.deaths > (p.kills + p.assists) and p.time > 1200, "As a Mid laner, you are meant to be the center of the map, not the center of the enemy's highlight reel. Your kill participation is lower than your death count—mathematically embarrassing."),
            (lambda: p.role == 'UTILITY' and p.damage > p.team_kills * 1000 and p.vision_score < p.minutes, "You dealt plenty of damage, but your vision score is lower than the time it took for the game to end. You aren't a support; you're just a greedy mage who didn't want to wait in the Mid lane queue.")
        ]

    def _praise_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.kills >= 15 and p.deaths <= 3 and p.win, "Incredible carry. Your back must be absolutely aching from dragging those four heavy weights to the finish line. A flawless performance!"),
            (lambda: p.kills >= 15 and p.damage > 35000 and not p.win, "You fought valiantly. You dealt the damage. You secured the kills. And yet... your Nexus still exploded. What a beautiful, heartbreaking tragedy."),
            (lambda: p.assists >= 25 and p.deaths < 5 and p.win, f"{p.assists} assists and barely a scratch on you. You are the invisible maestro orchestrating this victory. I tip my hat to you, unsung hero."),
            (lambda: p.damage > 40000 and p.gold < 11000, "Over 40,000 damage on less than 11k gold? Truly the pinnacle of budget-friendly efficiency. You did more with pocket change than most players do with a full six-item build."),
            (lambda: p.role == 'JUNGLE' and p.stolen_objs >= 2, "Two or more objectives stolen? You didn't just play Jungle; you were a phantom in their pit. The enemy Jungler is likely uninstalling as we speak. Magnificent work."),
            (lambda: p.kp_percent >= 80.0 and p.win, "Over 80% kill participation! You were everywhere, doing everything, all at once. The map was your stage, and you were the undisputed lead actor."),
            (lambda: p.win and p.time < 1500 and p.kills >= 10 and p.deaths <= 1, "A sub-25 minute victory with double-digit kills and almost zero deaths. That wasn't a match; it was a public execution. I almost feel sorry for them. Almost."),
            (lambda: p.turrets >= 6 and p.win, "Six towers destroyed! You didn't just win the game; you personally dismantled their entire civilization. A true architect of destruction.")
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
            "A completely victimless game from you. You refused to hurt anyone. How noble, and how utterly useless.",
            "You played a carry role and dealt less damage than the Support's ignite. I suggest you apologize to your keyboard for wasting its mechanical life cycle.",
            "Your presence on the map was essentially a rumor. The enemy team didn't even buy armor because they simply didn't consider you a threat.",
            "I've seen more aggressive behavior from a scuttle crab. You spent 30 minutes in a high-stakes arena and somehow remained a complete pacifist.",
            "Were you attempting to win through the power of friendship? Because your damage numbers suggest you didn't land a single hostile ability all game."
        ]

        return [
            # random.choice() will pick a different sentence every single time this runs
            (lambda: 3 <= p.kills <= 7 and 3 <= p.deaths <= 7 and not p.win, random.choice(loss_quotes)),
            (lambda: 3 <= p.kills <= 7 and 3 <= p.deaths <= 7 and p.win, random.choice(win_quotes)),
            (lambda: p.kills < 4 and p.deaths < 4 and p.damage < 12000 and p.role != 'UTILITY', random.choice(afk_quotes))
        ]

    def _macro_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.time > 2100 and p.turrets == 0, "A 35-minute game and you didn't destroy a single tower. Were you under the impression that the enemy Nexus would simply collapse out of sheer boredom?"),
            (lambda: p.damage > 40000 and p.turrets == 0 and not p.win, "All that damage, yet you refused to hit a stationary building. League of Legends is a game of real estate, darling, not a gladiatorial arena. Hold this well-deserved loss."),
            (lambda: p.cs > 350 and p.turrets == 0 and p.assists < 5, "You hit minions for 40 minutes, ignored every team fight, and took zero towers. Your dedication to PVE is inspiring. Have you considered playing Minecraft instead?"),
            (lambda: p.role == "JUNGLE" and p.turrets == 0 and p.damage < 10000, "A Jungler who deals no damage and takes no towers. I assume you spent the entire game reading a book while mindlessly clicking on Gromp?"),
            (lambda: p.kills >= 10 and p.turrets == 0 and p.dragons == 0 and not p.win, "You treated the Rift like a Team Deathmatch. You secured ten kills, ignored every tower, and let every dragon slip away. A spectacular failure to understand the win condition."),
            (lambda: p.cs_per_min >= 8.5 and p.damage < 15000 and p.turrets == 0 and not p.win, f"An impressive {p.cs_per_min:.1f} CS per minute, yet you dealt less damage than the Support. You weren't a carry; you were just an exceptionally wealthy minion-slayer."),
            (lambda: p.role == 'JUNGLE' and p.turrets == 0 and p.dragons == 0 and p.win, "You won, but the map remains untouched by your hands. I assume your strategy was to let your team do the actual work while you wandered aimlessly through the bushes?")
        ]

    def _coward_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.deaths == 0 and p.damage < 10000 and p.time > 1500, "Zero deaths? How wonderful! It is quite easy to survive when you spend the entire match hiding two screens behind your team, watching them die. A true coward."),
            (lambda: p.kills >= 10 and p.damage < 15000 and p.time > 1500, "Ten kills with less than 15,000 damage. You are not a carry, you are simply a vulture swooping in to steal the glory from your starving team."),
            (lambda: p.healing == 0 and p.role == "UTILITY" and p.deaths == 0 and not p.win, "You played Support, healed no one, and never died while your team lost. Let me guess: you abandoned your ADC at minute five to preserve your precious KDA?"),
            (lambda: p.deaths == 0 and not p.win and p.damage < 12000 and p.time > 1200, "The Nexus exploded and you still have zero deaths. Did you spend the final stand hiding in the fountain to protect your precious KDA? A truly spineless performance."),
            (lambda: p.damage > 25000 and p.damage_taken < 8000 and not p.win, "You dealt plenty of damage, but you took almost none. You were so terrified of getting hit that you let your team die for every single kill you took. A selfish, hollow display."),
            (lambda: p.assists >= 20 and p.damage < 8000 and p.role != 'UTILITY', "Twenty assists with less than 8,000 damage. You weren't 'facilitating' your team; you were merely standing nearby and throwing a single auto-attack to claim credit for their hard work.")
        ]

    def _anomaly_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.kills == 0 and p.deaths == 0 and p.assists == 0 and p.time > 900, "0 kills. 0 deaths. 0 assists. Did your internet disconnect, or did you achieve true enlightenment and transcend the need to actually play the game?"),
            (lambda: not p.first_blood and p.deaths >= 13 and p.time < 1500, "Dying 13 times in 25 minutes? You were not simply beaten; you were relentlessly bullied. I would sincerely suggest finding a new hobby. Perhaps gardening?"),
            (lambda: p.vision_score > 100, "A vision score over 100! You were not playing a MOBA, you were operating a state-of-the-art surveillance network. Paranoia suits you, detective."),
            (lambda: p.win and p.kills == 0 and p.assists == 0 and p.time > 1200, "You won a 20-minute game without participating in a single kill. You were essentially a ghost—present on the map, yet entirely non-existent in the conflict."),
            (lambda: (p.pentas >= 1 or p.quadras >= 1) and not p.win and p.deaths >= 10, "A multikill followed by a double-digit death count and a loss. You reached the pinnacle of mechanics only to immediately plummet back into the abyss. A chaotic, confusing tragedy."),
            (lambda: p.vision_score > (p.minutes * 3) and p.role == 'UTILITY', f"A vision score of {p.vision_score}! You've illuminated the Rift so thoroughly that the fog of war is practically a myth. A obsessive, beautiful dedication to surveillance.")
        ]

    def _item_rules(self) -> list:
        p = self.p
        inv = set(p.items)

        def has(name: str) -> bool:
            return ITEM_NAME_TO_ID.get(name, -1) in inv
        item_map = {
            "Mejai's Soulstealer": [
                (lambda: p.deaths >= 5, "You bought Mejai's and died five or more times. Every single death deleted a portion of your investment. You didn't buy an item. You bought a subscription to disappointment."),
                (lambda: p.deaths < 5 and not p.win and p.kills < 5, "You purchased Mejai's Soulstealer. A bold declaration of confidence from someone who accomplished absolutely nothing with it. The stacks never came. They never do."),
                (lambda: p.deaths < 5 and p.win and p.kills >= 10, "You bought Mejai's and it actually paid off. I refuse to congratulate you. The item is a coin flip and you landed heads. Enjoy it while it lasts.")
            ],
            "Tear of the Goddess": [(lambda: p.time < 1200, "You stacked Tear of the Goddess in a game that ended before 20 minutes. You spent the entire match auto-attacking minions to charge an item that never mattered. A riveting strategy.")],
            "Archangel's Staff": [(lambda: p.damage < 10000, "Archangel's Staff. The item you build after patiently stacking Tear for the entire early game. You completed this ancient ritual and then dealt absolutely no damage. The mana was for nothing.")],
            "Manamune": [(lambda: p.role in ['UTILITY', 'JUNGLE'], "Manamune on a Support or Jungler. I see you have found a creative solution to a problem that did not exist. Your commitment to building incorrectly is genuinely inspiring.")],
            "Warmog's Armor": [(lambda: p.role in ['MIDDLE', 'BOTTOM'] and p.damage < 15000, "Warmog's Armor on a carry. You didn't come here to deal damage. You came here to simply exist, absorb resources, and be unkillable while contributing absolutely nothing. A bold life choice.")],
            "Thornmail": [(lambda: p.role in ['MIDDLE', 'BOTTOM'], "Thornmail on a carry. Your grand strategy was to get hit repeatedly and hope the passive killed them. Truly a revolutionary approach to dealing damage in a damage-dealing role.")],
            "Guardian Angel": [
                (lambda: p.deaths == 0, "You built Guardian Angel and never died. The passive never activated. You paid 2,800 gold for a security blanket you never needed. A stunning display of financial anxiety."),
                (lambda: p.deaths >= 8, "You built Guardian Angel and still died eight times. Guardian Angel revives you once, not repeatedly. It is not a subscription service for dying.")
            ],
            "Banshee's Veil": [(lambda: p.role in ['BOTTOM', 'JUNGLE'] and p.deaths >= 6, "Banshee's Veil blocks one spell. One. You died six times anyway. The shield either expired immediately or you walked directly into five abilities the moment it popped. Either way, not your finest hour.")],
            "Rabadon's Deathcap": [
                (lambda: p.damage < 15000, "Rabadon's Deathcap. The item that amplifies your ability power by a massive percentage. You built it and dealt less than 15,000 damage. What exactly were you amplifying? Your AFK time?"),
                (lambda: p.role in ['TOP', 'JUNGLE'] and p.damage < 20000, "Rabadon's Deathcap in the Top lane or Jungle with minimal damage. Somewhere, a real AP mage is weeping softly at what you have done to their signature item.")
            ],
            "Void Staff": [(lambda: p.damage < 12000, "Void Staff is specifically designed to shred magic resistance so your spells deal more damage. Yours dealt no damage with or without the penetration. The enemies were not the problem.")],
            "Shadowflame": [(lambda: p.role in ['TOP', 'JUNGLE', 'BOTTOM'], "Shadowflame on a non-mage. The item grants ability power and magic penetration — two stats you are biologically incapable of using in your current role. Bold. Wrong. But bold.")],
            "Infinity Edge": [
                (lambda: p.role in ['UTILITY', 'JUNGLE'], "Infinity Edge on a Support or Jungler. You didn't buy a crit amplifier. You bought a very expensive trophy your teammates had to carry around their necks all game."),
                (lambda: p.damage < 12000, "Infinity Edge. Maximum critical strike damage. You built it and the damage numbers suggest your critical strikes were hitting enemies made entirely of feathers.")
            ],
            "Heartsteel": [
                (lambda: p.role in ['MIDDLE', 'BOTTOM', 'UTILITY'], "Heartsteel on a non-tank. You are a carry who has decided that 6,000 health is a valid substitution for skill. It is not. Your team needed damage. You brought a gymnasium."),
                (lambda: p.damage > 25000, "You built Heartsteel and still dealt meaningful damage. I find this deeply irritating. Please pick a lane — are you a tank or a carry? Your identity crisis is confusing everyone.")
            ],
            "Ardent Censer": [(lambda: p.role != 'UTILITY', "Ardent Censer on a non-support. Your healing and shielding numbers were presumably so impressive that you decided to buff them. They were not impressive.")],
            "Moonstone Renewer": [(lambda: p.role not in ['UTILITY', 'MIDDLE'], "Moonstone Renewer on a non-support. You are healing allies with an item that requires you to be in combat — in a role where you are supposed to be doing the combat, not spectating it.")],
            "Locket of the Iron Solari": [(lambda: p.role in ['MIDDLE', 'BOTTOM', 'JUNGLE'], "Locket of the Iron Solari on a non-support. You shielded your teammates. How thoughtful. How completely unnecessary. How absolutely devastating for your team's damage output.")],
            "Sunfire Aegis": [(lambda: p.role in ['MIDDLE', 'BOTTOM'], "Sunfire Aegis on a damage dealer. Your strategy was to deal damage slowly, over time, by standing next to enemies and hoping the burn finished them. This is not a strategy. This is a retirement plan.")],
            "Trinity Force": [(lambda: p.role == 'UTILITY', "Trinity Force on a Support. Somewhere inside you there is a Top laner screaming to be let out. Your team needed a support. They got this instead.")],
            "Iceborn Gauntlet": [(lambda: p.role in ['MIDDLE', 'BOTTOM'], "Iceborn Gauntlet on a carry. You slowed the enemies so thoroughly that they had all the time in the world to watch you fail to kill them with your complete lack of damage items.")]}

        rules = []
        for item_name, specific_rules in item_map.items():
            if has(item_name):
                rules.extend(specific_rules)

        return rules

    def _macro_item_rules(self) -> list:
        p = self.p
        inv = set(p.items)

        def has(name: str) -> bool:
            return ITEM_NAME_TO_ID.get(name, -1) in inv

        def count(category_names: tuple) -> int:
            return sum(1 for name in category_names if has(name))

        armor = count(("Thornmail", "Frozen Heart", "Randuin's Omen", "Dead Man's Plate", "Gargoyle Stoneplate", "Iceborn Gauntlet"))
        ap = count(("Rabadon's Deathcap", "Void Staff", "Shadowflame", "Horizon Focus"))
        lethality = count(("Youmuu's Ghostblade", "Serpent's Fang", "Duskblade of Draktharr", "Edge of Night"))
        supp_items = count(("Ardent Censer", "Moonstone Renewer", "Staff of Flowing Water", "Shurelya's Battlesong", "Locket of the Iron Solari"))
        boots_count = count(("Berserker's Greaves", "Plated Steelcaps", "Mercury's Treads", "Sorcerer's Shoes", "Ionian Boots of Lucidity", "Boots of Swiftness", "Mobility Boots", "Boots", "Symbiotic Soles"))
        anti_heal = count(("Morellonomicon", "Thornmail", "Mortal Reminder", "Chempunk Chainsword", "Executioner's Calling", "Oblivion Orb", "Bramble Vest"))
        actives = count(("Zhonya's Hourglass", "Redemption", "Mikael's Blessing", "Youmuu's Ghostblade", "Randuin's Omen", "Hextech Rocketbelt", "Profane Hydra", "Ravenous Hydra", "Titanic Hydra"))
        atk_speed = count(("Phantom Dancer", "Rapid Firecannon", "Runaan's Hurricane", "Statikk Shiv", "Kraken Slayer", "Guinsoo's Rageblade", "Nashor's Tooth", "Blade of the Ruined King"))

        return [
            (lambda: boots_count == 0 and p.time > 1500 and p.champ not in ["Cassiopeia", "Yuumi"] and p.item_count < 6, "A 25-minute game, empty slots in your inventory, and you never purchased boots. You spent the entire match slowly waddling around the Rift like a lost toddler. Did you think sprinting was a premium feature?"),
            (lambda: anti_heal >= 2, "Multiple anti-heal items in the same inventory. Grievous Wounds do not stack, my clueless friend. The only thing you are reducing is your own damage output."),
            (lambda: actives >= 4, "Four or more active items in your inventory. Let’s be completely honest: you did not remember to press a single one of those buttons during a team fight, did you?"),
            (lambda: has("The Collector") and p.kills < 3, "You purchased The Collector. An item explicitly designed to execute enemies and secure kills. You finished the game with less than three kills. The only thing you collected was a defeat screen."),
            (lambda: atk_speed >= 3 and p.damage < 12000, "Three or more attack speed items but absolutely zero damage. You were slapping the enemy at Mach 3, yet dealing the equivalent of a light breeze. A terrifyingly fast tickle monster."),
            (lambda: armor >= 2 and lethality >= 2, "You mixed heavy armor with lethality. You are an assassin wearing a full suit of plate mail. You are neither stealthy nor unkillable; you are just a confused, clanking metal target."),
            (lambda: supp_items >= 2 and p.role in ['TOP', 'JUNGLE', 'BOTTOM'], "Multiple support items on a carry role. Your team needed someone to deal damage. You gave them a second support. Some crimes are unforgivable."),
            (lambda: armor >= 3 and p.role in ['MIDDLE', 'BOTTOM'], "Three or more armor items on a carry. The enemy team was not particularly fed. You simply decided that being a piece of furniture was preferable to being a threat."),
            (lambda: lethality >= 2 and p.role == 'UTILITY', "Multiple lethality items on a Support. You didn't come here to heal. You came here to murder. I respect the audacity. I do not respect the four deaths and zero kills that accompanied it."),
            (lambda: ap >= 2 and lethality >= 2, "AP items and lethality items in the same inventory. You have constructed a build so philosophically incoherent that I am not sure what you were trying to kill or how you expected to kill it."),
            (lambda: p.item_count <= 2 and p.time > 1800, "A 30-minute game and you finished with barely any items. Were you window-shopping in the store? Did the item prices offend you personally? This is borderline criminal negligence."),
            (lambda: p.item_count == 6 and p.damage < 10000 and p.role != 'UTILITY', "A complete six-item build. Every slot filled. Maximum gold spent. And yet your damage suggests the inventory was purely decorative. Truly an aesthetic build."),
            (lambda: p.item_count <= 1 and p.deaths >= 5, "One item. Five deaths. You were essentially a naked champion running into the enemy team. I sincerely hope this was not intentional.")
        ]

    def _objective_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.role == "JUNGLE" and p.dragons == 0 and p.time > 1200, "A Jungler who secured absolutely zero dragons. I assume the elemental drakes simply terrified you, or perhaps you forgot that the bottom half of the map exists?"),
            (lambda: p.stolen_objs >= 1, "You actually managed to steal an objective! A rare moment of competence. Do not let it go to your head, it was likely pure luck."),
            (lambda: p.role == "JUNGLE" and p.stolen_objs == 0 and p.dragons <= 1 and p.time > 1800, "Out-smited and out-maneuvered. You spent 30 minutes in the jungle and surrendered every major objective. You are not a Jungler; you are a glorified forest guide for the enemy team."),
            (lambda: p.role != "JUNGLE" and p.stolen_objs >= 1, "You stole an objective without having Smite. Your Jungler should be taking notes, and the enemy Jungler should be completely ashamed."),
            (lambda: p.role not in ['TOP', 'JUNGLE'] and p.turrets >= 3 and p.win, f"You personally brought down {p.turrets} towers as a {p.role.capitalize()}. It seems you were the only one who remembered that we win by destroying the Nexus, not just chasing kills. I am almost impressed."),
            (lambda: p.role == 'JUNGLE' and p.dragons >= 4 and p.win, "Four dragons secured. You treated the elemental drakes like your own personal pets. A dominant performance in objective control that even I cannot find a flaw in."),
            (lambda: p.win and p.turrets == 0 and p.dragons == 0 and p.stolen_objs == 0 and p.role != 'UTILITY', "Your team dismantled the enemy's entire infrastructure while you were... where, exactly? You finished a victory without touching a single objective. A masterclass in being a passenger."),
            (lambda: p.role == 'MIDDLE' and p.turrets >= 3 and p.win, "A Mid laner who actually hits the towers after a roam? A rare and beautiful sight. You didn't just win your lane; you deleted it from the map."),
            (lambda: (p.turrets >= 4 or p.dragons >= 3) and not p.win, "You secured the towers, you secured the drakes, and yet your team still found a way to collapse. You provided the foundation, but the rest of the cast simply forgot their lines. A tragic waste of macro.")
        ]

    def _rival_rules(self) -> list:
        p = self.p
        if not p.rival:
            return []

        return [
            (lambda: p.rival.get('deaths', 1) == 0 and p.time > 1200, f"You allowed the enemy {p.r_champ} to finish the game with absolutely zero deaths. You were less of a lane opponent and more of a harmless spectator."),
            (lambda: p.rival.get('kills', 0) >= (p.kills + 10), f"The enemy {p.r_champ} secured at least 10 more kills than you. They were the main character of this match, and you were merely their collateral damage."),
            (lambda: p.role == 'JUNGLE' and (p.kills + p.assists) > 0 and (p.rival.get('kills', 0) + p.rival.get('assists', 0)) > ((p.kills + p.assists) * 2), f"The enemy {p.r_champ} had more than double your kill participation. They were orchestrating map-wide destruction while you were apparently playing a cozy forest exploration game."),
            (lambda: p.damage > p.r_dmg and p.gold > p.r_gold and not p.win, f"You dealt more damage and earned more gold than the enemy {p.r_champ}, yet you still managed to lose. Having the statistical advantage means absolutely nothing if you lack the macro intellect to use it."),
            (lambda: p.r_gold > p.gold and p.r_cs > p.cs and p.rival.get('kills', 0) > p.kills and p.r_dmg > p.damage, f"Out-damaged, out-farmed, out-funded, and out-killed by the {p.r_champ}. An absolute, flawless gap in every single measurable category. You did not just lose; you were a tutorial bot."),
            (lambda: p.r_dmg > (p.damage * 2) and p.damage > 0, f"The enemy {p.r_champ} dealt more than double your damage. You did not just lose your lane, you were mathematically eclipsed by a superior player."),
            (lambda: p.r_cs > (p.cs + 80) and p.role in ['TOP', 'MIDDLE', 'BOTTOM'], f"The enemy {p.r_champ} out-farmed you by over 80 CS. Were you politely waiting for the minions to die of natural causes while they actually played the game?"),
            (lambda: p.role == "UTILITY" and p.r_vision > (p.vision_score * 2) and p.vision_score > 0, f"The enemy {p.r_champ} had more than double your vision score. Your team was playing in the dark while the enemy support built a literal surveillance state. Do your job."),
            (lambda: p.r_gold > (p.gold + 5000), f"The enemy {p.r_champ} generated 5,000 more gold than you. You were playing a survival horror game while they were playing a tycoon simulator. A massive 'diff' in every sense."),
            (lambda: p.champ == p.r_champ and p.deaths > p.r_deaths and not p.win, f"You played the exact same champion as your opponent, and they played it infinitely better. The mirror matchup does not lie. You are simply the inferior {p.champ}."),
            (lambda: p.win and p.damage > (p.r_dmg * 2) and p.r_dmg > 0, f"You dealt more than double the damage of the enemy {p.r_champ}. They weren't playing League of Legends; they were participating in a 30-minute interactive seminar on how to be completely irrelevant."),
            (lambda: p.win and p.kills >= (p.r_deaths + 5) and p.role in ['TOP', 'MIDDLE', 'BOTTOM'], f"The enemy {p.r_champ} was essentially your personal gold courier this match. I hope you thanked them for the generous donations toward your full build."),
            (lambda: p.win and p.gold > (p.r_gold + 4000), f"A massive 4,000 gold lead over the enemy {p.r_champ}. You were playing with the budget of a monarch while they were struggling to afford their own starter items. A truly pathetic gap.")
        ]

    def _multikill_rules(self) -> list:
        p = self.p
        return [
            (lambda: p.pentas >= 1 and not p.win, "You secured a Pentakill and still managed to lose the game. You peaked beautifully, only to immediately throw it all away. A spectacular, five-man tragedy."),
            (lambda: p.pentas >= 1 and p.win, "A Pentakill! An entire enemy team eradicated by your hand alone. I suppose I must offer my genuine applause. Try not to let it inflate your ego too much."),
            (lambda: p.quadras >= 1 and p.pentas == 0 and not p.win, "A Quadrakill followed by a Defeat screen. You desperately tried to be the hero, wiped out 80% of their team, and still couldn't save your Nexus. A magnificent, heartbreaking failure."),
            (lambda: p.quadras >= 1 and p.pentas == 0, "A Quadrakill. Four enemies dead, and yet... the fifth eluded you. Whether it was violently stolen by a teammate or you simply choked, you will always know you were one kill short of true perfection.")
        ]

    def get_fallback_quote(self) -> list:
        global last_win_quotes, last_loss_quotes

        win_quotes = [
            "A perfectly acceptable victory. Nothing more, nothing less.",
            "You won. The crowd goes mild.",
            "A victory so utterly standard it defies any attempt at commentary.",
            "You secured the win without doing anything remarkably stupid or remarkably brilliant. How quaint.",
            "The Nexus exploded in your favor, yet I am left entirely uninspired by how it happened.",
            "The Oratrice Mecanique d'Analyse Cardinale has ruled in your favor. Though personally, I found your performance lacking in dramatic tension.",
            "A victory! Yet the audience remains seated. You must learn to play to the balcony, my dear!",
            "You secured the win, but where was the flair? The drama? I was promised a grand opera, not a dress rehearsal!",
            "The curtain falls on a successful final act. Please, try to be the actual star of the show next time.",
            "Justice is served, and your Nexus stands. A perfectly adequate, if painfully uninspired, performance.",
            "I suppose I should offer a polite, lukewarm golf clap. *Clap.* There. Do not let it go to your head.",
            "You survived the stage today. The Oratrice has spared you my wrath... for now.",
            "A win is a win. Even the nameless extras in the background get to bow at the end of the play.",
            "The Oratrice remains silent, as does the audience. A victory achieved through sheer, unadulterated boredom.",
            "Bravo! You managed to win while being as exciting as a wet piece of cardboard. Truly, a unique talent.",
            "You won, but I shall be the one taking the bows. After all, it was my guidance that kept you from tripping over your own feet.",
            "A win is a win, I suppose, but where is the *sparkle*? You played like a stagehand when you should have been the lead!",
            "Justice has been served, though it was served with all the flavor of a plain baguette. Move along.",
            "The lights dim on your victory. It was a functional performance, but lacks the 'je ne sais quoi' I usually demand.",
            "You secured the LP. Now, if only you could secure a sense of style to match, we would truly have something to celebrate.",
            "A victory so unremarkable that I've already forgotten which champion you were playing. How... economical."
        ]

        loss_quotes = [
            "A rather embarrassing defeat. Please, try to be more entertaining next time.",
            "You lost. It was neither a spectacular tragedy nor a close match. It was simply a waste of time.",
            "Defeat. The most interesting thing about this match is that it eventually ended.",
            "You played, you lost, and the world continues to spin completely unchanged.",
            "A flawlessly generic defeat. You didn't even fail spectacularly enough to warrant a proper roast.",
            "The Oratrice Mecanique d'Analyse Cardinale has found you guilty... of being entirely forgettable in your defeat.",
            "A tragedy! But alas, a poorly written one. The audience is already demanding their refunds at the box office.",
            "You call that a performance? I have seen hilichurls display better macro on the stage.",
            "The curtain falls, the Nexus explodes, and the audience yawns. Try to feed with a bit more cinematic flair next time.",
            "Defeat. If this were a real opera in Fontaine, you would have been booed off the stage by the second act.",
            "You lost. As your director, I am seriously considering recasting your role for the next match.",
            "An utterly flavorless defeat. Even a true tragedy requires a hero; you were merely a bystander to your own demise.",
            "I expected a magnificent collapse, a dramatic final stand! Instead, you just... quietly surrendered. How incredibly boring.",
            "The Oratrice Mecanique d'Analyse Cardinale is not amused, and frankly, neither am I. Exit stage left, immediately!",
            "A tragedy without a climax is just a waste of a good costume. You should be ashamed of this narrative pacing.",
            "You lost, and you did it without a single shred of dignity. I’ve seen better footwork from a Geovishap Hatchling.",
            "Do you hear that? It's the sound of the audience leaving early. I suggest you follow their lead and log off.",
            "You were meant to be the protagonist! Instead, you were nothing more than a prop for the enemy's highlight reel.",
            "A defeat so profound it borders on performance art. Unfortunately, the art is terrible and I hate it.",
            "I’ve seen more coordination in a troupe of performing poodles. Your macro was a literal comedy of errors.",
            "The curtain falls on your shame. I shall be scrubbing my memory of this match with a very expensive fontainian wine.",
            "You didn't just lose; you failed to even make the defeat look *intentional*. A sloppy, uninspired mess."
        ]

        # Shuffle deck every time to ensure a different quote is selected each time
        # Select the target list and the history list
        target_list = win_quotes if self.p.win else loss_quotes
        history_list = last_win_quotes if self.p.win else last_loss_quotes

        # If the history is empty, refill it and shuffle
        if not history_list:
            history_list.extend(target_list)
            random.shuffle(history_list)

        # Pull the next quote off the "deck"
        selection = history_list.pop(0)

        # Save the updated deck back to the global variable
        if self.p.win:
            last_win_quotes = history_list
        else:
            last_loss_quotes = history_list
        return selection

    def get_all_rules(self) -> list:
        # Order matters, priority cascades from Top to Bottom.
        return (
            self._champion_rules() +
            self._multikill_rules() +
            self._tragedy_rules() +
            self._rival_rules() +
            self._economy_rules() +
            self._role_rules() +
            self._objective_rules() +
            self._item_rules() +
            self._macro_item_rules() +
            self._macro_rules() +
            self._coward_rules() +
            self._anomaly_rules() +
            self._praise_rules() +
            self._mediocre_rules()
        )