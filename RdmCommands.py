import json
import os

import discord
import random
import asyncio

class WhoSayView(discord.ui.View):
    def __init__(self, bon_auteur, choix):
        super().__init__(timeout=None)
        self.bon_auteur = bon_auteur
        self.termine = False

        for auteur in choix:
            button = discord.ui.Button(label=auteur.name, style=discord.ButtonStyle.grey)
            button.callback = self.make_callback(auteur)
            self.add_item(button)

    def make_callback(self, auteur):
        async def callback(interaction):
            if self.termine:
                return
            self.termine = True

            if auteur == self.bon_auteur:
                await interaction.response.send_message(f"Bravo, c'était éfféctivement {self.bon_auteur.name} !")
            else:
                await interaction.response.send_message(f"Faux, C'était {self.bon_auteur.name} !")
        return callback

    def get_barre(self, secondes_restantes):
        total_blocs = 15
        rempli = int((secondes_restantes / 15) * total_blocs)
        barre = "🟩" * rempli + "⬛" * (total_blocs - rempli)
        return f"{barre} \n {secondes_restantes}s restantes"

    async def lancer_timer(self, message, embed):
        for secondes_restantes in range(15, -1, -1):
            if self.termine:
                return

            embed.set_footer(text=self.get_barre(secondes_restantes))
            await message.edit(embed=embed)

            if secondes_restantes == 0:
                self.termine = True
                embed.set_footer(text=f"Temps écoulé ! \n Réponse : {self.bon_auteur.name}")
                await message.edit(embed=embed, view=None)
                return

            await asyncio.sleep(1)

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

    @bot.tree.command(name="whosay")
    async def salut(interaction: discord.Interaction):
        await interaction.response.defer()

        messages = []
        for channel in interaction.guild.text_channels:
            async for message in channel.history(limit=100):
                if not message.author.bot:
                    messages.append((message, message.author))

        message_random, author = random.choice(messages)

        members = []
        for member in interaction.guild.members :
            if member.bot or member == author : continue
            members.append(member)

        faux = random.sample(members, 2)
        choix = faux + [author]
        random.shuffle(choix)

        embed = discord.Embed(
            title="Qui a dit ça ?",
            description=message_random.content,
            color=0xff0000
        )

        view = WhoSayView(author, choix)
        message = await interaction.followup.send(embed=embed, view=view)
        await view.lancer_timer(message, embed)

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