import datetime

import discord
import json
import os
import matplotlib.pyplot as plt
import io

class messStatView(discord.ui.View):
    def __init__(self, bot, load_stats, user, display_name):
        super().__init__(timeout=None)
        self.bot = bot
        self.load_stats = load_stats
        self.user = user
        self.display_name = display_name

    @discord.ui.select(
        placeholder="Choisir une stat...",
        options=[
            discord.SelectOption(label="Message le plus pop", value="most_pop_mot"),
            discord.SelectOption(label="Heure moyenne d'envoie de message", value="heure_moy"),
            discord.SelectOption(label="Channel le plus utilisé", value="most_pop_channel"),
        ]
    )
    async def select_stat(self, interaction: discord.Interaction, select: discord.ui.Select):
        choix = select.values[0]
        data = self.load_stats()

        embed, file = await getEmbed(self.bot, data, choix, self.user, self.display_name)
        if file: await interaction.response.edit_message(embed=embed, attachments=[file])
        else: await interaction.response.edit_message(embed=embed, attachments=[])


async def getEmbed(bot, data, stat, user_id, display_name):
    file = None

    if stat == "most_pop_mot":
        titre = f"Mot le plus écrit de {display_name}"
        user_id = str(user_id)
        if user_id not in data: return None, None
        tous_les_mots = []
        for msg in data[user_id]["messages"]:
            tous_les_mots.extend(msg["content"].split())

        from collections import Counter
        most_common = Counter(tous_les_mots).most_common(1)[0]
        desc = f"Dit **{most_common[1]}** fois : **{most_common[0]}**"

    if stat == "heure_moy":
        titre = f"Heure moyenne d'envoi de {display_name}"
        user_id = str(user_id)
        if user_id not in data: return None, None

        toutes_les_minutes = []
        toutes_les_heures = []
        for msg in data[user_id]["messages"]:
            date = datetime.datetime.fromisoformat(msg["date"])
            toutes_les_minutes.append(date.hour * 60 + date.minute)
            toutes_les_heures.append(date.hour)

        moyenne = sum(toutes_les_minutes) / len(toutes_les_minutes)
        heures = int(moyenne) // 60
        minutes = int(moyenne) % 60
        desc = f"Écrit en moyenne à **{heures}h{minutes:02d}**"

        buf = generate_graph(toutes_les_heures)
        file = discord.File(buf, filename="graph.png")

    if stat == "most_pop_channel":
        titre = f"Channel le plus utilisé par {display_name}"
        user_id = str(user_id)
        if user_id not in data: return None, None

        from collections import Counter
        channels = [msg["channel"] for msg in data[user_id]["messages"]]
        compteur = Counter(channels)

        desc = ""
        for channel_name, count in compteur.most_common():
            channel = discord.utils.get(bot.get_all_channels(), name=channel_name)
            if channel:
                desc += f"<#{channel.id}> — {count} messages\n"
            else:
                desc += f"#{channel_name} — {count} messages\n"

    embed = discord.Embed(title=titre, description=desc, color=0xff0000)
    if file:
        embed.set_image(url="attachment://graph.png")

    return embed, file


def generate_graph(toutes_les_heures):
    from collections import Counter
    compteur = Counter(toutes_les_heures)

    heures = list(range(24))
    counts = [compteur.get(h, 0) for h in heures]

    plt.figure(figsize=(10, 4))
    plt.bar(heures, counts, color="royalblue")
    plt.xlabel("Heure")
    plt.ylabel("Messages")
    plt.title("Activité par heure")
    plt.xticks(heures)

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    return buf

def load_messages():
    if os.path.exists("messages.json"):
        with open("messages.json", "r") as f:
            return json.load(f)
    else:
        return {}

def save_messages(messages):
    with open("messages.json", "w") as f:
        json.dump(messages, f, indent=4)














def setup_messagesStats(bot):
    stats_choix = ["most_pop_mot", "heure_moy", "most_pop_channel"]

    @bot.event
    async def on_message(message):

        messages = load_messages()
        user_id = str(message.author.id)

        if message.content == "" : return

        if user_id not in messages:
            messages[user_id] = {"messages": []}
        messages[user_id]["messages"].append({
            "content": message.content,
            "date": message.created_at.isoformat(),
            "channel": message.channel.name,
            "id": message.id
        })


        save_messages(messages)

    async def messages_user_autocomplet(interaction: discord.Interaction, current: str):
        choix = [member.display_name for member in interaction.guild.members if not member.bot]

        return [
            discord.app_commands.Choice(name=c, value=c)
            for c in choix if current.lower() in c.lower()
        ][:25]

    async def messages_stat_autocomplet(interaction: discord.Interaction, current: str):
        choix = stats_choix

        return [
            discord.app_commands.Choice(name=c, value=c)
            for c in choix if current.lower() in c.lower()
        ][:25]

    @bot.tree.command(name="mess_stats")
    @discord.app_commands.describe(user="Choisis un utilisateur")
    @discord.app_commands.autocomplete(user=messages_user_autocomplet)
    @discord.app_commands.describe(mess_stat="Choisis une stat")
    @discord.app_commands.autocomplete(mess_stat=messages_stat_autocomplet)
    async def stats(interaction: discord.Interaction, user: str, mess_stat: str):
        await interaction.response.defer()
        member = discord.utils.get(interaction.guild.members, display_name=user)
        user_id = str(member.id) if member else None

        if not user_id:
            await interaction.followup.send("Utilisateur introuvable.")
            return

        if mess_stat in stats_choix:
            messages = load_messages()
            embed, file = await getEmbed(bot, messages, mess_stat, user_id, user)
            if file: await interaction.followup.send(embed=embed, file=file, view=messStatView(bot, load_messages, user_id, user))
            else: await interaction.followup.send(embed=embed, view=messStatView(bot, load_messages, user_id, user))