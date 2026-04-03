import discord
import json
import os
from datetime import datetime

class StatsView(discord.ui.View):
    def __init__(self, bot, load_stats):
        super().__init__(timeout=None)
        self.bot = bot
        self.load_stats = load_stats

    @discord.ui.select(
        placeholder="Choisir une stat...",
        options=[
            discord.SelectOption(label="Messages", value="message_count"),
            discord.SelectOption(label="Temps vocal", value="vocal_time"),
            discord.SelectOption(label="Reactions", value="reaction_count"),
        ]
    )
    async def select_stat(self, interaction: discord.Interaction, select: discord.ui.Select):
        choix = select.values[0]
        data = self.load_stats()

        embed = await getEmbed(self.bot, data, interaction.user.id, choix)

        await interaction.response.edit_message(embed=embed)


async def getEmbed(bot, data, author_id, stat):
    if stat == "message_count":
        titre = "Top 10 : Nombre de messages"
        clé = "message_count"
        unité = "messages"
    elif stat == "vocal_time":
        titre = "Top 10 : Temps en voc"
        clé = "vocal_time"
        unité = "s"
    elif stat == "reaction_count":
        titre = "Top 10 : Réactions"
        clé = "reaction_count"
        unité = "réactions"

    classement = sorted(data.items(), key=lambda x: x[1][clé], reverse=True)
    description = ""
    user_rank = None

    for i, (user_id, stats) in enumerate(classement):
        user = await bot.fetch_user(int(user_id))
        if i < 10:
            description += f"**{i+1}.** {user.name} : {stats[clé]} {unité}\n"
        if user_id == str(author_id):
            user_rank = (i+1, stats[clé])

    embed = discord.Embed(title=titre, description=description, color=0xff0000)

    if user_rank and user_rank[0] > 10:
        embed.set_footer(text=f"Ta position : #{user_rank[0]} — {user_rank[1]} {unité}")

    return embed

def setup_stats(bot):
    join_times = {}
    defauls_stats = {"message_count": 0, "vocal_time": 0, "reaction_count": 0}

    def get_user_data(data, user_id):
        if user_id not in data:
            data[user_id] = defauls_stats.copy()
        return data[user_id]

    def load_stats():
        if os.path.exists("stats.json"):
            with open("stats.json", "r") as f:
                return json.load(f)
        else:
            return {}

    def save_stats(data):
        with open("stats.json", "w") as f:
            json.dump(data, f, indent=4)

    @bot.event
    async def on_message(message):
        if message.author.bot: return

        data = load_stats()
        user_id = str(message.author.id)

        get_user_data(data, user_id)["message_count"] += 1
        save_stats(data)

    @bot.event
    async def on_voice_state_update(member, before, after):
        if member == bot.user: return
        data = load_stats()

        user_id = str(member.id)

        if before.channel == None:
            join_times[user_id] = datetime.now().isoformat()

        if after.channel == None:
            if join_times[user_id] is None:
                print(f"Temps non compté pour {member.name}")
                return

            now = datetime.now()

            join_time = datetime.fromisoformat(join_times[user_id])
            time_in_channel = now - join_time
            seconds = round(time_in_channel.total_seconds())

            get_user_data(data, user_id)["vocal_time"] += seconds

        save_stats(data)

    @bot.event
    async def on_reaction_add(reaction, user):
        if user.bot: return

        data = load_stats()
        user_id = str(user.id)

        get_user_data(data, user_id)["reaction_count"] += 1

        save_stats(data)

    @bot.event
    async def on_reaction_remove(reaction, user):
        if user.bot: return

        data = load_stats()
        user_id = str(user.id)

        if get_user_data(data, user_id)["reaction_count"] <= 0 : return
        get_user_data(data, user_id)["reaction_count"] -= 1

        save_stats(data)

    async def stats_autocomplet(interaction: discord.Interaction, current: str):
        choix = list(defauls_stats.keys())
        return [
            discord.app_commands.Choice(name=c, value=c)
            for c in choix if current.lower() in c.lower()
        ]

    @bot.tree.command(name="stats", description="affiche les stats")
    @discord.app_commands.describe(stat="Choisis la stat")
    @discord.app_commands.autocomplete(stat=stats_autocomplet)
    async def stats(interaction: discord.Interaction, stat: str):
        await interaction.response.defer()

        if stat in defauls_stats.keys():
            data = load_stats()
            embed = await getEmbed(bot, data, interaction.user.id, stat)
            await interaction.followup.send(embed=embed, view=StatsView(bot, load_stats))