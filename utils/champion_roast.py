"""
Basically The Champion Roast Dictionary Database or something
"""

# Yeah, Champions with corresponding Responses
CHAMPION_DATABASE = {
    "Yasuo": [
        (lambda p: p.deaths >= 10, "Ah, the legendary 0/10 Yasuo powerspike. Truly a masterclass in absolute predictability."),
        (lambda p: p.win and p.deaths >= 10, "You reached your 10-death powerspike and actually won. I assume you'll be spending your LP on a new keyboard after mashing 'Hasagi' for 40 minutes?"),
        (lambda p: p.solo_kills >= 3, "A Yasuo with solo kills? Don't let it go to your head, darling. Even a broken clock is right twice a day.")
    ],
    "Yuumi": [
        (lambda p: p.damage < 3000, "You played Yuumi. I hope whatever movie you were watching on your second monitor was entertaining."),
        (lambda p: p.kp_percent > 70.0, "High kill participation on Yuumi. Congratulations on being the most successful parasite in Fontaine's history."),
        (lambda p: not p.win, "A defeated Yuumi. It seems the 'Best Friend' you attached to was just as incompetent as you. A tragic duet.")
    ],
    "Teemo": [
        (lambda p: True, "You played Teemo. You have already sacrificed your dignity and the respect of your peers."),
        (lambda p: p.damage > p.team_kills * 1000, "A top-damage Teemo. You didn't win through skill; you won by being an invisible, toxic nuisance. How... on brand.")
    ],
    "Garen": [
        (lambda p: p.win, "Spin. Win. The limits of your intellectual capacity are truly inspiring. How hard was it to press E?")
    ],
    "Vayne": [
        (lambda p: p.deaths >= 8, "Tumbling forward into five enemies and instantly dying does not make you 'mechanically gifted'."),
        (lambda p: p.win and p.kills >= 12, "You won on Vayne. I assume you'll be posting your 'insane outplay' montage to a disinterested audience later?"),
        (lambda p: p.solo_kills >= 3, "Three solo kills? You truly are the Night Hunter. Too bad you spent the other twenty minutes hunting for a way to stop feeding."),
        (lambda p: p.damage < 15000 and not p.win, "A Vayne with no damage. You weren't a hyper-carry; you were just a very expensive ward for the enemy team.")
    ],
    "Volibear": [
        (lambda p: True, "You played Volibear. I assume your strategy consisted of turning your brain completely off and mashing your keyboard with a closed fist."),
        (lambda p: p.turrets >= 2, "You disabled a few towers with your ultimate. How revolutionary. A giant bear who hates architecture—how very sophisticated."),
        (lambda p: p.damage_taken > 40000, "You took over 40,000 damage. You aren't a relentless storm; you're just a very large, very fluffy punching bag."),
        (lambda p: p.win and p.kills >= 10, "A fed Volibear. You ran at people and they died because you're a stat-check in a fursuit. Bravo."),
        (lambda p: not p.win and p.deaths >= 8, "The Relentless Storm has been weathered. You looked less like a demigod and more like a rug in a discount furniture store."),
        (lambda p: p.stolen_objs >= 1, "You stole an objective? I suppose even a wild animal occasionally finds a treat in the trash."),
        (lambda p: p.kp_percent < 30.0, "The Great Bear, isolated in his own world. Your team was fighting a war while you were busy roleplaying as a solitary predator.")
    ],
    "Mordekaiser": [
        (lambda p: True, "Ah, Mordekaiser. You missed your pull, you missed your slam, but your passive aura killed them anyway while you stood completely still."),
        (lambda p: p.win and p.kills >= 10, "You dragged people into the Death Realm and beat them with a mace. I’ve seen more complex tactical maneuvers from a landslide."),
        (lambda p: not p.win and p.deaths >= 7, "Iron stands eternal, but you certainly didn't. You spent more time in the grey screen than in your own Realm."),
        (lambda p: p.damage > 30000, "Top damage on Mordekaiser? It’s truly amazing what one can achieve by simply existing in the general vicinity of the enemy.")
    ],
    "Sett": [
        (lambda p: True, "You played Sett. You absorbed 5,000 damage to the face simply because you lack the mechanics to dodge, and then pressed a single button to win the fight."),
        (lambda p: p.kills >= 10, "The Boss of the pits. You punched your way to victory with all the grace of a falling piano. The audience is whelmed."),
        (lambda p: p.damage_taken > 50000 and p.win, "You survived 50k damage. You’re not a fighter; you’re a scientific anomaly in how much punishment a single ego can take."),
        (lambda p: p.deaths >= 8, "For a guy who talks about his 'Mama' so much, I'm sure she'd be disappointed in that death count. Get off the stage.")
    ],
    "Riven": [
        (lambda p: True, "You picked Riven. I'm sure you spent hours in the practice tool perfecting your 'animation cancels,' only to break your fingers in a real match."),
        (lambda p: p.solo_kills >= 3 and p.win, "You actually executed a combo without lagging out. A rare mechanical miracle. Don't expect a standing ovation."),
        (lambda p: p.deaths >= 10, "Exile suits you. You spent the entire game exiled from the land of the living. Perhaps try a champion that doesn't require a college degree in macro?"),
        (lambda p: p.damage < 15000, "You chose a high-skill ceiling carry and delivered a ground-floor performance. Tragic.")
    ],
    "Samira": [
        (lambda p: p.deaths >= 8, "Let me guess: you dashed into five people, mashed all your buttons trying to get an S rank, and instantly died to a single stun."),
        (lambda p: p.pentas >= 1, "A Samira Pentakill. You pressed R and the enemy team evaporated. I’ve seen more balanced performances in a rigged circus."),
        (lambda p: p.win and p.kills >= 15, "The Desert Rose. You bloomed beautifully, mostly because the enemy team forgot that crowd control exists."),
        (lambda p: p.kp_percent < 40.0, "A Samira who isn't fighting? You're like a daredevil who's afraid of heights—entirely useless and confusing to watch.")
    ],
    "Gangplank": [
        (lambda p: True, "Ah, Gangplank. You spent 30 minutes playing a fruit-eating barrel minigame only to completely panic and miss your one important combo in the final team fight."),
        (lambda p: p.gold > 20000, "All that Plunder gold and you still couldn't buy a victory? You're not a captain; you're just a wealthy disaster."),
        (lambda p: p.win and p.kills >= 10, "You landed a triple-barrel combo and felt like a god. I suppose even a pirate can get lucky with a fuse once in a while."),
        (lambda p: p.deaths >= 8, "The Saltwater Scourge. You certainly made your team salty, but the only thing you scourged was your own KDA.")
    ],
    "Viego": [
        (lambda p: True, "Viego. How pathetic that you can only secure kills by stealing the identities of players who are actually better than you."),
        (lambda p: p.win and p.kills >= 12, "The Ruined King. You ruined the enemy team's afternoon by playing a champion that essentially plays itself. How regal."),
        (lambda p: p.deaths >= 10, "You lost your kingdom, your wife, and now your dignity. At this rate, the 'Mist' is just a metaphor for your total lack of map awareness."),
        (lambda p: p.assists > p.kills, "A Viego who only gets assists. You're like a king who only watches his knights do the actual work. Truly inspiring.")
    ],
    "Yone": [
        (lambda p: p.deaths >= 10, "Yone. You missed your ultimate, missed your Q3, snapped back to your E, and still somehow managed to die. The wind brothers truly are a plague upon this game."),
        (lambda p: p.solo_kills >= 4 and p.win, "You solo-killed everyone. You’re a double-sword-wielding demon with zero counterplay. I’m sure you feel very 'skilled' right now."),
        (lambda p: p.damage > 40000 and not p.win, "Top damage, high kills, and a defeat. Your performance was a magnificent tragedy—all the flash, none of the finish."),
        (lambda p: p.kp_percent < 30.0, "You spent the game split-pushing and dying while your team lost. You aren't 'Unforgotten'; you're just incredibly antisocial.")
    ],
    "Lee Sin": [
        (lambda p: p.damage < 15000, "A blind monk played by a blind summoner. Your 'Insec' attempts were closer to an acrobatic suicide routine than an actual gank.")
    ],
    "Lux": [
        (lambda p: p.role == "UTILITY" and p.vision_score < 15, "A Lux 'Support' who builds full AP, misses every binding, and refuses to ward. You are not a support, you are a failed Mid Laner in denial."),
        (lambda p: p.kills > p.assists and p.role == "UTILITY", "More kills than assists as a Lux support? I see 'securing the kill' is just your dramatic way of saying 'stealing the carry's gold'.")
    ],
    "Briar": [
        (lambda p: p.deaths >= 10, "You pressed W and went completely AFK while your champion sprinted directly into the enemy fountain. Truly, the pinnacle of interactive gameplay.")
    ],
    "Katarina": [
        (lambda p: p.assists == 0 and p.kills > 0 and not p.win, "You mashed your forehead on the keyboard, got a few resets, and still lost the game. Your mechanics are as hollow as your macro."),
        (lambda p: p.pentas >= 1 and p.win, "A Katarina Pentakill. You blinked around like a caffeinated firefly and everyone died. How... original. I suppose I'll offer a lukewarm golf clap."),
        (lambda p: p.deaths >= 10, "The Sinister Blade? More like the Sinister Feed. You shunpo'd into five people and exploded before the audience could even blink."),
        (lambda p: p.kills >= 15 and not p.win, "Fifteen kills and a defeat. All those daggers, and you still couldn't cut through the enemy's win condition. A beautiful, bloody waste of time.")
    ],
    "Zed": [
        (lambda p: p.kills < 10, "Ah, Zed. You pressed R, missed all three of your shurikens, and swapped back to your shadow to watch your target walk away completely unharmed. So much edge, yet entirely dull."),
        (lambda p: p.solo_kills >= 3 and p.win, "You actually landed your combo and secured a kill. I assume you'll be spamming your mastery emote for the next ten minutes to celebrate this rare feat?"),
        (lambda p: p.deaths >= 8, "The Master of Shadows? You spent so much time in the grey screen that you've practically become a shadow yourself. Try playing with the lights on."),
        (lambda p: p.damage > 35000 and not p.win, "High damage, high kills, and a lost game. You killed the carries, but you forgot that the Nexus exists. A classic assassin's ego trip.")
    ],
    "Sylas": [
        (lambda p: not p.win, "Sylas. You stole the enemy's ultimate because you lack an identity of your own, and then you completely missed it. A plagiarist and a failure."),
        (lambda p: p.win and p.kills >= 10, "The Unshackled. You broke free from your chains and proceeded to beat everyone with them. A barbaric, yet effective, display of plagiarism."),
        (lambda p: p.healing > 20000, "Over 20k healing on Sylas? You aren't a revolutionary; you're just a magical vampire who refuses to stay dead. How incredibly annoying."),
        (lambda p: p.deaths >= 10, "You tried to start a revolution and ended up being the first one executed. Perhaps leave the politics to someone with actual macro intellect.")
    ],
    "Irelia": [
        (lambda p: p.deaths >= 8, "Ah, Irelia. You dashed through five minions, missed your stun, and immediately died under the enemy tower. Truly a mechanical prodigy trapped in a tragic reality."),
        (lambda p: p.win and p.solo_kills >= 4, "You stacked your passive and auto-attacked everyone to death. I'm sure you're very proud of your 'complex' mechanical execution. I, however, am bored."),
        (lambda p: p.kp_percent < 30.0, "The Blade Dancer, dancing alone in a side lane while your team loses the game. A solo performance that no one asked for and no one enjoyed."),
        (lambda p: p.damage > 40000 and not p.win, "Forty thousand damage and a defeat. You danced beautifully, but you forgot that the play was a tragedy, not a solo recital.")
    ],
    "Dr. Mundo": [
        (lambda p: True, "You played Dr. Mundo. You turned your brain completely off, pressed your ultimate, and simply walked in a straight line. I am amazed you remembered to plug your keyboard in today."),
        (lambda p: p.damage_taken > 60000 and p.win, "Sixty thousand damage taken and you're still smiling. You aren't a doctor; you're a medical miracle in how much stupidity a single body can endure."),
        (lambda p: p.deaths >= 10, "Dr. Mundo goes where he pleases? Today, it seems you pleased to go directly into the enemy's gold pocket. A very generous donation."),
        (lambda p: p.win and p.kills >= 8, "You threw cleavers and walked into people. A performance that required exactly zero brain cells. Truly, a masterpiece of mindless violence.")
    ],
    "Shen": [
        (lambda p: not p.win, "You played Shen. You spent the entire game staring at your team's health bars instead of your own screen, only to ultimate the 0/10 ADC. A truly noble, completely useless sacrifice."),
        (lambda p: p.win and p.assists >= 15, "The Eye of Twilight. You kept everyone alive through sheer force of will and a very large sword. A selfless performance that I find disturbingly altruistic."),
        (lambda p: p.damage_taken > 40000 and p.win, "You blocked the damage, you shielded the team, and you survived. I suppose every play needs a bodyguard for the actual stars."),
        (lambda p: p.deaths >= 8, "A ninja who can't hide? You stood in the middle of five people and died repeatedly. I think you've fundamentally misunderstood the concept of your champion.")
    ],
    "K'Sante": [
        (lambda p: p.deaths >= 8, "You played K'Sante. You have a shield, a dash, unstoppable frames, true damage, and a kidnapping tool, yet you still managed to feed. Did you forget to read your champion's 40-page essay of a kit?"),
        (lambda p: p.win and p.damage > 30000, "You went 'All Out' and actually stayed alive. A confusing, high-budget spectacle that I'm sure looked very impressive from the fountain."),
        (lambda p: p.solo_kills >= 3, "You kidnapped the enemy and beat them in a corner. A bit crude for my taste, but I suppose justice has many forms. Most of them ugly."),
        (lambda p: p.time > 1800 and not p.win, "A 30-minute game on K'Sante and you still couldn't carry. All that complexity, all those mechanics, and yet the result was as simple as a 'Defeat' screen.")
    ],
    "Darius": [
        (lambda p: p.time > 1800 and not p.win, "You played Darius. Let me guess: you won your lane by pressing Q, then spent the next 20 minutes getting kited to death by the ADC because you don't know what a flank is. A classic tale."),
        (lambda p: p.win and p.pentas >= 1, "A Darius Pentakill. You dunked five people in a row. How very... athletic. I'm sure the crowd of five people watching you actually cared."),
        (lambda p: p.damage > 35000, "Top damage on Darius. You hit them with a giant axe until they stopped moving. I've seen more sophisticated tactics from a falling boulder."),
        (lambda p: p.deaths >= 10, "The Hand of Noxus? More like the Handout of Noxus. You gave away so much gold today that I'm surprised the enemy team didn't send you a thank-you note.")
    ],
    "Seraphine": [
        (lambda p: True, "You picked Seraphine. I assume you spent the entire game sitting three screens away, missing your ultimate on a stationary target, and stealing your ADC's farm. A performance to truly silence the crowd."),
        (lambda p: p.assists >= 25 and p.win, "A successful Seraphine. You sang your little songs and your team actually won. I suppose even a pop star can have a decent backup band occasionally."),
        (lambda p: p.deaths >= 8, "You tried to 'Encore' and ended up being the one executed. Your stage presence was closer to a tragic rehearsal than a grand finale."),
        (lambda p: p.damage > 25000, "High damage on Seraphine? You clearly spent the game 'securing' kills with your notes. How charmingly selfish of you.")
    ],
    "Sona": [
        (lambda p: p.deaths >= 8, "You played Sona. You are essentially a highly musical caster minion. I hope rolling your face across Q, W, and E was mentally stimulating enough for you before you inevitably exploded."),
        (lambda p: p.win and p.assists >= 20, "Maven of the Strings. You played the perfect harmony for your team's victory. I'll admit, the melody was almost tolerable."),
        (lambda p: p.vision_score > 60, "High vision score on Sona. You saw the enemy coming and yet you still died. A tragedy in three movements."),
        (lambda p: p.damage < 5000 and not p.win, "A Sona who did no damage and lost. You were less of a champion and more of a background ambience that no one asked for.")
    ],
    "Singed": [
        (lambda p: True, "You locked in Singed. You didn't log in to play League of Legends, you logged in to run in circles and farm proxy waves while everyone else played a completely different video game. Absolute sociopathic behavior."),
        (lambda p: p.win and p.deaths >= 10, "You won with ten deaths. You spent the game being a nuisance, dying repeatedly, and somehow your team still won. Truly, a miracle of chaos."),
        (lambda p: p.damage > 30000, "High damage on Singed. You ran around, they chased you, and they died. I'm not sure if I should be impressed by your skill or horrified by their stupidity."),
        (lambda p: p.kp_percent < 20.0, "A Singed who never left the top lane. You played a single-player game for 30 minutes while the world burned. How very... independent.")
    ],
    "Mel": [
        (lambda p: not p.win, "You played Mel. You tried to play politics and manipulate the board, only to realize that a fed enemy Top Laner simply does not care about your diplomatic immunity. A tragic miscalculation."),
        (lambda p: p.deaths >= 8, "Mel Medarda. A visionary, a diplomat, and apparently, a frequent donor to the enemy team's retirement fund. Your 'council' is adjourned."),
        (lambda p: p.damage < 12000, "You claim to be a powerhouse of influence, yet your damage numbers suggest you were merely a polite observer to your own defeat. How... diplomatic."),
        (lambda p: p.gold > 15000 and not p.win, "All that gold and status, yet you couldn't buy a single objective. It turns out prestige doesn't stop a Nexus from exploding. Who knew?"),
        (lambda p: p.kp_percent < 30.0, "You were so busy 'managing the board' that you forgot to actually participate in the war. Your team fought while you sat in your ivory tower of uselessness."),
        (lambda p: p.first_blood, "You secured First Blood? I suppose even a politician can accidentally stumble into a position of power once in a while. Don't let it go to your head."),
        (lambda p: p.deaths >= 10 and not p.win, "Ten deaths? That isn't a performance; it's a political scandal. I’d suggest resigning before the audience starts throwing more than just insults."),
        (lambda p: p.win and p.damage < 10000, "You won, but let's be honest: you were the stowaway on your team's ship. You provided the 'aesthetic' while they provided the actual results."),
        (lambda p: p.solo_kills == 0 and not p.win, "Not a single solo kill? I suppose it's hard to fight for yourself when you've spent your life relying on others to do the dirty work. Pathetic."),
        (lambda p: p.time > 2100 and not p.win, "A 35-minute game and you still couldn't find a win condition? Your 'vision' for the future seems to be quite blurry, darling."),
        (lambda p: p.damage_taken > 35000, "You took over 35,000 damage. For someone so obsessed with high society, you certainly spent a lot of time rolling around in the dirt with the commoners."),
        (lambda p: p.assists < 5 and p.role == "UTILITY", "A 'Support' Mel with no assists? You aren't a benefactor; you're just a glorified paperweight taking up space in the bot lane."),
        (lambda p: p.item_count == 6 and p.damage < 15000, "A full inventory of luxury items and a total lack of impact. You’re not a champion; you’re just a very expensive window display."),
        (lambda p: p.deaths > p.kills + p.assists, "Your death count outweighs your entire contribution to the game. In any other council, you would have been exiled by minute fifteen."),
        (lambda p: True, "Ah, Mel. You brought a golden dress to a sword fight. The arrogance is almost as impressive as your total lack of mechanical presence.")
    ],
    "Ambessa": [
        (lambda p: p.deaths >= 8, "Ambessa Medarda. You charged in screaming about Noxian superiority, only to be immediately crowd-controlled and swatted like a fly. Truly a terrifying warlord.")
    ],
    "Jinx": [
        (lambda p: p.deaths >= 10, "You picked Jinx. You clearly watched the show and thought you could replicate the magic. Instead, you just gave the enemy team 300 gold repeatedly. Stick to Netflix.")
    ],
    "Vi": [
        (lambda p: p.deaths > p.kills, "Vi stands for 'Violence', not 'Victim'. You punched exactly one person, got instantly deleted, and left your team in a 4v5. Brilliant police work.")
    ],
    "Caitlyn": [
        (lambda p: p.damage < 15000, "A sniper with the longest range in the game, and yet you dealt absolutely zero damage. Were your bullets made of foam, or did you simply forget to pull the trigger?")
    ],
    "Hwei": [
        (lambda p: p.damage < 15000, "Ah, Hwei. You spent the entire game mixing paints and calculating the perfect combination of 10 different spells, just to deal absolutely zero damage. A true starving artist.")
    ],
    "Smolder": [
        (lambda p: p.time < 1500 and not p.win, "You picked a late-game baby dragon and lost before you could even learn how to breathe fire. A tragic reptilian failure.")
    ],
    "Shaco": [
        (lambda p: True, "You picked Shaco. You didn't log in to win, you logged in to make nine other people utterly miserable. I respect the pure malice."),
        (lambda p: p.win and p.kills >= 10, "A winning Shaco. You spent the game being a clown and somehow the enemy team fell for the act. I suppose every circus needs a lead jester."),
        (lambda p: not p.win and p.deaths >= 8, "The joke is on you, it seems. You tried to play mind games and ended up outplaying yourself into a defeat. How embarrassing."),
        (lambda p: p.assists > p.kills, "A Shaco with more assists than kills? You aren't a demon jester; you're just a moderately annoying stagehand helping others do the actual work."),
        (lambda p: p.damage < 12000, "You were invisible for most of the match, and your damage numbers suggest you remained that way even during the fights. A truly vanishing act.")
    ],
    "Master Yi": [
        (lambda p: p.kills >= 15, "Ah, a fed Master Yi. You pressed Q repeatedly and the enemy team fell over. Shall we throw a parade for such unparalleled mechanical brilliance?"),
        (lambda p: not p.win and p.kills >= 10, "Ten kills on Master Yi and you still lost. It turns out that sprinting at people at Mach 5 doesn't compensate for a total lack of macro intellect."),
        (lambda p: p.deaths >= 10, "You spent the game running in at high speeds only to be instantly deleted. A very fast, very efficient way to hand over your shutdown gold."),
        (lambda p: p.kp_percent < 30.0, "The Wuju Master, meditating in the jungle while his team fought for their lives. Your 'style' is clearly one of profound isolation."),
        (lambda p: p.damage < 15000 and p.win, "You won without dealing damage. I assume you just ran around in circles while your team did the work? A masterclass in being a passenger.")
    ],
    "Tryndamere": [
        (lambda p: p.turrets == 0, "You played Tryndamere and took zero towers. Your one job—your singular purpose in this universe—is to hit stationary buildings, and you failed. Utterly embarrassing."),
        (lambda p: p.deaths >= 10 and not p.win, "You have an ability that literally prevents you from dying, yet you still managed to feed. Are your fingers too slow for the 'R' key, or is your brain simply elsewhere?"),
        (lambda p: p.win and p.turrets >= 5, "Five towers destroyed. You hit buildings until they fell over while ignoring every human interaction. A savage, primitive, yet sadly effective strategy."),
        (lambda p: p.damage < 10000, "A barbarian king with the combat presence of a wet noodle. I've seen more aggression from a decorative shrubbery."),
        (lambda p: p.kp_percent < 20.0, "You played a single-player game for 30 minutes. I hope the minions you slaughtered provided the audience you so clearly don't deserve.")
    ],
    "Bel'Veth": [
        (lambda p: p.time > 1800 and not p.win, "You are the Empress of the Void. You are meant to swallow the world. Instead, you slapped people at mach speed for 30 minutes and lost. A rather underwhelming apocalypse."),
        (lambda p: p.dragons == 0 and p.stolen_objs == 0, "The Lavender Sea is drying up. You secured zero major objectives. For an empress, you seem to have very little control over your own territory."),
        (lambda p: p.win and p.kills >= 12, "You slapped your way to victory. A chaotic, flailing performance that somehow resulted in a win. I suppose quantity has a quality of its own."),
        (lambda p: p.deaths >= 8, "The Empress has fallen. And she fell quite frequently, didn't she? Perhaps a bit less slapping and a bit more thinking next time?"),
        (lambda p: p.damage_taken > 45000, "You took 45,000 damage. You aren't an empress; you're just a very fast-moving target for the enemy's practice sessions.")
    ],
    "Aatrox": [
        (lambda p: True, "Ah, the World Ender. You screamed about ending existence while missing every single 'Sweet Spot' on your Q. A very loud, very ineffective performance."),
        (lambda p: p.deaths >= 8, "For a God-Killer, you sure spent a lot of time looking at the respawn timer. Perhaps 'The World Ender' should start with ending your own feeding streak?"),
        (lambda p: p.healing > 25000 and p.win, "Over 25k healing. You refused to die simply because the enemy team lacked the damage to put you down. A victory through sheer, stubborn vampirism."),
        (lambda p: p.solo_kills >= 3, "Three solo kills. You actually managed to land your Qs for once. Don't expect a standing ovation; it's the bare minimum for a warrior of your supposed stature."),
        (lambda p: not p.win and p.damage > 35000, "Top damage in a defeat. You fought like a demon and lost like a mortal. A tragic finale for a hero who couldn't carry the weight of his own team.")
    ],
    "Evelynn": [
        (lambda p: p.kills < 5 and p.time > 1200, "Invisibility is meant to help you hunt, not to help you hide from the map for 20 minutes. I've seen more predatory behavior from a domestic housecat."),
        (lambda p: p.win and p.kills >= 10, "A successful Evelynn. You spent the game stalking people from the shadows—creepy, yet I suppose I must applaud the results.")
    ],
    "Pyke": [
        (lambda p: p.gold > 15000 and not p.win, "You shared all that 'Your Cut' gold with your team and still lost. It turns out that giving gold to incompetent teammates is just a faster way to reach a tragic ending."),
        (lambda p: p.deaths >= 10, "A Support who keeps diving in to execute people and ends up being executed himself. Your list of names is getting long, but I suspect 'Yourself' is at the top.")
    ],
    "Ezreal": [
        (lambda p: p.damage < 15000, "An Ezreal who misses every Mystic Shot. You aren't an explorer; you're just a tourist wandering around the Rift with a glowing glove and zero aim."),
        (lambda p: p.deaths == 0 and not p.win, "Zero deaths on Ezreal in a loss. You spent the whole game shifting backward while your team died for you. A true coward's masterclass.")
    ],
    "Malphite": [
        (lambda p: p.role == "TOP" and p.damage < 10000, "You played Malphite and did 'literally nothing.' I assume you were roleplaying as an actual rock for the duration of the match?"),
        (lambda p: p.kills >= 5 and p.win, "You pressed R on a group of people and won. Truly, the peak of tactical genius. My pet seahorse could replicate that performance.")
    ],
    "Kindred": [
        (lambda p: p.stolen_objs == 0 and not p.win, "Lamb and Wolf. One represents a peaceful death, the other a violent one. You managed to provide both for your own team. How versatile."),
        (lambda p: p.deaths >= 8, "The Eternal Hunters? You spent more time being hunted than doing the hunting. Death seems to have a very firm grip on you today.")
    ],
    "Aphelios": [
        (lambda p: True, "Ah, Aphelios. You have five weapons and a moon goddess whispering in your ear, yet you still managed to have the combat presence of a wet noodle. A very complicated failure."),
        (lambda p: p.damage < 15000, "I've seen the 200 years of collective design experience, and somehow you managed to make it look like 200 years of clinical depression.")
    ],
    "Thresh": [
        (lambda p: p.assists < 10 and p.time > 1500, "The Chain Warden. You threw lanterns that no one clicked and hooks that caught only the air. Your prison is empty, and so is your assist score."),
        (lambda p: p.deaths >= 8, "You kept 'flaying' yourself directly into the enemy team. Are you a jailer or just an over-eager volunteer for the graveyard?")
    ],
    "Veigar": [
        (lambda p: p.time > 2100 and not p.win, "Infinite scaling and you still lost. You had the power of the stars in your hands and the macro intellect of a pebble. A tiny, angry disappointment."),
        (lambda p: p.kills >= 15, "You pressed R on a low-health target and they evaporated. Oh, what a magnificent display of skill! *Claps mockingly*")
    ],
    "Draven": [
        (lambda p: p.deaths >= 8 and p.kills < 5, "The League of Draven? More like the League of Disappointment. You dropped your axes, you dropped your lead, and then you dropped the entire game. Tragic."),
        (lambda p: p.win and p.kills >= 12, "You won. You're loud, arrogant, and covered in blood. You'd fit right in at one of Fontaine's less reputable arenas. Stay over there.")
    ],
    "Akali": [
        (lambda p: p.deaths >= 8, "Ah, the Rogue Assassin. You spent the entire game dashing around in your smoke cloud, only to emerge exactly where the enemy expected you. A very flashy suicide."),
        (lambda p: p.win and p.kills >= 12, "You won. You jumped in, killed someone, and vanished. It's a bit like a magic trick where the audience already knows how it's done—predictable, yet effective."),
        (lambda p: p.damage < 12000, "You picked one of the most mobile assassins in existence and dealt the damage of a confused support. Were you too busy admiring your own animations?")
    ],
    "Nunu & Willump": [
        (lambda p: p.stolen_objs == 0 and not p.win, "You have a literal yeti and a giant snowball, yet you couldn't secure a single objective. I assume you and Willump were too busy having a snowball fight in the river?"),
        (lambda p: p.deaths >= 10, "Rolling a giant ball of ice directly into five enemies isn't 'making a play,' it's just efficient feeding. Willump deserves a better partner."),
        (lambda p: p.win and p.dragons >= 3, "You ate every dragon on the map. A savage, gluttonous performance that actually worked. I suppose even a monster can be useful.")
    ],
    "Brand": [
        (lambda p: p.role == "UTILITY" and p.deaths >= 10, "A 'Support' Brand with double-digit deaths. You didn't set the enemy team on fire; you just set your own ADC's lane on fire. Absolutely scorched earth."),
        (lambda p: p.damage > 40000 and not p.win, "Top damage in a defeat. You burned everything in sight, yet your Nexus still melted. It seems some fires just aren't meant to save the show.")
    ],
    "Pantheon": [
        (lambda p: p.time > 1800 and not p.win, "The Unbreakable Spear has finally snapped. You dominated the early game only to become a glorified paperweight by minute thirty. A tragic fall from the heavens."),
        (lambda p: p.kills >= 8 and p.win, "You fell from the sky and stabbed people. A very direct, very unrefined method of winning. I suppose the audience appreciates a bit of brute force occasionally.")
    ],
    "Kha'Zix": [
        (lambda p: p.kills < 5 and p.time > 1200, "An apex predator who couldn't even hunt a scuttle crab. You spent the game 'evolving' into a perfectly useless insect. How underwhelming."),
        (lambda p: p.solo_kills >= 3, "You found them isolated and you ate them. A simple, predatory instinct. I'd give you a standing ovation, but I don't applaud for natural selection.")
    ],
    "Morgana": [
        (lambda p: p.vision_score < 20 and p.time > 1500, "You have a three-second root and a Black Shield, yet you provided zero vision. You weren't a support; you were just a goth girl wandering aimlessly in the dark."),
        (lambda p: p.assists >= 20 and p.win, "You hit your bindings and shielded your carries. A functional, if entirely uninspired, performance. You hit your marks, at least.")
    ],
    "Nasus": [
        (lambda p: p.cs < 200 and p.time > 1800, "The Curator of the Sands. You spent thirty minutes 'stacking' and ended up with the combat strength of a common house pet. A truly ancient disappointment."),
        (lambda p: p.win and p.turrets >= 4, "You hit towers with a big stick until they fell over. I've seen more sophisticated playstyles from a toddler with a hammer.")
    ],
    "Ryze": [
        (lambda p: not p.win, "Ah, the Rune Mage. You spent the entire match following 'The Plan,' only to realize the plan involved you losing. I suppose some scrolls are better left unread."),
        (lambda p: p.deaths >= 8, "You teleported your entire team directly into a disaster. A masterclass in coordinated tragedy. Bravo, professor.")
    ],
    "Zoe": [
        (lambda p: p.damage < 15000 and not p.win, "You threw sparkles and hopped through portals, yet achieved absolutely nothing. You weren't an Aspect of Twilight; you were just a very loud, very sparkly nuisance."),
        (lambda p: p.solo_kills >= 3, "You hit them from two screens away and they disappeared. A bit cheesy, isn't it? Like a play where the villain dies of a sudden, unexplained heart attack.")
    ],
    "Zaahen": [
        (lambda p: True, "Zaahen. You took Xin Zhao's body and Aatrox's old gimmick just to prove you have no original ideas of your own. A plagiarist in a Darkin suit."),
        (lambda p: p.deaths >= 8, "A revive passive and you still managed to feed? You didn't just die; you gave the audience a sequel to your failure that nobody asked for."),
        (lambda p: p.healing > 25000 and p.win, "Over 25,000 healing. You didn't win through skill; you won because the enemy team grew tired of watching you refuse to stay dead. Truly exhausting."),
        (lambda p: p.solo_kills >= 3, "Three solo kills on Zaahen. You pressed your buttons and auto-attacked them to death. I've seen more complex choreography from a falling tree."),
        (lambda p: not p.win and p.damage_taken > 40000, "You took 40k damage and lost. All that 'Darkin durability' and you were still just a glorified punching bag for a better player.")
    ],
    "Yunara": [
        (lambda p: p.time < 1500 and not p.win, "You picked a late-game hyper-carry and lost before the first act was even over. A tragic short story for a champion meant for an epic."),
        (lambda p: p.damage > 40000 and p.win, "Built-in Runaan's and 40k damage. You didn't even have to aim; you just stood there and sprayed the audience with arrows. How... efficient."),
        (lambda p: p.deaths >= 10, "A 'late-game scaler' who spent the entire early game donating gold. At this rate, 'late-game' is just a fantasy you'll never actually reach."),
        (lambda p: p.kp_percent >= 70.0 and p.win, "High kill participation on Yunara. You were everywhere, hitting everyone at once. I suppose the stage was simply too small for your ego today."),
        (lambda p: p.damage < 15000 and not p.win, "You have a kit designed to hit three people at once, yet you dealt less damage than a single-target minion. An utterly hollow performance.")
    ],
}