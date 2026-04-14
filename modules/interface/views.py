"""
Button and dropdowns like that should be here, so that they can be easily imported and used in cogs and other places.
"""

import discord
from modules.interface.embed_formatter import build_lastgame_embed, build_draft_embed
from modules.utils.parsers import extract_postgame_stats, quick_resolve_champion
from modules.interface.canvas_engine import render_draft_board

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

        # If the champion is a valid character in League of Legends
        if champ_name not in self.dashboard.champ_dict.values():
            self.dashboard.error_msg = f"'{self.champ_input.value}' is not a valid champion!"
            await self.dashboard.update_dashboard(interaction)
            return

        # If the champion is already locked in the draft pick
        if champ_name in self.dashboard.blue_dict.values() or champ_name in self.dashboard.red_dict.values():
            self.dashboard.error_msg = f"{champ_name} is already locked in elsewhere!"
            await self.dashboard.update_dashboard(interaction)
            return

        # If the champion is banned
        if champ_name in self.dashboard.banned_champs:
            self.dashboard.error_msg = f"{champ_name} is banned and cannot be drafted!"
            await self.dashboard.update_dashboard(interaction)
            return

        self.dashboard.save_state() # Take a snapshot before modifying!

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
        self.history = []
        self.banned_champs = []
        self.last_ban_input = ""

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

        # Add Undo button
        undo_btn = discord.ui.Button(label="Undo", style=discord.ButtonStyle.secondary, emoji="⏪", row=2)

        async def undo_callback(interaction):
            if len(self.history) == 0:
                self.error_msg = "Nothing to undo!"
                await interaction.response.defer()
                return await self.update_dashboard(interaction)

            # Pop the last saved state and overwrite the current board
            last_state = self.history.pop()
            self.blue_dict = last_state['blue'].copy()
            self.red_dict = last_state['red'].copy()
            self.banned_champs = last_state['bans'].copy()
            self.error_msg = None

            await interaction.response.defer()
            await self.update_dashboard(interaction)
            return None

        undo_btn.callback = undo_callback
        self.add_item(undo_btn)

        # Ban button
        ban_btn = discord.ui.Button(label="Add Ban", style=discord.ButtonStyle.secondary, emoji="🚫", row=2)
        async def ban_callback(interaction):
            await interaction.response.send_modal(BanInputModal(self, self.last_ban_input))

        ban_btn.callback = ban_callback
        self.add_item(ban_btn)

        # Add Reset button
        reset_btn = discord.ui.Button(label="Reset Draft", style=discord.ButtonStyle.secondary, emoji="↩️", row=2)

        async def reset_callback(interaction):
            self.blue_dict = dict.fromkeys(positions, "Unknown")
            self.red_dict = dict.fromkeys(positions, "Unknown")
            self.banned_champs = []
            self.last_ban_input = ""
            self.history = []
            self.error_msg = None
            await interaction.response.defer()
            await self.update_dashboard(interaction)

        reset_btn.callback = reset_callback
        self.add_item(reset_btn)

    # Takes a snapshot of the board before a change happens
    def save_state(self):
        self.history.append({
            'blue': self.blue_dict.copy(),
            'red': self.red_dict.copy(),
            'bans': self.banned_champs.copy()
        })

    async def update_dashboard(self, interaction: discord.Interaction):
        top_picks = self.ai.suggest_champion(self.role, self.user_team, self.blue_dict, self.red_dict, self.role_db, self.banned_champs)

        # Call build_draft_embed from embed_formatter.py
        embed = build_draft_embed(
            role=self.role,
            user_team=self.user_team,
            error_msg=self.error_msg,
            top_picks=top_picks,
            blue_dict=self.blue_dict,
            red_dict=self.red_dict,
            role_db=self.role_db,
            banned_champs=self.banned_champs
        )

        image_buffer = await render_draft_board(
            self.blue_dict,
            self.red_dict,
            self.role,
            interaction.user.display_name,
            self.user_team
        )
        file = discord.File(fp=image_buffer, filename="draft_board.png")

        try:
            await interaction.edit_original_response(embed=embed, view=self, attachments=[file])
        except discord.errors.InteractionResponded:
            pass

# This class handles champion input for bans in '/coach'
class BanInputModal(discord.ui.Modal):
    def __init__(self, dashboard_view, default_text: str = ""):
        super().__init__(title="Add Banned Champions")
        self.dashboard = dashboard_view

        self.champ_input = discord.ui.TextInput(
            label="Banned Champion",
            placeholder="e.g., Aatrox, Zed, Yasuo",
            required=True,
            max_length=100,
            default=default_text
        )
        self.add_item(self.champ_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Instantly save whatever they typed into the Dashboard's memory
        self.dashboard.last_ban_input = self.champ_input.value

        # Split by comma and instantly remove any extra spaces
        raw_inputs = [c.strip() for c in self.champ_input.value.split(',') if c.strip()]

        # Enforce 1 to 5 champions per submission
        if len(raw_inputs) > 5:
            self.dashboard.error_msg = "You can only add up to 5 bans at a time!"
            return await self.dashboard.update_dashboard(interaction)

        # Enforce the absolute 10-ban limit
        if len(self.dashboard.banned_champs) + len(raw_inputs) > 10:
            self.dashboard.error_msg = f"Exceeds the 10 ban limit! (Currently at {len(self.dashboard.banned_champs)}/10)"
            return await self.dashboard.update_dashboard(interaction)

        valid_bans_to_add = []

        # Validate every single typed champion before locking any of them in
        for raw_champ in raw_inputs:
            champ_name = quick_resolve_champion(raw_champ, self.dashboard.champ_dict)

            if champ_name not in self.dashboard.champ_dict.values():
                self.dashboard.error_msg = f"'{raw_champ}' is not a valid champion!"
                return await self.dashboard.update_dashboard(interaction)

            if champ_name in self.dashboard.blue_dict.values() or champ_name in self.dashboard.red_dict.values():
                self.dashboard.error_msg = f"{champ_name} is already locked in! Cannot ban."
                return await self.dashboard.update_dashboard(interaction)

            if champ_name in self.dashboard.banned_champs or champ_name in valid_bans_to_add:
                self.dashboard.error_msg = f"{champ_name} is already banned!"
                return await self.dashboard.update_dashboard(interaction)

            valid_bans_to_add.append(champ_name)

        # If everything passes, inject all the valid bans at once
        self.dashboard.save_state()
        self.dashboard.banned_champs.extend(valid_bans_to_add)
        self.dashboard.last_ban_input = ""
        self.dashboard.error_msg = None
        await self.dashboard.update_dashboard(interaction)
        return None