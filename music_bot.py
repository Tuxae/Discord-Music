import asyncio

import discord
import youtube_dl

from discord.ext import commands

from my_constants import TOKEN, DEFAULT_CHANNEL
from playlist import Playlist

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.radio = False

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Se connecter au channel donné en argument. Rejoins le channel général sinon."""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, query):
        """Joue un fichier en local, présent sur le disque dur"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """Joue à partir d'une URL (tout ce que youtube_dl supporte)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Maintenant, dans vos douces oreilles: {}'.format(player.title))

    @commands.command()
    async def radio(self, ctx, *, mode):
        """Active le mode radio."""

        self.radio = mode

        playlist = Playlist()
        while(self.radio):
            for url in playlist.get_urls():
                async with ctx.typing():
                    player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                    #print(player.data)
                    ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
                    await ctx.send('{} - {} '.format(player.data['uploader'], player.data['title']))
                # Sleep 1 second
                await asyncio.sleep(player.data['duration'] + 1) 


    @commands.command()
    async def stream(self, ctx, *, url):
        """Comme la fonction yt, mais il ne télécharge pas la musique en local"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('{} - {} '.format(player.uploader, player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Change le volume sonore"""

        if ctx.voice_client is None:
            return await ctx.send("Pour changer le volume, il faudrait déjà que je sois connecté sur un channel vocal !")

        if volume > 150:
            return await ctx.send("Tu veux qu'on devienne sourd ?")
        
        if volume < 0:
            return await ctx.send("Un volume dans le négatif. On aura tout vu...")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Volume reglé sur {}%".format(volume))
    
    @commands.command()
    async def pause(self, ctx):
        """Met en pause la musique"""

        ctx.voice_client.pause()

    @commands.command()
    async def resume(self, ctx):
        """Relance la musique"""

        ctx.voice_client.resume()
    
    @commands.command()
    async def stop(self, ctx):
        """Arrête la musique"""

        ctx.voice_client.stop()

    @commands.command()
    async def disconnect(self, ctx):
        """Se déconnecte du channel vocal"""

        await ctx.voice_client.disconnect()

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"),
        description="DJ Botlavoine pour vous servir :-)")

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')
    channel = bot.get_channel(DEFAULT_CHANNEL)
    await channel.connect()

bot.add_cog(Music(bot))
bot.run(TOKEN)
