import discord
from firebase_admin import firestore
from typing import Optional

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


def save_banque(user_id, amount):
    db = get_db()
    doc_ref = db.collection("banque").document(user_id)

    doc_ref.set({
        "enfants": firestore.Increment(amount)
    }, merge=True)

def setup_EnfantsManager(bot):

    async def messages_user_autocomplet(interaction: discord.Interaction, current: str):
        choix = [member.display_name for member in interaction.guild.members if not member.bot]
        return [discord.app_commands.Choice(name=c, value=c) for c in choix if current.lower() in c.lower()][:25]

    @bot.tree.command(name="bal")
    @discord.app_commands.describe(user="Choisis un utilisateur")
    @discord.app_commands.autocomplete(user=messages_user_autocomplet)
    async def bal(interaction: discord.Interaction, user: Optional[str] = None):
        await interaction.response.defer()

        if user is None: user = interaction.user.display_name

        member = discord.utils.get(interaction.guild.members, display_name=user)
        user_id = str(member.id) if member else None

        if not user_id:
            await interaction.followup.send("Utilisateur introuvable.")
            return

        data = load_banque()
        enfants = data.get(user_id, {}).get("enfants", 0)

        if enfants == 0:
            await interaction.followup.send("Pas d'enfants")
            return

        embed = discord.Embed(
            title=f"Balance de {member.display_name}",
            description=f"**{enfants}** enfants",
            color=0xff0000
        )

        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="give")
    @discord.app_commands.describe(user="Choisis un utilisateur", num="Combien d'enfants")
    @discord.app_commands.autocomplete(user=messages_user_autocomplet)
    async def give(interaction: discord.Interaction, user: str, num: int):
        await interaction.response.defer()

        member = discord.utils.get(interaction.guild.members, display_name=user)
        user_id = str(member.id) if member else None

        if not user_id:
            await interaction.followup.send("Utilisateur introuvable.")
            return

        save_banque(user_id, num)

        await interaction.followup.send(f"Dont de **{num}** enfants de l'orphelinat à {member.mention} par {interaction.user.mention} !")

async def setup_banque(guild):
    members = guild.members
    for m in members:
        user_id = str(m.id)
        if m.bot: continue
        if not user_id: continue

        data = load_banque()
        enfants = data.get(user_id, {}).get("enfants", 0)
        if enfants == 0: save_banque(user_id, 100)

