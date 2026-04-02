import random

import discord
import yt_dlp
import asyncio

class MusicView(discord.ui.View):
    def __init__(self, voice_client):
        super().__init__(timeout=None)
        self.voice_client = voice_client

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

class blindTestView(discord.ui.View):
    def __init__(self, bon_titre, choix, info, liste, voice_client):
        super().__init__(timeout=None)
        self.bon_titre = bon_titre
        self.termine = False
        self.info = info
        self.liste = liste
        self.voice_client = voice_client

        for titre in choix:
            button = discord.ui.Button(label=titre, style=discord.ButtonStyle.grey)
            button.callback = self.make_callback(titre)
            self.add_item(button)

    def make_callback(self, auteur):
        async def callback(interaction):
            if self.termine:
                return
            self.termine = True

            if auteur == self.bon_titre:
                await interaction.response.send_message(f"Bravo, c'était éfféctivement {self.bon_titre} !")
            else:
                await interaction.response.send_message(f"Faux, C'était {self.bon_titre} !")

            await interaction.channel.send(embed=getEmbed(self.info, self.liste), view=MusicView(self.voice_client))
        return callback

def getEmbed(info, liste):
    embed = discord.Embed(
        title="Je joue actuellement :",
        description=info['title'],
        color=0xff0000
    )

    minutes = info['duration'] // 60
    secondes = info['duration'] % 60
    duration = f"{minutes}min{secondes}s"

    embed.set_thumbnail(url=info['thumbnail'])
    embed.add_field(name="Duration", value=duration, inline=True)
    embed.add_field(name="Queue", value=len(liste), inline=True)

    return embed


def setup_YoutubeAudio(bot):

    liste = []
    voice_client = None
    isOnPlaying = False
    is_blindtest = False
    text_channel = None

    async def play_next():
        nonlocal isOnPlaying, voice_client, text_channel

        if not voice_client or not voice_client.is_connected():
            return

        if not liste:
            isOnPlaying = False
            await voice_client.disconnect()
            return

        info = liste.pop(0)
        url = info['url']

        before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        ffmpeg_options = "-vn"

        source = discord.FFmpegPCMAudio(url, before_options=before_options, options=ffmpeg_options)

        def after_playing(error):
            fut = asyncio.run_coroutine_threadsafe(play_next(), bot.loop)
            fut.result()

        voice_client.play(source, after=after_playing)
        isOnPlaying = True

        if text_channel:
            if is_blindtest :
                embed = discord.Embed(
                    title="Je joue actuellement :",
                    description="???",
                    color=0xff0000
                )

                embed.set_thumbnail(url="https://tse1.mm.bing.net/th/id/OIP.1O5Rh45dLmxoBTxS1_Sg2gHaFm?pid=Api")
                embed.add_field(name="Duration", value="???", inline=True)
                embed.add_field(name="Queue", value=len(liste), inline=True)

                faux = random.sample([e['title'] for e in liste], min(2, len(liste)))
                choix = faux + [info['title']]
                random.shuffle(choix)
                await text_channel.send(embed=embed, view=blindTestView(info['title'], choix, info, liste, voice_client))
            else :
                await text_channel.send(embed=getEmbed(info, liste), view=MusicView(voice_client))

    @bot.tree.command(name="play", description="lance l'audio de la vidéo")
    async def play(interaction: discord.Interaction, lien: str):
        nonlocal voice_client, isOnPlaying, text_channel
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Tu dois être dans un salon vocal.", ephmeral=True)
            return

        options = {
            'format': 'bestaudio',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(lien, download=False)

        if isOnPlaying:
            liste.append(info)
            await interaction.followup.send(f"Ajouté à la file d'attente : {info['title']}")
            return

        vocal_channel = interaction.user.voice.channel
        text_channel = interaction.channel

        if interaction.guild.voice_client:
            voice_client = interaction.guild.voice_client
        else:
            voice_client = await vocal_channel.connect()

        liste.append(info)
        await play_next()
        await interaction.followup.send(f"Je joue : {info['title']}")

    @bot.tree.command(name="playlist")
    async def play(interaction: discord.Interaction, lien: str):
        nonlocal voice_client, isOnPlaying, text_channel
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Tu dois être dans un salon vocal.", ephmeral=True)
            return

        options = {
            'format': 'bestaudio',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(lien, download=False)

        if isOnPlaying:
            if 'entries' in info:
                for entry in info['entries']:
                    if entry is not None:
                        liste.append(entry)
                await interaction.followup.send(f"Playlist ajouté à la file d'attente")
            else:
                liste.append(info)
                await interaction.followup.send(f"Ajouté à la file d'attente : {info['title']}")
            return

        vocal_channel = interaction.user.voice.channel
        text_channel = interaction.channel

        if interaction.guild.voice_client:
            voice_client = interaction.guild.voice_client
        else:
            voice_client = await vocal_channel.connect()

        if 'entries' in info:
            for entry in info['entries']:
                if entry is not None:
                    liste.append(entry)
            await interaction.followup.send(f"Je joue la playlist")
        else:
            liste.append(info)

        await play_next()

    @bot.tree.command(name="blindtest")
    async def play(interaction: discord.Interaction, lien: str):
        nonlocal voice_client, isOnPlaying, text_channel, is_blindtest
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Tu dois être dans un salon vocal.", ephmeral=True)
            return

        options = {
            'format': 'bestaudio',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(lien, download=False)

        if isOnPlaying:
            liste.clear()
            if 'entries' in info:
                is_blindtest = True
                for entry in info['entries']:
                    if entry is not None:
                        liste.append(entry)
                random.shuffle(liste)
                await interaction.followup.send(f"Playlist ajouté à la file d'attente")
            else:
                await interaction.followup.send(f"Le liens doit être celui d'une playlist")
            return

        vocal_channel = interaction.user.voice.channel
        text_channel = interaction.channel

        if interaction.guild.voice_client:
            voice_client = interaction.guild.voice_client
        else:
            voice_client = await vocal_channel.connect()

        if 'entries' in info:
            is_blindtest = True
            for entry in info['entries']:
                if entry is not None:
                    liste.append(entry)
            random.shuffle(liste)
            await interaction.followup.send(f"Playlist ajouté à la file d'attente")
        else:
            await interaction.followup.send(f"Le liens doit être celui d'une playlist")

        await play_next()

    @bot.tree.command(name="degage", description="Le bot quitte le salon vocal")
    async def degage(interaction: discord.Interaction):
        nonlocal isOnPlaying, voice_client, text_channel

        if interaction.guild.voice_client:
            liste.clear()
            text_channel = None
            isOnPlaying = False
            voice_client = None
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Je quitte le vocal !")
        else:
            await interaction.response.send_message("Je ne suis pas en vocal.", ephemeral=True)