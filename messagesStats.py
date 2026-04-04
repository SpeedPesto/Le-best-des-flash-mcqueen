import datetime
import discord
import json
import os
import matplotlib.pyplot as plt
import io
from collections import Counter

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

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
            discord.SelectOption(label="Mot le plus écrit",         value="most_pop_world"),
            discord.SelectOption(label="Heure moyenne d'envoi",     value="heure_moy"),
            discord.SelectOption(label="Channel le plus utilisé",   value="most_pop_channel"),
            discord.SelectOption(label="Jour le plus actif",        value="most_pop_day"),
            discord.SelectOption(label="Longueur moyenne",          value="moy_length"),
            discord.SelectOption(label="Total de mots écrits",      value="total_words"),
            discord.SelectOption(label="Message le plus long",      value="longest_msg"),
            discord.SelectOption(label="Premier message",           value="first_msg"),
            discord.SelectOption(label="Streak de jours actifs",    value="streak"),
        ]
    )
    async def select_stat(self, interaction: discord.Interaction, select: discord.ui.Select):
        choix = select.values[0]
        data = self.load_stats()
        embed, file = await getEmbed(self.bot, data, choix, self.user, self.display_name)
        if file: await interaction.response.edit_message(embed=embed, attachments=[file])
        else:    await interaction.response.edit_message(embed=embed, attachments=[])


async def getEmbed(bot, data, stat, user_id, display_name):
    file = None
    user_id = str(user_id)

    if user_id not in data or not data[user_id]["messages"]:
        embed = discord.Embed(title="Aucune donnée", description="Pas de messages enregistrés.", color=0xff0000)
        return embed, None

    messages = data[user_id]["messages"]

    # -- Mot le plus écrit ------------------------------------------------------
    if stat == "-most_pop_world":
        titre = f"Mot le plus écrit de {display_name}"
        tous_les_mots = []
        for msg in messages:
            tous_les_mots.extend(msg["content"].lower().split())
        most_common = Counter(tous_les_mots).most_common(1)[0]
        desc = f"Dit **{most_common[1]}** fois : **{most_common[0]}**"

    # -- Heure moyenne ----------------------------------------------------------
    elif stat == "heure_moy":
        titre = f"Heure moyenne d'envoi de {display_name}"
        toutes_les_minutes = []
        toutes_les_heures  = []
        for msg in messages:
            date = datetime.datetime.fromisoformat(msg["date"])
            toutes_les_minutes.append(date.hour * 60 + date.minute)
            toutes_les_heures.append(date.hour)
        moyenne = sum(toutes_les_minutes) / len(toutes_les_minutes)
        heures  = int(moyenne) // 60
        minutes = int(moyenne) % 60
        desc = f"Écrit en moyenne à **{heures}h{minutes:02d}**"
        buf  = generate_hour_graph(toutes_les_heures)
        file = discord.File(buf, filename="graph.png")

    # -- Channel le plus utilisé ------------------------------------------------
    elif stat == "most_pop_channel":
        titre    = f"Channel le plus utilisé par {display_name}"
        channels = [msg["channel"] for msg in messages]
        compteur = Counter(channels)
        desc     = ""
        for channel_name, count in compteur.most_common():
            channel = discord.utils.get(bot.get_all_channels(), name=channel_name)
            desc   += f"{'<#' + str(channel.id) + '>' if channel else '#' + channel_name} — **{count}** messages\n"

    # -- Jour le plus actif -----------------------------------------------------
    elif stat == "most_pop_day":
        titre = f"Jour le plus actif de {display_name}"
        weekdays = [datetime.datetime.fromisoformat(msg["date"]).weekday() for msg in messages]
        compteur = Counter(weekdays)
        counts = [compteur.get(d, 0) for d in range(7)]

        plt.figure(figsize=(10, 4))
        plt.bar(JOURS, counts, color="royalblue")
        plt.xlabel("Jour")
        plt.ylabel("Messages")
        plt.title("Activité par jour")

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        desc = f"Jour le plus actif : **{JOURS[max(compteur, key=compteur.get)]}** avec **{max(compteur.values())} messages**"
        file = discord.File(buf, filename="graph.png")

    # -- Longueur moyenne -------------------------------------------------------
    elif stat == "moy_length":
        titre    = f"Longueur moyenne des messages de {display_name}"
        longueurs = [msg.get("char_count", len(msg["content"])) for msg in messages]
        moy_chars = sum(longueurs) / len(longueurs)
        moy_mots  = sum(msg.get("word_count", len(msg["content"].split())) for msg in messages) / len(messages)
        desc      = f"En moyenne **{moy_chars:.1f} caractères** et **{moy_mots:.1f} mots** par message"

    # -- Total de mots ----------------------------------------------------------
    elif stat == "total_words":
        titre      = f"Total de mots écrits par {display_name}"
        total_mots = sum(msg.get("word_count", len(msg["content"].split())) for msg in messages)
        total_msgs = len(messages)
        desc       = f"**{total_mots:,}** mots écrits en **{total_msgs:,}** messages"

    # -- Message le plus long ---------------------------------------------------
    elif stat == "longest_msg":
        titre       = f"Message le plus long de {display_name}"
        plus_long   = max(messages, key=lambda m: len(m["content"]))
        date        = datetime.datetime.fromisoformat(plus_long["date"]).strftime("%d/%m/%Y")
        contenu     = plus_long["content"][:300] + ("..." if len(plus_long["content"]) > 300 else "")
        desc        = f"**{len(plus_long['content'])} caractères** — envoyé le {date}\n\n> {contenu}"

    # -- Premier message --------------------------------------------------------
    elif stat == "first_msg":
        titre    = f"Premier message de {display_name}"
        premier  = min(messages, key=lambda m: m["date"])
        date     = datetime.datetime.fromisoformat(premier["date"]).strftime("%d/%m/%Y à %Hh%M")
        channel  = discord.utils.get(bot.get_all_channels(), name=premier["channel"])
        chan_str = f"<#{channel.id}>" if channel else f"#{premier['channel']}"
        desc     = f"Envoyé le **{date}** dans {chan_str}\n\n> {premier['content'][:300]}"

    # -- Streak -----------------------------------------------------------------
    elif stat == "streak":
        titre = f"Streak de jours actifs de {display_name}"
        jours_actifs = sorted(set(
            datetime.datetime.fromisoformat(msg["date"]).date() for msg in messages
        ))
        if not jours_actifs:
            desc = "Aucun jour actif trouvé."
        else:
            max_streak     = 1
            current_streak = 1
            for i in range(1, len(jours_actifs)):
                if (jours_actifs[i] - jours_actifs[i - 1]).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1

            # streak actuel (depuis aujourd'hui)
            today          = datetime.date.today()
            streak_actuel  = 0
            for jour in reversed(jours_actifs):
                if (today - jour).days == streak_actuel:
                    streak_actuel += 1
                else:
                    break

            desc = f"Streak actuel : **{streak_actuel} jour{'s' if streak_actuel > 1 else ''}**\nMeilleur streak : **{max_streak} jour{'s' if max_streak > 1 else ''}**"

    else:
        embed = discord.Embed(title="Stat inconnue", color=0xff0000)
        return embed, None

    embed = discord.Embed(title=titre, description=desc, color=0xff0000)
    if file:
        embed.set_image(url="attachment://graph.png")
    return embed, file


