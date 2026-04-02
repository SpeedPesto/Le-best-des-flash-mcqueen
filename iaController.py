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

    @discord.ui.button(label="Training", style=discord.ButtonStyle.primary, custom_id="ia_train")
    async def train(self, interaction, button):
        await interaction.response.defer()
        if self.ia_type == None:
            await interaction.followup.send("Choisi une ia !", ephemeral=True)
        else :
            embed = await getEmbed(self.ia_type, self.ia_default_stats, True)
            await interaction.edit_original_response(embed=embed)
            self.message = await interaction.original_response()

            self.training_time[self.ia_type] = datetime.now()
            if not self.update_embed.is_running():
                self.update_embed.start()

            async def on_epoch(epochi, img):
                file = discord.File(img, filename="preview.png")
                embed = await getEmbed(self.ia_type, self.ia_default_stats, True)
                embed.set_thumbnail(url="attachment://preview.png")
                await self.message.edit(embed=embed, attachments=[file])

            await self.ia_gen["training"](self.ia_type, self.ia_default_stats, on_epoch)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red, custom_id="ia_stop")
    async def stop(self, interaction, button):
        await interaction.response.defer()
        if self.ia_type == None:
            await interaction.followup.send("Choisi une ia !", ephemeral=True)
        else:
            await self.ia_gen["stop_training"]()
            if self.update_embed.is_running():
                self.update_embed.cancel()
            embed = await getEmbed(self.ia_type, self.ia_default_stats, False)
            await interaction.edit_original_response(embed=embed)
            await interaction.followup.send("Training arrêté avec succès !", ephemeral=True)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green, custom_id="ia_save")
    async def save(self, interaction, button):
        await interaction.response.defer()
        if self.ia_type not in self.training_time:
            await interaction.followup.send("Aucun training en cours !", ephemeral=True)
            return
        else:
            await self.ia_gen["save"](self.ia_type)
            embed = await getEmbed(self.ia_type, self.ia_default_stats, False)
            await interaction.edit_original_response(embed=embed)

            if self.update_embed.is_running():
                self.update_embed.cancel()

            data = load_ia()
            now = datetime.now()

            join_time = self.training_time[self.ia_type]
            time_in_channel = now - join_time
            seconds = round(time_in_channel.total_seconds())

            get_type_data(data, self.ia_type, self.ia_default_stats)["training_time"] += seconds
            save_ia(data)

    @discord.ui.button(label="Generate", style=discord.ButtonStyle.grey, custom_id="ia_generate")
    async def generate(self, interaction, button):
        await interaction.response.defer()
        if self.ia_type is None:
            await interaction.followup.send("Choisi une ia !", ephemeral=True)
        else:
            buffer = await self.ia_gen["generate"]()
            file = discord.File(buffer, filename="generated.png")

            data = load_ia()

            get_type_data(data, self.ia_type, self.ia_default_stats)["generate_num"] += 1
            save_ia(data)

            embed = await getEmbed(self.ia_type, self.ia_default_stats, False)
            await interaction.edit_original_response(embed=embed)
            await interaction.followup.send(f"Image généré avec succès par **{interaction.user.name}**!",file=file)

    @tasks.loop(seconds=5)
    async def update_embed(self):
        if self.message and self.ia_type:

            data = load_ia()
            now = datetime.now()

            join_time = self.training_time[self.ia_type]
            time_in_channel = now - join_time
            seconds = round(time_in_channel.total_seconds())

            get_type_data(data, self.ia_type, self.ia_default_stats)["training_time"] += seconds
            save_ia(data)

            self.training_time[self.ia_type] = datetime.now()

            embed = await getEmbed(self.ia_type, self.ia_default_stats, True)
            await self.message.edit(embed=embed)

async def getEmbed(ia_type, ia_default_stats, isTraining : bool, image_url=None):

    titre = f"Ia générative : {ia_type}"
    if isTraining:
        description = "**Je m'entraine. . .**"
        if image_url: description += f"\n\nExemple genré en **temps réel** :"
        footer = "(si tu veux générer une image, appuie d'abord sur 'SAVE'"

    else:
        description = ""
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
    embed.add_field(name="Epoch", value=str(ia_data['epoch']), inline=True)
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

def save_ia(ia, ):
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

    @bot.event
    async def on_ready():
        ia_default_stats = {"training_time": 0, "generate_num": 0, "epoch": 0}
        ia_gen = setup_iaGen()
        bot.add_view(iaView(ia_default_stats, ia_gen))