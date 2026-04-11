"""
Button and dropdowns like that should be here, so that they can be easily imported and used in cogs and other places.
"""

import discord

from utils.embed_formatter import build_lastgame_embed
from utils.parsers import extract_postgame_stats


# This class handles the button for '/predict'
class PredictView(discord.ui.View):
    def __init__(self, blue_embed: discord.Embed, red_embed: discord.Embed):
        super().__init__(timeout=180)
        self.blue_embed = blue_embed
        self.red_embed = red_embed

    @discord.ui.button(label="Blue Team Draft", style=discord.ButtonStyle.blurple, custom_id="btn_blue")
    async def blue_button(self, interaction: discord.Interaction, _button: discord.ui.Button):
        # Instantly swap the embed to the Blue Team version
        await interaction.response.edit_message(embed=self.blue_embed)

    @discord.ui.button(label="Red Team Draft", style=discord.ButtonStyle.red, custom_id="btn_red")
    async def red_button(self, interaction: discord.Interaction, _button: discord.ui.Button):
        # Instantly swap the embed to the Red Team version
        await interaction.response.edit_message(embed=self.red_embed)

# This class handles the button for '/postgame'
class MatchCycleView(discord.ui.View):
    def __init__(self, riot_client, puuid, server, region, history, current_index, bot_version, full_riot_id):
        super().__init__(timeout=300) # = to 5 minutes of view time
        self.riot = riot_client
        self.puuid = puuid
        self.server = server
        self.region = region
        self.history = history
        self.index = current_index
        self.bot_version = bot_version
        self.full_riot_id = full_riot_id

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Fetch the new match details based on the current index
        match_id = self.history[self.index]
        match_data = await self.riot.get_match_details(match_id, region_override=self.region, server_context=self.server)

        if not match_data:
            await interaction.followup.send("⚠️ Could not fetch details for this match.", ephemeral=True)
            return

        # Parse and build the new embed
        player_stats = extract_postgame_stats(match_data, self.puuid, match_id)
        if not player_stats:
            await interaction.followup.send("⚠️ Error parsing player data for this match.", ephemeral=True)
            return

        embed = build_lastgame_embed(self.server, self.full_riot_id, player_stats, self.bot_version)

        # Update the original message with new embed and the same buttons
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.index < len(self.history) - 1:
            self.index += 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("That's the end of the recorded history!", ephemeral=True)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.send_message("You are already looking at the most recent performance!", ephemeral=True)