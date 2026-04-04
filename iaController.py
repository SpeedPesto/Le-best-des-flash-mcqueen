from datetime import datetime
import os
import json
from discord.ext import tasks

import discord
from iaGen import setup_iaGen


class iaView(discord.ui.View):
    def __init__(self, ia_default_stats, ia_gen):
        super().__init__(timeout=None)
        self.ia_default_stats = ia_default_stats
        self.ia_type = None
        self.ia_gen = ia_gen
        self.training_time = {}
        self.message = None
        self.buffer = None

    @discord.ui.select(
        custom_id="ia_select",
        placeholder="Choisir une ia...",
        options=[
            discord.SelectOption(label="Chien", value="chien")
        ]
    )

    async def select_stat(self, interaction: discord.Interaction, select: discord.ui.Select):
        choix = select.values[0]
        embed = await getEmbed(choix, self.ia_default_stats, False)

        self.ia_type = choix
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Generate", style=discord.ButtonStyle.blurple, custom_id="ia_generate")
    async def generate(self, interaction, button):
        await interaction.response.defer()
        if self.ia_type is None:
            await interaction.followup.send("Choisi une ia !", ephemeral=True)
        else:
            buffer = await self.ia_gen["generate"](self.ia_type)
            if buffer is None:
                await interaction.followup.send(f"Aucun modèle de {self.ia_type} trouvé", ephemeral=True)
                return

            data = load_ia()

            get_type_data(data, self.ia_type, self.ia_default_stats)["generate_num"] += 1
            save_ia(data)

            embed = await getEmbed(self.ia_type, self.ia_default_stats, interaction.user.mention, "attachment://preview.png")
            file = discord.File(buffer, filename="preview.png")
            self.buffer = buffer
            await self.message.edit(embed=embed, attachments=[file])

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green, custom_id="ia_save")
    async def save(self, interaction, button):
        await interaction.response.defer(ephemeral=True)

        if not self.buffer:
            await interaction.followup.send("Aucune image à sauvegarder !")
            return

        import io
        self.buffer.seek(0)
        file = discord.File(io.BytesIO(self.buffer.read()), filename="preview.png")
        await interaction.followup.send("Quel image de GOAT, rien que pour toi bg :)", file=file, ephemeral=True)

async def getEmbed(ia_type, ia_default_stats, user_id=None, image_url=None):

    titre = f"Ia générative : {ia_type}"
    description = f"Dernière photo générée par : **{user_id}**" if user_id else ""

    footer = "Tu peux générer une image en cliquant sur 'Generate'"

    data = load_ia()
    ia_data = get_type_data(data, ia_type, ia_default_stats)
    training_time = ia_data['training_time']
    heures = training_time // 3600
    minutes = (training_time % 3600) // 60
    secondes = training_time % 60
    images_generees = ia_data['generate_num']

    embed = discord.Embed(title=titre, description=description, color=0xff0000)
    embed.add_field(name="Training time", value=f"{heures}h {minutes}m {secondes}s", inline=True)
    embed.add_field(name="Images générées", value=str(images_generees), inline=True)
    embed.set_footer(text=footer)

    if image_url:
        embed.set_image(url=image_url)

    return embed

def load_ia():
    if os.path.exists("ia.json"):
        with open("ia.json", "r") as f:
            return json.load(f)
    else:
        return {}

import threading
_lock = threading.Lock()

def save_ia(ia):
    with _lock:
        with open("ia.json", "w") as f:
            json.dump(ia, f, indent=4)

def get_type_data(data, ia_type, ia_default_stats):
    if ia_type not in data:
        data[ia_type] = ia_default_stats.copy()
    return data[ia_type]

def setup_iaController(bot):
    ia_default_stats = {"training_time": 0, "generate_num": 0, "epoch": 0}
    ia_gen = setup_iaGen()

    @bot.tree.command(name="ia")
    async def stats(interaction: discord.Interaction):

        embed = discord.Embed(
            title="Ia générative super méga giga cool",
            description="",
            color=0xff0000
        )

        view = iaView(ia_default_stats, ia_gen)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()