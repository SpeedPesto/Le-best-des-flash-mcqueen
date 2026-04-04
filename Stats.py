import discord
from datetime import datetime
from itertools import combinations
from firebase_admin import firestore

class StatsView(discord.ui.View):
    def __init__(self, bot, load_stats):
        super().__init__(timeout=None)
        self.bot = bot
        self.load_stats = load_stats

    @discord.ui.select(
        placeholder="Choisir une stat...",
        options=[
            discord.SelectOption(label="Nombre de message",             value="message_count"),
            discord.SelectOption(label="Temps vocal",                   value="vocal_time"),
            discord.SelectOption(label="Reactions",                     value="reaction_count"),
            discord.SelectOption(label="Duo le plus ensemble",          value="top_duo"),
            discord.SelectOption(label="Trio le plus ensemble",         value="top_trio"),
            discord.SelectOption(label="Salon vocal le plus utilisé",   value="top_vocal_channel"),
            discord.SelectOption(label="Heure la plus active",          value="top_hour"),
            discord.SelectOption(label="Jour le plus actif",            value="top_day"),
        ]
    )
    async def select_stat(self, interaction: discord.Interaction, select: discord.ui.Select):
        choix = select.values[0]
        data  = self.load_stats()
        embed = await getEmbed(self.bot, data, interaction.user.id, choix)
        await interaction.response.edit_message(embed=embed)


JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

