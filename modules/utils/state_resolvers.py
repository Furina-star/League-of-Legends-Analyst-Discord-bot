"""
The Brain. It sits between the two.
It takes data from the database, compares it against the user's input, applies your specific "rules" (like anti-fraud or name change detection), and returns a final decision.
"""

# Determines the correct message and whether to abort the link process.
def resolve_link_state(db, user_id: int, new_puuid: str, new_riot_id: str) -> tuple[bool, str]:
    current_link = db.get_linked_account(user_id)

    # First Time Linking
    if not current_link:
        return False, f"✅ Successfully linked **{new_riot_id}** to your Discord account. You are now eligible for the Hall of Shame."
    old_riot_id, old_puuid = current_link

    # Swapping to a completely new account
    if old_puuid != new_puuid:
        # self.db.clear_user_logs(user_id) # Uncomment this for clear deletion of record.
        return False, f"🔄 Successfully updated your linked account from **{old_riot_id}** to **{new_riot_id}**."

    # Exact same account, exact same name
    if old_riot_id == new_riot_id:
        return True, f"⚠️ You are already linked to **{new_riot_id}**!"

    # Same account, but they changed their Riot ID name
    return False, f"🔄 Detected a name change! The Oratrice has updated your profile from **{old_riot_id}** to **{new_riot_id}**."

# Match Eligibility resolver
def resolve_match_eligibility(game_duration: int, queue_id: int) -> tuple[bool, str]:
    # The Remake Check (Games under 4 minutes / 240 seconds)
    if game_duration < 240:
        return False, "This match was a remake. The Oratrice ignores games that end before they truly begin."

    # We only want Summoner's Rift PvP matches.
    valid_queues = {400, 420, 430, 440, 490}
    if queue_id not in valid_queues:
        return False, "The Hall of Shame only accepts Summoner's Rift PvP matches. Rotating modes and ARAMs are exempt from judgment."

    return True, "Match is eligible."