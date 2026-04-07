import discord
from discord.ext import commands
import os, sys
import json
import requests
import re
from dotenv import load_dotenv
from riot_api import RiotAPIClient
from ai_wrapper import LeagueAI
import logging

# This creates and print debugs logs properly.
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/furina.log"),  # saves to a file
        logging.StreamHandler()              # still shows in console
    ]
)
logger = logging.getLogger(__name__)

# Initiate Data Dragon dictionary API  as a function
CACHE_FILE = "data/champion_cache.json"
def get_champion_mapping():
    try:
        # Fetch just the version number
        latest_version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10).json()[0]

        # Check if cache exists and is up to date
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                cached_data = json.load(f)

                # If cache matches the live patch, use the cache
                if cached_data.get("version") == latest_version:
                    return cached_data.get("mapping")

        # If no cache exists, or the patch updated, download the heavy file
        champ_data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json", timeout=10).json()

        id_to_name = {str(info['key']): name for name, info in champ_data['data'].items()}
        id_to_name["-1"] = "None"

        # Save the new mapping and version to the cache file
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True) # Ensure 'data' folder exists
        with open(CACHE_FILE, "w") as f:
            json.dump({"version": latest_version, "mapping": id_to_name}, f, indent=4)
        return id_to_name

    except Exception as e:
        logger.error(f"Data Dragon error: {e}")

        # Just in case the Riot Server is down (Imagine RITO????)
        if os.path.exists(CACHE_FILE):
            logger.warning("Network Failed: Falling back to old local cache.")
            with open(CACHE_FILE, "r") as f:
                return json.load(f).get("mapping", {})

        return {} # Return an empty dictionary if everything fails

# Initiate Roles from Champion_Roles.json as a function
def load_meta_roles():
    try:
        with open('data/Champion_Roles.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.warning("⚠️ CRITICAL: Could not find data/Champion_Roles.json!")
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

if not TOKEN or not RIOT_KEY: # Stop the system if .env is not set up.
    sys.exit("Error: DISCORD_TOKEN and RIOT_API_KEY must be set in the .env file.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=custom_prefix, case_insensitive=True, intents=intents)

if __name__ == "__main__":
    logger.info("Downloading Data Dragon files...")
    champ_dict_cache = get_champion_mapping()
    meta_db_cache = load_meta_roles()


    @bot.event
    async def on_ready():
        bot.remove_command('help')
        print(f'Logged in as {bot.user.name}')

        # Wake up the ducking tools.
        bot.riot_client = RiotAPIClient(RIOT_KEY)
        bot.ai_system = LeagueAI()

        bot.meta_db = meta_db_cache
        bot.champ_dict = champ_dict_cache

        # And then dump everything to the Cog
        await bot.load_extension("cogs.draft_commands")

        logger.info("Furina Architecture Online and Ready!")

    bot.run(TOKEN)
