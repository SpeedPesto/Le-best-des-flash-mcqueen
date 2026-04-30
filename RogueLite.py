import random

import discord
from groq import Groq
import os
from dotenv import load_dotenv
from firebase_admin import firestore

load_dotenv()

GROC_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROC_KEY)

current_items = ["Aucun"]

class exploreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.message = None

        self.select_item = discord.ui.Select(
            custom_id="e_mine",
            placeholder="Choisir de récupérer un item",
            options=[discord.SelectOption(label=item, value=item) for item in current_items]
        )
        self.select_item.callback = self.select_callback
        self.add_item(self.select_item)

    async def select_callback(self, interaction: discord.Interaction):
        choix = self.select_item.values[0]
        await interaction.response.send_message(f"tu as choisi : {choix}", ephemeral=True)

    @discord.ui.button(label="Next Salle", style=discord.ButtonStyle.blurple, custom_id="e_next")
    async def generate(self, interaction, button):
        await interaction.response.defer()
        embed = await getEmbed()

        self.select_item.options = [discord.SelectOption(label=item, value=item) for item in current_items]

        await self.message.edit(embed=embed, view=self)

def get_items(n, k):
    items = [
        "arbre",
        "cailloux",
        "fer",
        "or",
        "diamant",
        "platine",
        "obsidienne",
    ]

    poids = {
        "arbre": [80, 20],
        "cailloux": [70, 30],
        "fer": [60, 40],
        "or": [50, 50],
        "diamant": [40, 60],
        "platine": [30, 70],
        "obsidienne": [20, 80],
    }

    niveaux_poids = [poids[item][n] for item in items]
    resultat = []
    items_restants = items.copy()
    poids_restants = niveaux_poids.copy()

    for _ in range(k):
        choix = random.choices(items_restants, weights=poids_restants, k=1)[0]
        idx = items_restants.index(choix)
        resultat.append(choix)
        items_restants.pop(idx)
        poids_restants.pop(idx)

    return resultat

async def getEmbed():
    global current_items

    titre = f"Exploration, **salle : 0**"

    items = get_items(0,3)
    current_items = items
    description = f"Items dans la salle : \n" +  "\n".join(f"- {item}" for item in items)

    footer = f"Exploration de : user"

    embed = discord.Embed(title=titre, description=description, color=0xff0000)
    embed.add_field(name="Niveau", value=f"0", inline=True)
    embed.set_footer(text=footer)

    return embed

db = None

def get_db():
    global db
    if db is None:
        db = firestore.client()
    return db

def load_rl():
    db = get_db()
    docs = db.collection("rl").stream()
    return {doc.id: doc.to_dict() for doc in docs}


def save_rl(user_id, amount, add = True):
    db = get_db()
    doc_ref = db.collection("rl").document(user_id)

    doc_ref.set({
        "enfants": firestore.Increment(amount if add else -amount),
        "hp": firestore.Increment(amount if add else -amount)
    }, merge=True)

def setup_roguelite(bot):

    action = ["Explorer", "duel", "demander à dieu"]

    async def actions_autocomplet(interaction: discord.Interaction, current: str):
        return [discord.app_commands.Choice(name=a, value=a) for a in action if current.lower() in a.lower()][:25]

    @bot.tree.command(name="rl")
    @discord.app_commands.describe(action="action")
    @discord.app_commands.autocomplete(action=actions_autocomplet)
    async def command_groq(interaction: discord.Interaction, action : str):
        await interaction.response.defer()

        if action == "Explorer":
            view = exploreView()
            view.message = await interaction.original_response()
            await interaction.followup.send(embed=await getEmbed(), view=view)
        else:
            await interaction.followup.send("tg")
