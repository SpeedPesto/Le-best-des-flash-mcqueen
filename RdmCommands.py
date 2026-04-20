import json
import os

import discord
import random


def setup_rdmCommand(bot):

    @bot.tree.command(name="salut")
    async def salut(interaction: discord.Interaction):
        await interaction.response.send_message("Ka-chow 🚗💨")

    @bot.tree.command(name="qui_es-tu")
    async def salut(interaction: discord.Interaction):
        message = (
            "*Bon allons-y concentrations, rapide...* **Je suis rapide !**\n"
            "1 vainqueur 42 perdants, j'en fais qu'une boucher a mon ptit déjeuner des perdants !\n"
            "Oh en parlant de petit déjeuner, un bon ptit dej ça me ferait peut-être du bien !\n"
            "Non non non concentration ! *Vitesse...* plus rapide que la lumière, **JE SUIS FLASH MCQUEEN !!**"
        )
        await interaction.response.send_message(message)

    @bot.tree.command(name="rdm_mess")
    async def salut(interaction: discord.Interaction):
        await interaction.response.defer()

        messages = []
        for channel in interaction.guild.text_channels:
            async for message in channel.history(limit=100):
                if not message.author.bot:
                    messages.append((message, message.author))

        message_random, author = random.choice(messages)

        embed = discord.Embed(
            title=f"{author} à dit :",
            description=message_random.content,
            color=0xff0000
        )

        embed.add_field(name="Date", value=message_random.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)

        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="rdm_num")
    async def salut(interaction: discord.Interaction, nbr:int):

        reponse = random.randrange(0, nbr)

        await interaction.response.send_message(f"{reponse}")

    @bot.tree.command(name="note")
    @discord.app_commands.describe(guest="Choisis un truc à noter")
    async def note_cmd(interaction: discord.Interaction, guest: str):

        def load_note():
            if os.path.exists("note.json"):
                with open("note.json", "r") as f:
                    return json.load(f)
            else:
                return {}

        def save_note(note):
            with open("note.json", "w") as f:
                json.dump(note, f, indent=4)

        note = load_note()
        rdm_num = random.randrange(0, 100)

        if note.get(guest) is not None:
            rdm_num = note[guest]
        else:
            note[guest] = rdm_num
            save_note(note)

        await interaction.response.send_message(f"{guest} : {rdm_num} / 100")