async def getEmbed(bot, data, author_id, stat):

    # -- Stats par personne (classement) ---------------------------------------
    if stat in ("message_count", "vocal_time", "reaction_count"):
        if stat == "message_count":
            titre, clé, unité = "Top 10 : Nombre de messages", "message_count", "messages"
        elif stat == "vocal_time":
            titre, clé, unité = "Top 10 : Temps en vok", "vocal_time", "s"
        elif stat == "reaction_count":
            titre, clé, unité = "Top 10 : Réactions", "reaction_count", "réactions"

        classement  = sorted(data.get("users", {}).items(), key=lambda x: x[1].get(clé, 0), reverse=True)
        description = ""
        user_rank   = None

        for i, (user_id, stats) in enumerate(classement):
            user = await bot.fetch_user(int(user_id))
            if i < 10:
                description += f"**{i+1}.** {user.name} : {stats.get(clé, 0)} {unité}\n"
            if user_id == str(author_id):
                user_rank = (i + 1, stats.get(clé, 0))

        embed = discord.Embed(title=titre, description=description, color=0xff0000)
        if user_rank and user_rank[0] > 10:
            embed.set_footer(text=f"Ta position : #{user_rank[0]} — {user_rank[1]} {unité}")
        return embed

    server = data.get("server", {})

    # -- Duo le plus ensemble ---------------------------------------------------
    if stat == "top_duo":
        duos = server.get("duos", {})
        if not duos:
            return discord.Embed(title="Duo le plus ensemble", description="Pas encore de données.", color=0xff0000)

        top         = sorted(duos.items(), key=lambda x: x[1], reverse=True)[:5]
        description = ""
        for i, (pair, seconds) in enumerate(top):
            ids  = pair.split("_")
            u1   = await bot.fetch_user(int(ids[0]))
            u2   = await bot.fetch_user(int(ids[1]))
            h, m = seconds // 3600, (seconds % 3600) // 60
            description += f"**{i+1}.** {u1.name} & {u2.name} — **{h}h {m}m**\n"

        return discord.Embed(title="Duo les plus ensemble", description=description, color=0xff0000)

    # -- Trio le plus ensemble --------------------------------------------------
    if stat == "top_trio":
        trios = server.get("trios", {})
        if not trios:
            return discord.Embed(title="Trio le plus ensemble", description="Pas encore de données.", color=0xff0000)

        top         = sorted(trios.items(), key=lambda x: x[1], reverse=True)[:5]
        description = ""
        for i, (trio, seconds) in enumerate(top):
            ids   = trio.split("_")
            users = [await bot.fetch_user(int(uid)) for uid in ids]
            h, m  = seconds // 3600, (seconds % 3600) // 60
            description += f"**{i+1}.** {' & '.join(u.name for u in users)} — **{h}h {m}m**\n"

        return discord.Embed(title="Trios les plus ensemble", description=description, color=0xff0000)

    # -- Salon vocal le plus utilisé --------------------------------------------
    if stat == "top_vocal_channel":
        channels = server.get("vocal_channels", {})
        if not channels:
            return discord.Embed(title="Salons vocaux", description="Pas encore de données.", color=0xff0000)

        top         = sorted(channels.items(), key=lambda x: x[1], reverse=True)[:10]
        description = ""
        for i, (channel_name, seconds) in enumerate(top):
            channel  = discord.utils.get(bot.get_all_channels(), name=channel_name)
            chan_str  = f"<#{channel.id}>" if channel else f"#{channel_name}"
            h, m     = seconds // 3600, (seconds % 3600) // 60
            description += f"**{i+1}.** {chan_str} — **{h}h {m}m**\n"

        return discord.Embed(title="Salons vocaux les plus utilisés", description=description, color=0xff0000)

    # -- Heure la plus active ---------------------------------------------------
    if stat == "top_hour":
        hours = server.get("message_hours", {})
        if not hours:
            return discord.Embed(title="Heure la plus active", description="Pas encore de données.", color=0xff0000)

        top_hour    = max(hours, key=lambda h: hours[h])
        total       = sum(hours.values())
        description = f"Heure la plus active : **{top_hour}h** avec **{hours[top_hour]} messages**\nTotal : **{total} messages**"

        top5 = sorted(hours.items(), key=lambda x: x[1], reverse=True)[:5]
        description += "\n\n**Top 5 heures :**\n"
        for h, count in top5:
            description += f"**{h}h** — {count} messages\n"

        return discord.Embed(title="Heure la plus active du serveur", description=description, color=0xff0000)

    # -- Jour le plus actif -----------------------------------------------------
    if stat == "top_day":
        days = server.get("message_days", {})
        if not days:
            return discord.Embed(title="Jour le plus actif", description="Pas encore de données.", color=0xff0000)

        top_day     = max(days, key=lambda d: days[d])
        description = f"Jour le plus actif : **{JOURS[int(top_day)]}** avec **{days[top_day]} messages**\n\n"

        for d in range(7):
            count        = days.get(str(d), 0)
            description += f"**{JOURS[d]}** — {count} messages\n"

        return discord.Embed(title="Jours les plus actifs du serveur", description=description, color=0xff0000)

    return discord.Embed(title="Stat inconnue", color=0xff0000)

db = firestore.client()
default_user_stats = {"message_count": 0, "vocal_time": 0, "reaction_count": 0}
def get_user_data(data, user_id):
    if "users" not in data:
        data["users"] = {}
    if user_id not in data["users"]:
        data["users"][user_id] = default_user_stats.copy()
    return data["users"][user_id]

def get_server_data(data):
    if "server" not in data:
        data["server"] = {"duos": {}, "trios": {}, "vocal_channels": {}, "message_hours": {}, "message_days": {}}
    return data["server"]

def load_stats():
    data = {}

    users_docs = db.collection("stats").document("users").collection("data").stream()
    data["users"] = {doc.id: doc.to_dict() for doc in users_docs}

    server_doc = db.collection("stats").document("server").get()
    data["server"] = server_doc.to_dict() if server_doc.exists else {}

    return data

def save_stats(data):
    if "users" in data:
        for user_id, stats in data["users"].items():
            db.collection("stats").document("users").collection("data").document(user_id).set(stats)

    if "server" in data:
        db.collection("stats").document("server").set(data["server"])

