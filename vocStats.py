import datetime
import discord
import matplotlib.pyplot as plt
import io
from collections import Counter
from firebase_admin import firestore

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

class vocalStatView(discord.ui.View):
    def __init__(self, bot, load_stats, user_id, display_name):
        super().__init__(timeout=None)
        self.bot = bot
        self.load_stats = load_stats
        self.user_id = user_id
        self.display_name = display_name

    @discord.ui.select(
        placeholder="Choisir une stat...",
        options=[
            discord.SelectOption(label="Temps total",                   value="total_time"),
            discord.SelectOption(label="Salon le plus fréquenté",       value="most_pop_channel"),
            discord.SelectOption(label="Heure moyenne de co",           value="heure_moy"),
            discord.SelectOption(label="Durée moyenne d'une session",   value="moy_length"),
            discord.SelectOption(label="Nombre de sessions",            value="session_count"),
            discord.SelectOption(label="Jour le plus actif",            value="most_pop_day"),
            discord.SelectOption(label="Session la plus longue",        value="longest_session"),
            discord.SelectOption(label="Streak de jours",               value="streak"),
            discord.SelectOption(label="Historique des sessions",       value="history"),
        ]
    )
    async def select_stat(self, interaction: discord.Interaction, select: discord.ui.Select):
        choix = select.values[0]
        data  = self.load_stats()
        embed, file = await getEmbed(self.bot, data, choix, self.user_id, self.display_name)
        if file: await interaction.response.edit_message(embed=embed, attachments=[file])
        else:    await interaction.response.edit_message(embed=embed, attachments=[])


