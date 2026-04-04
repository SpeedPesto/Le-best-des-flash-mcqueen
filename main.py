import discord
from discord.ext import commands
from RdmCommands import setup_rdmCommand
from YoutubeAudio import setup_YoutubeAudio
from Stats import setup_stats
from messagesStats import setup_messagesStats
from iaController import setup_iaController
import sys
from dotenv import load_dotenv
from vocStats import setup_vocalStats
import os
import firebase_admin
from firebase_admin import credentials, firestore
from Stats import handle_stats_message
from messagesStats import handle_messages_stats
print(sys.executable)

load_dotenv()
TOKEN = os.getenv("TOKEN")

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

setup_rdmCommand(bot)
setup_YoutubeAudio(bot)
setup_stats(bot)
setup_messagesStats(bot)
setup_iaController(bot)
setup_vocalStats(bot)

@bot.event
async def on_message(message):
    print("ON MESSAGE DÉCLENCHÉ")
    if message.author.bot:
        return

    await handle_stats_message(message)
    await handle_messages_stats(message)

    await bot.process_commands(message)

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