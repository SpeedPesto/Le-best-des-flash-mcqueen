import discord
import asyncio

from firebase_admin import firestore
from typing import Optional
import random

class WhoSayView(discord.ui.View):
    def __init__(self, bon_auteur, choix, user_id, mise = None):
        super().__init__(timeout=None)
        self.bon_auteur     = bon_auteur
        self.termine        = False
        self.user_id        = user_id
        self.mise           = mise if mise else None

        for auteur in choix:
            button = discord.ui.Button(label=auteur.name, style=discord.ButtonStyle.grey)
            button.callback = self.make_callback(auteur)
            self.add_item(button)

    def make_callback(self, auteur):
        async def callback(interaction):
            if self.termine:
                return
            self.termine = True
            user_id = str(interaction.user.id)

            if interaction.user.id != self.user_id:
                await interaction.followup.send("Ce message ne te concerne pas :( occupe toi de tes affaires", ephemeral=True)
                return

            if auteur == self.bon_auteur:
                if self.mise : gain = self.mise * 2
                await interaction.response.send_message(f"Bravo, c'était éfféctivement **{self.bon_auteur.name}** !"
                                                        f"{f"\nTu remporte le double de ta mise (**{gain}**) !" if self.mise else ""}"
                                                        )
                if self.mise : save_banque(user_id, gain)
            else:
                await interaction.response.send_message(f"Faux, C'était **{self.bon_auteur.name}** !"
                                                        f"{f"\nTu pert ta mise (**{self.mise}**) !" if self.mise else ""}"
                                                        )
                if self.mise: save_banque(user_id, self.mise, False)
        return callback

    def get_barre(self, secondes_restantes):
        total_blocs = 15
        rempli = int((secondes_restantes / 15) * total_blocs)
        barre = "🟩" * rempli + "⬛" * (total_blocs - rempli)
        return f"{barre} \n {secondes_restantes}s restantes"

    async def lancer_timer(self, message, embed, user_id):
        for secondes_restantes in range(15, -1, -1):
            if self.termine:
                return

            embed.set_footer(text=self.get_barre(secondes_restantes))
            await message.edit(embed=embed)

            if secondes_restantes == 0:
                self.termine = True
                embed.set_footer(text=
                                 f"Temps écoulé ! \n Réponse : {self.bon_auteur.name}"
                                 f"{f"\nTu pert ta mise (**{self.mise}**) !" if self.mise else ""}"
                                 )
                if self.mise: save_banque(user_id, self.mise, False)
                await message.edit(embed=embed, view=None)

                return

            await asyncio.sleep(1)

db = None

def get_db():
    global db
    if db is None:
        db = firestore.client()
    return db

def load_banque():
    db = get_db()
    docs = db.collection("banque").stream()
    return {doc.id: doc.to_dict() for doc in docs}


def save_banque(user_id, amount, add = True):
    db = get_db()
    doc_ref = db.collection("banque").document(user_id)

    doc_ref.set({
        "enfants": firestore.Increment(amount if add else -amount),
    }, merge=True)

def load_server_config():
    db = get_db()
    docs = db.collection("serveurs").stream()
    return {doc.id: doc.to_dict() for doc in docs}

def save_whosay_banned_chanels(s_id, channels_id, supr=False):
    db = get_db()
    doc_ref = db.collection("serveurs").document(s_id)

    if supr:
        doc_ref.set({
            "channels": firestore.ArrayRemove([channels_id])
        }, merge=True)
    else:
        doc_ref.set({
            "channels": firestore.ArrayUnion([channels_id]),
        }, merge=True)

def setup_WhoSay(bot):

    @bot.tree.command(name="whosay")
    @discord.app_commands.describe(mise="Choisis une mise (OPTIONNEL)")
    async def salut(interaction: discord.Interaction, mise: Optional[int] = None):
        await interaction.response.defer()

        data = load_banque()
        user_id = str(interaction.user.id)

        if mise:
            if not data[user_id]["enfants"]:
                await interaction.followup.send("Joueur non trouvé")
                return
            if mise > data[user_id]["enfants"]:
                await interaction.followup.send("t'a pas assez :(")
                return

        messages = []
        config = load_server_config().get(str(interaction.guild.id), {})
        ban_channels = config.get("channels", [])

        for channel in interaction.guild.text_channels:
            if channel.id in ban_channels: continue
            async for message in channel.history(limit=100):
                if not message.author.bot:
                    messages.append((message, message.author))

        message_random, author = random.choice(messages)

        members = []
        for member in interaction.guild.members:
            # if member.bot or member == author : continue
            members.append(member)

        faux = random.sample(members, 2)
        choix = faux + [author]
        random.shuffle(choix)

        embed = discord.Embed(
            title=f"{interaction.user.display_name}, Qui a dit ça ?",
            description=message_random.content,
            color=0xff0000
        )

        if mise: embed.add_field(name="Mise", value=mise, inline=False)
        view = WhoSayView(author, choix, interaction.user.id, mise or None)
        message = await interaction.followup.send(embed=embed, view=view)
        await view.lancer_timer(message, embed, interaction.user.id)

    async def channels_autocomplet(interaction: discord.Interaction, current: str):
        return [
            discord.app_commands.Choice(name=channel.name, value=str(channel.id))
            for channel in interaction.guild.text_channels
            if current.lower() in channel.name.lower()
        ][:25]

    @bot.tree.command(name="whosay-ban-channel")
    @discord.app_commands.describe(c_id="Channel à ban", c2_id="Channel à ban (OPTIONNEL)", c3_id="Channel à ban (OPTIONNEL)")
    @discord.app_commands.autocomplete(c_id=channels_autocomplet, c2_id=channels_autocomplet, c3_id=channels_autocomplet)
    async def salut(interaction: discord.Interaction, c_id: str, c2_id: Optional[str] = None, c3_id: Optional[str] = None):

        s_id = str(interaction.guild.id)
        for cid in [c_id, c2_id, c3_id]:
            if cid: save_whosay_banned_chanels(s_id, int(cid))

        names = [
            f"<#{int(cid)}>"
            for cid in [c_id, c2_id, c3_id]
            if cid and interaction.guild.get_channel(int(cid))
        ]

        await interaction.response.send_message(
            f"serveur{'s' if c2_id else ''} bannis : {', '.join(names)}",
            ephemeral=True
        )

    @bot.tree.command(name="whosay-ban-list")
    async def salut(interaction: discord.Interaction):
        await interaction.response.defer()

        data = load_server_config()
        channels = data.get(str(interaction.guild.id), {}).get("channels", [])

        channels_names = [
            interaction.guild.get_channel(c).name
            for c in channels
            if interaction.guild.get_channel(c)
        ]

        desc = ", ".join(channels_names) if channels_names else "Aucun channel banni."
        await interaction.followup.send(embed=discord.Embed(title="**WhoSay**, Channels **bannis** :", description=desc, color=0xff0000))