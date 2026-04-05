import random

import discord
import yt_dlp
import asyncio


class MusicView(discord.ui.View):
    def __init__(self, voice_client, liste, info, guild_state):
        super().__init__(timeout=None)
        self.voice_client = voice_client
        self.liste = liste
        self.info = info
        self.guild_state = guild_state

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        await interaction.response.defer()
        self.voice_client.stop()

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.grey)
    async def pause(self, interaction, button):
        await interaction.response.defer()
        self.voice_client.pause()

    @discord.ui.button(label="Resume", style=discord.ButtonStyle.green)
    async def resume(self, interaction, button):
        await interaction.response.defer()
        self.voice_client.resume()

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction, button):
        await interaction.response.defer()

        guild_id = interaction.guild.id
        state = self.guild_state.get(guild_id)
        if state is None:
            return

        state["liste"].clear()
        state["text_channel"] = None
        state["is_playing"] = False
        state["is_blindtest"] = False

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            state["voice_client"] = None

        await interaction.followup.send("Je quitte le vocal !")

    @discord.ui.button(label="List", style=discord.ButtonStyle.red)
    async def list(self, interaction, button):
        await interaction.response.defer()
        await interaction.message.edit(embed=getEmbed(self.info, self.liste, True))

    @discord.ui.button(label="Shuffle", style=discord.ButtonStyle.red)
    async def shuffle(self, interaction, button):
        await interaction.response.defer()
        random.shuffle(self.liste)


class BlindTestView(discord.ui.View):
    def __init__(self, bon_titre, choix, info, liste, voice_client, guild_state):
        super().__init__(timeout=None)
        self.bon_titre = bon_titre
        self.termine = False
        self.info = info
        self.liste = liste
        self.voice_client = voice_client
        self.guild_state = guild_state

        for titre in choix:
            button = discord.ui.Button(label=titre, style=discord.ButtonStyle.grey)
            button.callback = self.make_callback(titre)
            self.add_item(button)

        stop_button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.danger)
        stop_button.callback = self.stop_callback
        self.add_item(stop_button)

    def make_callback(self, auteur):
        async def callback(interaction):
            if self.termine:
                return
            self.termine = True

            if auteur == self.bon_titre:
                await interaction.response.send_message(f"Bravo, c'était éfféctivement {self.bon_titre} !")
            else:
                await interaction.response.send_message(f"Faux, C'était {self.bon_titre} !")

            await interaction.channel.send(
                embed=getEmbed(self.info, self.liste),
                view=MusicView(self.voice_client, self.liste, self.info, self.guild_state)
            )
        return callback

    async def stop_callback(self, interaction):
        await interaction.response.defer()

        guild_id = interaction.guild.id
        state = self.guild_state.get(guild_id)
        if state is None:
            return

        state["liste"].clear()
        state["text_channel"] = None
        state["is_playing"] = False
        state["is_blindtest"] = False

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            state["voice_client"] = None

        await interaction.followup.send("Blindtest arrêté, je quitte le vocal !")


def getEmbed(info, liste, on_seeing=False):
    description = info['title']

    if on_seeing:
        if liste:
            lines = [f"**En cours :** {info['title']}", ""]
            for i, entry in enumerate(liste, start=1):
                lines.append(f"{i}. {entry['title']}")
            description = "\n".join(lines)
        else:
            description = f"**En cours :** {info['title']}\n\n*Pas de file d'attente*"

    embed = discord.Embed(
        title="Je joue actuellement :",
        description=description,
        color=0xff0000
    )

    duration = info.get('duration')
    if duration is not None:
        minutes = duration // 60
        secondes = duration % 60
        duration_str = f"{minutes}min{secondes:02d}s"
    else:
        duration_str = "Live / Inconnue"

    embed.set_thumbnail(url=info.get('thumbnail', ''))
    embed.add_field(name="Duration", value=duration_str, inline=True)
    embed.add_field(name="Queue", value=len(liste), inline=True)

    return embed


