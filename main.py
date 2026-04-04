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
import gdown
print(sys.executable)

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

os.makedirs("models", exist_ok=True)

urls = [
    "https://drive.google.com/file/d/1SkNOdgzLNqOQveKCsOGTcEZO0c4mM4nx/view",
    "https://drive.google.com/file/d/1zV4eieefZvvsfNF3cSBNjxqUqECB40Hx/view"
]

for url in urls:
    file_id = url.split("/d/")[1].split("/")[0]

    output_path = f"models/{file_id}.pth"

    gdown.download(
        f"https://drive.google.com/uc?id={file_id}",
        output_path,
        quiet=False
    )

    print(f"{output_path} téléchargé")



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