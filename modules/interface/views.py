"""
Button and dropdowns like that should be here, so that they can be easily imported and used in cogs and other places.
"""

import discord
from modules.interface.embed_formatter import build_lastgame_embed
from modules.utils.parsers import extract_postgame_stats, quick_resolve_champion

# Unique Logger for this module, with a filter to suppress specific warnings about views being added to messages multiple times


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

# This class handles champion input for '/coach'
class DraftInputModal(discord.ui.Modal):
    def __init__(self, dashboard_view, team_color: str, target_role: str):
        super().__init__(title=f"Add {team_color} {target_role.title()}")
        self.dashboard = dashboard_view
        self.team_color = team_color
        self.target_role = target_role

        self.champ_input = discord.ui.TextInput(
            label="Champion Name (or abbreviation)",
            placeholder="e.g., j4, yi, Volibear, Ashe",
            required=True,
            max_length=20
        )
        self.add_item(self.champ_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        champ_name = quick_resolve_champion(self.champ_input.value, self.dashboard.champ_dict)

        if champ_name not in self.dashboard.champ_dict.values():
            self.dashboard.error_msg = f"'{self.champ_input.value}' is not a valid champion!"
            await self.dashboard.update_dashboard(interaction)
            return

        if champ_name in self.dashboard.blue_dict.values() or champ_name in self.dashboard.red_dict.values():
            self.dashboard.error_msg = f"{champ_name} is already locked in elsewhere!"
            await self.dashboard.update_dashboard(interaction)
            return

        # Direct Injection, It goes exactly where you tell it to go.
        if self.team_color == "Blue":
            self.dashboard.blue_dict[self.target_role] = champ_name
        else:
            self.dashboard.red_dict[self.target_role] = champ_name

        # Clear any previous errors on success
        self.dashboard.error_msg = None
        await self.dashboard.update_dashboard(interaction)

# This class is the draft button for /coach
class DraftButton(discord.ui.Button):
    def __init__(self, team: str, role: str, row: int, dashboard):
        emotes = {"top": "⚔️", "jungle": "🌲", "mid": "🧙", "adc": "🏹", "support": "🛡️"}
        color = discord.ButtonStyle.primary if team == "Blue" else discord.ButtonStyle.danger
        display_label = "ADC" if role == "adc" else role.title()
        super().__init__(label=display_label, emoji=emotes[role], style=color, row=row)
        self.team = team
        self.role = role
        self.dashboard = dashboard

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DraftInputModal(self.dashboard, self.team, self.role))

# This class creates the dashboard for '/coach'
class LiveDraftDashboard(discord.ui.View):
    def __init__(self, ai_system, role: str, user_team: str, role_db: dict, champ_dict: dict):
        super().__init__(timeout=600)
        self.ai = ai_system
        self.role = role.lower()
        self.user_team = user_team.title()
        self.role_db = role_db
        self.champ_dict = champ_dict

        positions = ['top', 'jungle', 'mid', 'adc', 'support']
        self.blue_dict = dict.fromkeys(positions, "Unknown")
        self.red_dict = dict.fromkeys(positions, "Unknown")
        self.error_msg = None

        positions = ['top', 'jungle', 'mid', 'adc', 'support']
        for r in positions:
            btn = DraftButton("Blue", r, 0, self)
            # Lock out the user's specific role slot!
            if self.user_team == "Blue" and self.role == r:
                btn.disabled = True
            self.add_item(btn)

        for r in positions:
            btn = DraftButton("Red", r, 1, self)
            if self.user_team == "Red" and self.role == r:
                btn.disabled = True
            self.add_item(btn)

        # Add Reset button
        reset_btn = discord.ui.Button(label="Reset Draft", style=discord.ButtonStyle.secondary, emoji="↩️", row=2)

        async def reset_callback(interaction):
            self.blue_dict = dict.fromkeys(positions, "Unknown")
            self.red_dict = dict.fromkeys(positions, "Unknown")
            self.error_msg = None
            await interaction.response.defer()
            await self.update_dashboard(interaction)

        reset_btn.callback = reset_callback
        self.add_item(reset_btn)

    async def update_dashboard(self, interaction: discord.Interaction):
        top_picks = self.ai.suggest_champion(self.role, self.user_team, self.blue_dict, self.red_dict, self.role_db)

        # Embed color also reflects error state or team color
        desc = f"Simulating optimal **{self.role.title()}** picks for the **{self.user_team}** side."
        if self.error_msg:
            desc = f"🚨 **ERROR: {self.error_msg}**\n\n" + desc

        if self.error_msg:
            embed_color = discord.Color.red()
        elif self.user_team == "Blue":
            embed_color = discord.Color.blue()
        else:
            embed_color = discord.Color.red()

        embed = discord.Embed(
            title="🧠 Furina's Live Draft Coach",
            description=desc,
            color=embed_color
        )

        if not top_picks:
            embed.add_field(name="⚠️ Standby", value="Waiting for more data to simulate...", inline=False)
        else:
            for rank, (champ, prob) in enumerate(top_picks, 1):
                embed.add_field(name=f"#{rank} - {champ}", value=f"Predicted WR: **{prob * 100:.1f}%**", inline=False)

        # Create display copies so we can inject the "You" tag without corrupting the AI math
        disp_blue = self.blue_dict.copy()
        disp_red = self.red_dict.copy()

        if self.user_team == "Blue":
            disp_blue[self.role] = f"✨ **{interaction.user.display_name}** (You)"
        else:
            disp_red[self.role] = f"✨ **{interaction.user.display_name}** (You)"

        role_emojis = {"top": "⚔️ Top", "jungle": "🌲 Jgl", "mid": "🧙 Mid", "adc": "🏹 ADC", "support": "🛡️ Sup"}
        positions = ['top', 'jungle', 'mid', 'adc', 'support']

        blue_display = [f"{role_emojis[r]}: {disp_blue[r] if disp_blue[r] != 'Unknown' else '---'}" for r in positions]
        red_display = [f"{role_emojis[r]}: {disp_red[r] if disp_red[r] != 'Unknown' else '---'}" for r in positions]

        embed.add_field(name="🟦 Blue Team", value="\n".join(blue_display), inline=True)
        embed.add_field(name="🟥 Red Team", value="\n".join(red_display), inline=True)

        try:
            await interaction.edit_original_response(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            pass