def setup_YoutubeAudio(bot):

    guild_states = {}

    def get_state(guild_id):
        if guild_id not in guild_states:
            guild_states[guild_id] = {
                "liste": [],
                "voice_client": None,
                "is_playing": False,
                "is_blindtest": False,
                "text_channel": None,
            }
        return guild_states[guild_id]

    async def play_next(guild_id):
        state = get_state(guild_id)
        voice_client = state["voice_client"]

        if not voice_client or not voice_client.is_connected():
            state["is_playing"] = False
            return

        if not state["liste"]:
            state["is_playing"] = False
            state["is_blindtest"] = False
            await voice_client.disconnect()
            state["voice_client"] = None
            return

        info = state["liste"].pop(0)
        url = info['url']

        before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        ffmpeg_options = "-vn"

        source = discord.FFmpegPCMAudio(url, before_options=before_options, options=ffmpeg_options)

        def after_playing(error):
            asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)

        voice_client.play(source, after=after_playing)
        state["is_playing"] = True

        text_channel = state["text_channel"]
        if text_channel:
            if state["is_blindtest"]:
                embed = discord.Embed(
                    title="Je joue actuellement :",
                    description="???",
                    color=0xff0000
                )
                embed.set_thumbnail(url="https://tse1.mm.bing.net/th/id/OIP.1O5Rh45dLmxoBTxS1_Sg2gHaFm?pid=Api")
                embed.add_field(name="Duration", value="???", inline=True)
                embed.add_field(name="Queue", value=len(state["liste"]), inline=True)

                autres_titres = [e['title'] for e in state["liste"] if e['title'] != info['title']]
                faux = random.sample(autres_titres, min(2, len(autres_titres)))
                choix = faux + [info['title']]

                while len(choix) < 2:
                    choix.append("Inconnu")
                random.shuffle(choix)

                await text_channel.send(
                    embed=embed,
                    view=BlindTestView(info['title'], choix, info, state["liste"], voice_client, guild_states)
                )
            else:
                await text_channel.send(
                    embed=getEmbed(info, state["liste"]),
                    view=MusicView(voice_client, state["liste"], info, guild_states)
                )

    @bot.tree.command(name="play", description="Lance l'audio d'une vidéo YouTube")
    async def cmd_play(interaction: discord.Interaction, lien: str):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Tu dois être dans un salon vocal.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        state = get_state(guild_id)

        options = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'cookiefile': '/home/Le-best-des-flash-mcqueen/cookies.txt',
            'extractor_args': {
                'youtube': {
                    'po_token': ['web+Mng2bvbp5vtuiTZSQxzIcvCzox_KU0nnS24xXk8J6Qt4_H1t7oPM98DIhudjz1MuokmihdPiYXv2b997Ek-gSoAfdjXz6uThWbUl51qr5FIoxmHc8WMi7MMWxveW_SfTEk3kbt9GIJOvim0h6g1gUsJ0CxcVoJ9M31E='],
                    'visitor_data': ['CgszSGk4SlNhVUs3TSj44svOBjIKCgJVUxIEGgAgFg%3D%3D'],
                }
            },
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, lien, False)

        if state["is_playing"]:
            state["liste"].append(info)
            await interaction.followup.send(f"Ajouté à la file d'attente : {info['title']}")
            return

        vocal_channel = interaction.user.voice.channel
        state["text_channel"] = interaction.channel

        if interaction.guild.voice_client:
            state["voice_client"] = interaction.guild.voice_client
        else:
            state["voice_client"] = await vocal_channel.connect()

        state["liste"].append(info)
        await play_next(guild_id)
        await interaction.followup.send(f"Je joue : {info['title']}")

    @bot.tree.command(name="playlist", description="Lance une playlist YouTube")
    async def cmd_playlist(interaction: discord.Interaction, lien: str):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Tu dois être dans un salon vocal.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        state = get_state(guild_id)

        options = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'cookiefile': '/home/Le-best-des-flash-mcqueen/cookies.txt',
            'extractor_args': {
                'youtube': {
                    'po_token': ['web+Mng2bvbp5vtuiTZSQxzIcvCzox_KU0nnS24xXk8J6Qt4_H1t7oPM98DIhudjz1MuokmihdPiYXv2b997Ek-gSoAfdjXz6uThWbUl51qr5FIoxmHc8WMi7MMWxveW_SfTEk3kbt9GIJOvim0h6g1gUsJ0CxcVoJ9M31E='],
                    'visitor_data': ['CgszSGk4SlNhVUs3TSj44svOBjIKCgJVUxIEGgAgFg%3D%3D'],
                }
            },
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, lien, False)

        if state["is_playing"]:
            if 'entries' in info:
                for entry in info['entries']:
                    if entry is not None:
                        state["liste"].append(entry)
                await interaction.followup.send(f"Playlist ajouté à la file d'attente")
            else:
                state["liste"].append(info)
                await interaction.followup.send(f"Ajouté à la file d'attente : {info['title']}")
            return

        vocal_channel = interaction.user.voice.channel
        state["text_channel"] = interaction.channel

        if interaction.guild.voice_client:
            state["voice_client"] = interaction.guild.voice_client
        else:
            state["voice_client"] = await vocal_channel.connect()

        if 'entries' in info:
            for entry in info['entries']:
                if entry is not None:
                    state["liste"].append(entry)
            await interaction.followup.send(f"Je joue la playlist")
        else:
            state["liste"].append(info)
            await interaction.followup.send(f"Je joue : {info['title']}")

        await play_next(guild_id)

    @bot.tree.command(name="blindtest", description="Lance un blindtest depuis une playlist YouTube")
    async def cmd_blindtest(interaction: discord.Interaction, lien: str):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Tu dois être dans un salon vocal.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        state = get_state(guild_id)

        options = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'cookiefile': '/home/Le-best-des-flash-mcqueen/cookies.txt',
            'extractor_args': {
                'youtube': {
                    'po_token': ['web+Mng2bvbp5vtuiTZSQxzIcvCzox_KU0nnS24xXk8J6Qt4_H1t7oPM98DIhudjz1MuokmihdPiYXv2b997Ek-gSoAfdjXz6uThWbUl51qr5FIoxmHc8WMi7MMWxveW_SfTEk3kbt9GIJOvim0h6g1gUsJ0CxcVoJ9M31E='],
                    'visitor_data': ['CgszSGk4SlNhVUs3TSj44svOBjIKCgJVUxIEGgAgFg%3D%3D'],
                }
            },
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, lien, False)

        if 'entries' not in info:
            await interaction.followup.send("Le liens doit être celui d'une playlist.")
            return

        state["liste"].clear()
        state["is_blindtest"] = True
        for entry in info['entries']:
            if entry is not None:
                state["liste"].append(entry)
        random.shuffle(state["liste"])

        if state["is_playing"]:
            await interaction.followup.send("Playlist ajouté à la file d'attente")
            return

        vocal_channel = interaction.user.voice.channel
        state["text_channel"] = interaction.channel

        if interaction.guild.voice_client:
            state["voice_client"] = interaction.guild.voice_client
        else:
            state["voice_client"] = await vocal_channel.connect()

        await interaction.followup.send("Playlist ajouté à la file d'attente")
        await play_next(guild_id)

    @bot.tree.command(name="degage", description="Le bot quitte le salon vocal")
    async def degage(interaction: discord.Interaction):
        guild_id = interaction.guild.id
        state = get_state(guild_id)

        if interaction.guild.voice_client:
            state["liste"].clear()
            state["text_channel"] = None
            state["is_playing"] = False
            state["is_blindtest"] = False
            state["voice_client"] = None
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Je quitte le vocal !")
        else:
            await interaction.response.send_message("Je ne suis pas en vocal.", ephemeral=True)