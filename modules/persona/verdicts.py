"""
A sole helper function to generate a post-game review verdict for Furina, the Roast Bot.
This function takes in a dictionary of match statistics and uses the RoastGenerator to apply all relevant roasts based on the player's performance.
If no specific roasts apply, it provides a generic verdict based on whether the player won or lost.
The function also handles cases where the combined roast exceeds Discord's embed character limit by adding a humorous suffix.
"""

import random
from modules.persona.roasts import RoastGenerator

# Verdicts for post game review
def generate_furina_verdict(stats: dict) -> str:
    # Initialize the Roast Engine
    engine = RoastGenerator(stats)

    # Collect all matches instead of stopping at the first one
    applied_roasts = []
    for condition, verdict in engine.get_all_rules():
        if condition():
            applied_roasts.append(verdict)

    # If no condition met get the generic win and loss verdicts
    if not applied_roasts:
        return engine.get_fallback_quote()

    # (The [:1024] protects the bot from crashing Discord's embed character limit)
    combo_roast = " ".join(applied_roasts)
    if len(combo_roast) > 1024:
        suffixes = [
            "... And so much more. Truly a performance for the ages.",
            "... The list goes on, but I am simply too exhausted to continue.",
            "... I could keep going, but frankly, you are not worth my breath.",
            "... A tragedy so long, Discord physically will not let me finish it.",
            "... And that is only half of it. Please, log off and reflect on your choices.",
            "... I have run out of breath. Just uninstall the game.",
            "... I would list the rest of your blunders, but the audience is already leaving. What an absolute farce.",
            "... The Oratrice Mecanique d'Analyse Cardinale has quite literally overheated trying to process the sheer volume of your crimes. I rest my case.",
            "... To recount the entirety of this tragedy would take a full theatrical season. Let us just draw the curtains and pretend this never happened."
        ]

        # Choose a random suffix to add some variety to the bot's responses when the roast is too long
        chose_suffix = random.choice(suffixes)

        # Calculate how many characters we have left for the roast after adding the suffix
        safe_cut = 1020 - len(chose_suffix)
        raw_cut = combo_roast[:safe_cut]

        # Walk backward to the last space so we don't chop a word in half!
        clean_cut = raw_cut.rsplit(' ', 1)[0]

        return clean_cut + chose_suffix

    return combo_roast

# The verdict templates for the trial command, with placeholders for defendant and user mentions. .
GUILTY_TEMPLATES = [
    "**GUILTY!** {defendant}, your mechanical incompetence is an insult to the stage! {user} is absolved of all blame.",
    "**CONVICTED!** The evidence is overwhelming. {defendant} was playing with their eyes closed! {user} is the true victim here.",
    "**SENTENCED!** {defendant}, your 'gameplay' is a comedy of errors. The Oratrice rules in favor of {user}!",
    "**VERDICT: ATROCIOUS!** {defendant}, I've seen more coordination from a newborn hilichurl. {user} is innocent!",
    "**EXPOSED!** {defendant}, your 'tactical' decisions are nothing more than a series of unfortunate events. The Oratrice rules in favor of {user}!",
    "**CLOWN FIASCO!** {defendant}, I’ve seen better positioning from a target dummy. Your presence on the Rift is a tragedy, and {user} is the only hero here.",
    "**BEYOND REDEMPTION!** {defendant}, you didn't just throw the game; you launched it into orbit! The court finds you guilty of high treason against the LP of {user}.",
    "**CASE CLOSED!** {defendant}, your inability to land a single skillshot has reached legendary levels of failure. {user} is officially acquitted!"
]

PLOT_TWIST_TEMPLATES = [
    "**PLOT TWIST!** {user}, you dare accuse them when your own macro is this tragic? The Oratrice finds YOU guilty of throwing!",
    "**REVERSAL!** Upon further inspection, {user} was the one running it down all along! {defendant} is innocent!",
    "**FALSE ACCUSATION!** {user}, attempting to deflect blame only highlights your own failures. The Oratrice sentences YOU!",
    "**THE AUDACITY!** {user}, you brought this case to my court while your own KDA is a literal disaster? You are the one who is guilty!",
    "**REVERSAL OF FATE!** {user}, you claim {defendant} was the problem, yet you were the one hiding in the fountain during every team fight! GUILTY!",
    "**IRONY AT ITS FINEST!** {user}, pointing fingers won't hide your 15% kill participation. The Oratrice finds YOU responsible for this theatrical disaster!",
    "**PERJURY!** {user}, you attempted to frame {defendant} for your own mechanical collapse. For this deception, the court sentences YOU to the bronze abyss!",
    "**THE FINAL BLUFF!** {user}, did you think I wouldn't notice your damage chart? You dealt less than the support! The Oratrice finds the accuser guilty!"
]

MERCY_TEMPLATES = [
    "**FORGIVEN!** The Oratrice senses true remorse for your '{crime}'. Your LP will be spared.",
    "**ABSOLVED!** A momentary lapse in judgment like '{crime}' does not define a star.",
    "**CLEANSED!** Your honesty is refreshing. I shall personally see to it that your next teammates have actual human souls.",
    "**MERCY GRANTED!** Even the grandest stage has its blunders. You are free to return to the Rift, hopefully with more poise.",
    "**EXCUSED!** The Oratrice finds your crime... understandable. Barely. Take your acquittal and leave before I change my mind.",
    "**REPRIEVED!** Justice is not always cold. Today, you receive the blessing of the court. Do not waste it on a missed Smite.",
    "**GRACE BESTOWED!** A rare display of humility. I find your confession sufficient to offset your tragic mechanical failure.",
    "**NOT GUILTY!** While your play was an eyesore, your soul remains intact. The court dismisses these charges."
]

SENTENCE_TEMPLATES = [
    "**UNFORGIVABLE!** A confession does not erase a tragedy! The Oratrice sentences you to 5 games of Loser's Queue.",
    "**CONDEMNED!** You admit to such a crime and expect mercy? Your next 3 promos shall be populated entirely by inters!",
    "**GUILTY!** Honesty is noble, but your gameplay was a crime against humanity. The court sentences you to the Bronze Abyss.",
    "**NO MERCY!** I am a judge, not a saint! For that atrocious misplay, you shall suffer a 20-game winless streak.",
    "**EXECUTION!** (Of your LP, that is). Your confession only highlights how truly horrific your macro has become!",
    "**BANISHED!** Leave my sight! The Oratrice finds your sincerity lacking and your skillshots even worse.",
    "**SENTENCED!** You shall be forced to play with a 0/10 Yasuo main for the remainder of the evening. Court adjourned!",
    "**TRAGIC!** Your confession is as messy as your kiting. The Oratrice orders a permanent demotion to the depths of Iron."
]