def setup_stats(bot):
    channel_users = {}

    def flush_channel(data, channel_id, leaving_user_id=None):
        if channel_id not in channel_users or not channel_users[channel_id]:
            return

        now     = datetime.now()
        present = channel_users[channel_id]
        server  = get_server_data(data)

        for uid, join_dt in present.items():
            seconds = round((now - join_dt).total_seconds())
            if seconds < 5: continue
            get_user_data(data, uid)["vocal_time"] += seconds

        channel_obj = bot.get_channel(channel_id)
        if channel_obj:
            name = channel_obj.name
            server["vocal_channels"][name] = server["vocal_channels"].get(name, 0) + max(
                round((now - min(present.values())).total_seconds()), 0
            )

        user_ids = list(present.keys())
        for pair in combinations(sorted(user_ids), 2):
            key     = "_".join(pair)
            seconds = round((now - max(present[pair[0]], present[pair[1]])).total_seconds())
            if seconds >= 5:
                server["duos"][key] = server["duos"].get(key, 0) + seconds

        for trio in combinations(sorted(user_ids), 3):
            key     = "_".join(trio)
            seconds = round((now - max(present[u] for u in trio)).total_seconds())
            if seconds >= 5:
                server["trios"][key] = server["trios"].get(key, 0) + seconds

        for uid in list(present.keys()):
            if uid != leaving_user_id:
                channel_users[channel_id][uid] = now
        if leaving_user_id and leaving_user_id in channel_users[channel_id]:
            del channel_users[channel_id][leaving_user_id]

    @bot.event
    async def on_voice_state_update(member, before, after):
        if member == bot.user: return

        user_id = str(member.id)
        data    = load_stats()

        if before.channel is not None:
            flush_channel(data, before.channel.id, leaving_user_id=user_id if after.channel != before.channel else None)

        if after.channel is not None:
            if after.channel.id not in channel_users:
                channel_users[after.channel.id] = {}
            channel_users[after.channel.id][user_id] = datetime.now()

        save_stats(data)

    @bot.event
    async def on_reaction_add(reaction, user):
        if user.bot: return
        data    = load_stats()
        user_id = str(user.id)
        get_user_data(data, user_id)["reaction_count"] += 1
        save_stats(data)

    @bot.event
    async def on_reaction_remove(reaction, user):
        if user.bot: return
        data    = load_stats()
        user_id = str(user.id)
        if get_user_data(data, user_id)["reaction_count"] <= 0: return
        get_user_data(data, user_id)["reaction_count"] -= 1
        save_stats(data)

    async def stats_autocomplet(interaction: discord.Interaction, current: str):
        choix = ["message_count", "vocal_time", "reaction_count", "top_duo", "top_trio", "top_vocal_channel", "top_hour", "top_day"]
        return [discord.app_commands.Choice(name=c, value=c) for c in choix if current.lower() in c.lower()]

    @bot.tree.command(name="stats", description="affiche les stats")
    @discord.app_commands.describe(stat="Choisis la stat")
    @discord.app_commands.autocomplete(stat=stats_autocomplet)
    async def stats(interaction: discord.Interaction, stat: str):
        await interaction.response.defer()
        data  = load_stats()
        embed = await getEmbed(bot, data, interaction.user.id, stat)
        await interaction.followup.send(embed=embed, view=StatsView(bot, load_stats))

async def handle_stats_message(message):
    data = load_stats()
    user_id = str(message.author.id)
    server = get_server_data(data)

    get_user_data(data, user_id)["message_count"] += 1
    print(f"[STATS] user {user_id} → message_count = {data['users'][user_id]['message_count']}")

    hour = str(message.created_at.hour)
    day = str(message.created_at.weekday())
    server["message_hours"][hour] = server["message_hours"].get(hour, 0) + 1
    server["message_days"][day] = server["message_days"].get(day, 0) + 1

    save_stats(data)
    print(f"[STATS] save_stats terminé")