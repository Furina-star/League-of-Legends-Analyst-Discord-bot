import discord
from discord.ext import commands
import os
import json
import requests
import re
from dotenv import load_dotenv

# Classes
from riot_api import RiotAPIClient
from ai_wrapper import LeagueAI

# Initiate Data Dragon dictionary API  as a function
def get_champion_mapping():
    try:
        version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
        champ_data = requests.get(f"http://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json").json()

        id_to_name = {str(info['key']): name for name, info in champ_data['data'].items()}
        id_to_name["-1"] = "None"  # Riot's code for "No Ban"

        return id_to_name
    except Exception as e:
        print(f"⚠️ Data Dragon Error: {e}")
        return {}  # Return an empty dictionary if Riot's servers are down

# Initiate Roles from Champion_Roles.json as a function
def load_meta_roles():
    try:
        with open('data/Champion_Roles.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("⚠️ CRITICAL: Could not find data/Champion_Roles.json!")
        return {}

# Custom Prefix
def custom_prefix(bot, message):
    match = re.match(r'^(furina\s*|f\s*)', message.content, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return "!"  # Default fallback

# Initiate the bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
RIOT_KEY = os.getenv('RIOT_API_KEY')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=custom_prefix, case_insensitive=True, intents=intents)

@bot.event
async def on_ready():
    # Remove the default help since it uses a custom one
    bot.remove_command('help')

    print(f'Logged in as {bot.user.name}')

    # Wake up the ducking tools.
    bot.riot_client = RiotAPIClient(RIOT_KEY)
    bot.ai_system = LeagueAI()
    bot.meta_db = load_meta_roles()
    bot.champ_dict = get_champion_mapping()

    # And then dump everything to the Cog
    await bot.load_extension("cogs.draft_commands")

    print("Furina Architecture Online and Ready!")

if __name__ == "__main__":
    if not TOKEN or not RIOT_KEY:
        print("⚠️ Error: Missing Discord Token or Riot API Key in .env file!")
    else:
        bot.run(TOKEN)