async def getEmbed(bot, data, stat, user_id, display_name):
    file    = None
    user_id = str(user_id)

    if user_id not in data or not data[user_id]["sessions"]:
        embed = discord.Embed(title="Aucune donnée", description="Pas de sessions vocales enregistrées.", color=0xff0000)
        return embed, None

    sessions = data[user_id]["sessions"]

    # -- Temps total ------------------------------------------------------------
    if stat == "total_time":
        titre        = f"Temps total en vocal de {display_name}"
        total        = sum(s["duration"] for s in sessions)
        heures       = total // 3600
        minutes      = (total % 3600) // 60
        secondes     = total % 60
        desc         = f"**{heures}h {minutes}m {secondes}s** passées en vocal"

    # -- Salon le plus fréquenté ------------------------------------------------
    elif stat == "most_pop_channel":
        titre    = f"Salon vocal le plus fréquenté par {display_name}"
        channels = [s["channel"] for s in sessions]
        compteur = Counter(channels)
        desc     = ""
        for channel_name, count in compteur.most_common():
            channel  = discord.utils.get(bot.get_all_channels(), name=channel_name)
            chan_str = f"<#{channel.id}>" if channel else f"#{channel_name}"
            duree    = sum(s["duration"] for s in sessions if s["channel"] == channel_name)
            h        = duree // 3600
            m        = (duree % 3600) // 60
            desc    += f"{chan_str} : **{count} sessions** ({h}h {m}m)\n"

    # -- Heure moyenne de connexion ---------------------------------------------
    elif stat == "heure_moy":
        titre              = f"Heure moyenne de connexion de {display_name}"
        toutes_les_minutes = []
        toutes_les_heures  = []
        for s in sessions:
            date = datetime.datetime.fromisoformat(s["joined_at"])
            toutes_les_minutes.append(date.hour * 60 + date.minute)
            toutes_les_heures.append(date.hour)
        moyenne = sum(toutes_les_minutes) / len(toutes_les_minutes)
        h       = int(moyenne) // 60
        m       = int(moyenne) % 60
        desc    = f"Se connecte en moyenne à **{h}h{m:02d}**"

        compteur = Counter(toutes_les_heures)
        heures   = list(range(24))
        counts   = [compteur.get(h, 0) for h in heures]
        plt.figure(figsize=(10, 4))
        plt.bar(heures, counts, color="royalblue")
        plt.xlabel("Heure")
        plt.ylabel("Sessions")
        plt.title("Connexions par heure")
        plt.xticks(heures)
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()
        file = discord.File(buf, filename="graph.png")

    # -- Durée moyenne d'une session --------------------------------------------
    elif stat == "moy_length":
        titre   = f"Durée moyenne d'une session de {display_name}"
        moyenne = sum(s["duration"] for s in sessions) / len(sessions)
        h       = int(moyenne) // 3600
        m       = int(moyenne % 3600) // 60
        s_      = int(moyenne % 60)
        desc    = f"En moyenne **{h}h {m}m {s_}s** par session"

    # -- Nombre de sessions -----------------------------------------------------
    elif stat == "session_count":
        titre = f"Nombre de sessions vok de {display_name}"
        total = sum(s["duration"] for s in sessions)
        h     = total // 3600
        m     = (total % 3600) // 60
        desc  = f"**{len(sessions)} sessions** pour un total de **{h}h {m}m**"

    # -- Jour le plus actif -----------------------------------------------------
    elif stat == "most_pop_day":
        titre    = f"Jour le plus actif en vocal de {display_name}"
        weekdays = [datetime.datetime.fromisoformat(s["joined_at"]).weekday() for s in sessions]
        compteur = Counter(weekdays)
        counts   = [compteur.get(d, 0) for d in range(7)]
        desc     = f"Jour le plus actif : **{JOURS[max(compteur, key=compteur.get)]}** avec **{max(compteur.values())} sessions**"

        plt.figure(figsize=(10, 4))
        plt.bar(JOURS, counts, color="royalblue")
        plt.xlabel("Jour")
        plt.ylabel("Sessions")
        plt.title("Activité vocale par jour")
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()
        file = discord.File(buf, filename="graph.png")

    # -- Session la plus longue -------------------------------------------------
    elif stat == "longest_session":
        titre   = f"Session la plus longue de {display_name}"
        longest = max(sessions, key=lambda s: s["duration"])
        date    = datetime.datetime.fromisoformat(longest["joined_at"]).strftime("%d/%m/%Y à %Hh%M")
        h       = longest["duration"] // 3600
        m       = (longest["duration"] % 3600) // 60
        s_      = longest["duration"] % 60
        channel = discord.utils.get(bot.get_all_channels(), name=longest["channel"])
        chan_str = f"<#{channel.id}>" if channel else f"#{longest['channel']}"
        desc    = f"**{h}h {m}m {s_}s** dans {chan_str}\nLe {date}"

    # -- Streak -----------------------------------------------------------------
    elif stat == "streak":
        titre        = f"Streak de jours actifs en vocal de {display_name}"
        jours_actifs = sorted(set(
            datetime.datetime.fromisoformat(s["joined_at"]).date() for s in sessions
        ))
        max_streak     = 1
        current_streak = 1
        for i in range(1, len(jours_actifs)):
            if (jours_actifs[i] - jours_actifs[i - 1]).days == 1:
                current_streak += 1
                max_streak      = max(max_streak, current_streak)
            else:
                current_streak  = 1

        today         = datetime.date.today()
        streak_actuel = 0
        for jour in reversed(jours_actifs):
            if (today - jour).days == streak_actuel:
                streak_actuel += 1
            else:
                break

        desc = f"Streak actuel : **{streak_actuel} jour{'s' if streak_actuel > 1 else ''}**\nMeilleur streak : **{max_streak} jour{'s' if max_streak > 1 else ''}**"

    # -- Historique -------------------------------------------------------------
    elif stat == "history":
        titre   = f"Dernières sessions de {display_name}"
        desc    = ""
        for s in reversed(sessions[-10:]):
            date    = datetime.datetime.fromisoformat(s["joined_at"]).strftime("%d/%m/%Y %Hh%M")
            h       = s["duration"] // 3600
            m       = (s["duration"] % 3600) // 60
            s_      = s["duration"] % 60
            channel = discord.utils.get(bot.get_all_channels(), name=s["channel"])
            chan_str = f"<#{channel.id}>" if channel else f"#{s['channel']}"
            desc   += f"`{date}`, {chan_str}, **{h}h {m}m {s_}s**\n"

    else:
        embed = discord.Embed(title="Stat inconnue", color=0xff0000)
        return embed, None

    embed = discord.Embed(title=titre, description=desc, color=0xff0000)
    if file:
        embed.set_image(url="attachment://graph.png")
    return embed, file


