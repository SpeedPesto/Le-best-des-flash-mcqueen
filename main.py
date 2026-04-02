import discord
from discord.ext import commands
from RdmCommands import setup_rdmCommand
from YoutubeAudio import setup_YoutubeAudio
from Stats import setup_stats
from messagesStats import setup_messagesStats
from iaController import setup_iaController
import sys
from dotenv import load_dotenv
import os
print(sys.executable)

load_dotenv()
try:
    from google.colab import userdata
    TOKEN = userdata.get("DISCORD_TOKEN")
except ImportError:
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

setup_rdmCommand(bot)
setup_YoutubeAudio(bot)
setup_stats(bot)
setup_messagesStats(bot)
setup_iaController(bot)



#----------------------------------------------------------------------------------------------#

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Commandes synchronisées : {len(synced)}")
    except Exception as e:
        print(e)

bot.run(TOKEN)