def generate_hour_graph(toutes_les_heures):
    compteur = Counter(toutes_les_heures)
    heures   = list(range(24))
    counts   = [compteur.get(h, 0) for h in heures]

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
    return {}

def save_messages(messages):
    with open("messages.json", "w") as f:
        json.dump(messages, f, indent=4)


def setup_messagesStats(bot):
    stats_choix = ["-most_pop_world", "heure_moy", "most_pop_channel", "most_pop_day", "moy_length", "total_words", "longest_msg", "first_msg", "streak"]

    @bot.event
    async def on_message(message):
        if message.author.bot: return
        if message.content == "": return

        messages = load_messages()
        user_id  = str(message.author.id)

        if user_id not in messages:
            messages[user_id] = {"messages": []}

        messages[user_id]["messages"].append({
            "content":    message.content,
            "date":       message.created_at.isoformat(),
            "channel":    message.channel.name,
            "id":         message.id,
            "word_count": len(message.content.split()),
            "char_count": len(message.content),
            "weekday":    message.created_at.weekday()
        })

        save_messages(messages)

    async def messages_user_autocomplet(interaction: discord.Interaction, current: str):
        choix = [member.display_name for member in interaction.guild.members if not member.bot]
        return [discord.app_commands.Choice(name=c, value=c) for c in choix if current.lower() in c.lower()][:25]

    async def messages_stat_autocomplet(interaction: discord.Interaction, current: str):
        return [discord.app_commands.Choice(name=c, value=c) for c in stats_choix if current.lower() in c.lower()][:25]

    @bot.tree.command(name="mess_stats")
    @discord.app_commands.describe(user="Choisis un utilisateur", mess_stat="Choisis une stat")
    @discord.app_commands.autocomplete(user=messages_user_autocomplet, mess_stat=messages_stat_autocomplet)
    async def stats(interaction: discord.Interaction, user: str, mess_stat: str):
        await interaction.response.defer()
        member  = discord.utils.get(interaction.guild.members, display_name=user)
        user_id = str(member.id) if member else None

        if not user_id:
            await interaction.followup.send("Utilisateur introuvable.")
            return

        if mess_stat in stats_choix:
            messages        = load_messages()
            embed, file     = await getEmbed(bot, messages, mess_stat, user_id, user)
            view            = messStatView(bot, load_messages, user_id, user)
            if file: await interaction.followup.send(embed=embed, file=file, view=view)
            else:    await interaction.followup.send(embed=embed, view=view)