def setup_vocalStats(bot):
    db            = firestore.client()
    stats_choix   = ["total_time", "most_pop_channel", "heure_moy", "moy_length", "session_count", "most_pop_day", "longest_session", "streak", "history"]

    def load_vocal():
        docs = db.collection("vocal").stream()
        return {doc.id: doc.to_dict() for doc in docs}

    async def vocal_user_autocomplet(interaction: discord.Interaction, current: str):
        choix = [member.display_name for member in interaction.guild.members if not member.bot]
        return [discord.app_commands.Choice(name=c, value=c) for c in choix if current.lower() in c.lower()][:25]

    async def vocal_stat_autocomplet(interaction: discord.Interaction, current: str):
        return [discord.app_commands.Choice(name=c, value=c) for c in stats_choix if current.lower() in c.lower()][:25]

    @bot.tree.command(name="vocal_stats")
    @discord.app_commands.describe(user="Choisis un utilisateur", vocal_stat="Choisis une stat")
    @discord.app_commands.autocomplete(user=vocal_user_autocomplet, vocal_stat=vocal_stat_autocomplet)
    async def stats(interaction: discord.Interaction, user: str, vocal_stat: str):
        await interaction.response.defer()
        member  = discord.utils.get(interaction.guild.members, display_name=user)
        user_id = str(member.id) if member else None

        if not user_id:
            await interaction.followup.send("Utilisateur introuvable.")
            return

        if vocal_stat in stats_choix:
            data        = load_vocal()
            embed, file = await getEmbed(bot, data, vocal_stat, user_id, user)
            view        = vocalStatView(bot, load_vocal, user_id, user)
            if file: await interaction.followup.send(embed=embed, file=file, view=view)
            else:    await interaction.followup.send(embed=embed, view=view)


async def on_voice_state_update_vocStats(member, before, after):

    db = firestore.client()
    user_id = str(member.id)
    join_times = {}
    join_channels = {}

    def save_vocal_session(user_id, session):
        doc_ref  = db.collection("vocal").document(user_id)
        doc      = doc_ref.get()
        sessions = doc.to_dict().get("sessions", []) if doc.exists else []
        sessions.append(session)
        doc_ref.set({"sessions": sessions})

    # Connexion
    if before.channel is None and after.channel is not None:
        join_times[user_id]    = datetime.datetime.now()
        join_channels[user_id] = after.channel.name

    # Déconnexion
    elif after.channel is None and before.channel is not None:
        if user_id not in join_times:
            return

        duration = round((datetime.datetime.now() - join_times.pop(user_id)).total_seconds())
        channel  = join_channels.pop(user_id, before.channel.name)

        if duration < 3:
            return

        save_vocal_session(user_id, {
            "joined_at": datetime.datetime.now().isoformat(),
            "channel":   channel,
            "duration":  duration,
        })

    # Changement de salon
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        if user_id in join_times:
            duration = round((datetime.datetime.now() - join_times[user_id]).total_seconds())
            channel  = join_channels.get(user_id, before.channel.name)

            if duration >= 3:
                save_vocal_session(user_id, {
                    "joined_at": join_times[user_id].isoformat(),
                    "channel":   channel,
                    "duration":  duration,
                })

        join_times[user_id]    = datetime.datetime.now()
        join_channels[user_id] = after.channel.name