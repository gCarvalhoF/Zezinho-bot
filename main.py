import discord
from time import sleep
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import youtube_dl
import asyncio

load_dotenv()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=";", intents=intents)


music_path = './music.mp3'

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
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
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

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print(
            f'Player error: {e}') if e else None)

        await ctx.send(f'Now playing: {query}')

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(
                f'Player error: {e}') if e else None)

        await ctx.send(f'Now playing: {player.title}')

    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(
                f'Player error: {e}') if e else None)

        await ctx.send(f'Now playing: {player.title}')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

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
                raise commands.CommandError(
                    "Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


def register_channel(message):
    with open('db.txt', 'r') as f:
        index = 0
        for line in f:
            index += 1
            if str(message.guild.id) in line or str(message.channel.id) in line:
                break

        content = line
        content = content.split(":")

        request_channel_id = content[1].split("\\")
        request_channel_id = int(request_channel_id[0])
        return request_channel_id


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


def is_spam(message):
    full_of_spaces = re.compile(r'(.*)(\s{5})(.*)', re.IGNORECASE)
    repeating_the_same_word = re.compile(
        r'\b(\w+)\n\1\b', re.IGNORECASE)
    is_full_of_spaces = re.search(
        full_of_spaces, message.content)
    is_repeating_the_same_word = re.search(
        repeating_the_same_word, message.content)

    is_spam = True if is_full_of_spaces or is_repeating_the_same_word else False

    return is_spam


@bot.event
async def on_guild_join(guild):
    global request_channel_id

    await guild.create_text_channel('requests', position=0, topic='Vardux baitola', reason='Channel to be used to request songs | Canal para colocar pedidos de músicas')

    channels = guild.channels
    request_channel_id = None

    for c in channels:
        if c.name == 'requests':
            request_channel_id = c.id

    with open('db.txt', 'a') as f:
        f.write(
            f'Id do canal de request servidor {guild.id}:{request_channel_id} \n')


@bot.command()
async def connect(ctx):
    voice_client = ctx.author.voice.channel
    return await voice_client.connect()


@bot.command()
async def disconnect(ctx):
    voice_clients = bot.voice_clients
    for voice_client in voice_clients:
        if voice_client.guild == ctx.guild:
            return await voice_client.disconnect()


@bot.event
async def on_message(message):
    if is_spam(message):
        await message.delete()

    request_channel_id = register_channel(message)

    if message.author.id != bot.user.id:
        bot_member = await message.guild.fetch_member(bot.user.id)
        if message.channel.id == request_channel_id:

            try:
                voice_client = await connect(message)
                await bot_member.edit(deafen=True)

            except discord.errors.ClientException:
                members_on_channel = bot_member.voice.channel.members

                if len(members_on_channel) > 1 and message.author.voice.channel != bot_member.voice.channel:
                    await message.channel.send(
                        content='Eu já estou sendo usado em outra chamada, entre nela para ouvir junto com os outros :)')
                elif len(members_on_channel) == 1:
                    voice_client = message.guild.voice_client
                    await disconnect(message)
                    await connect(message)
                    await bot_member.edit(deafen=True)
            finally:
                voice_client.play(discord.FFmpegPCMAudio(
                    executable="C:/ffmpeg/bin/ffmpeg.exe", source=music_path))

    await bot.process_commands(message)


@bot.command()
async def tempban(ctx, member, time=10):
    split = member.split('@!')
    member = ctx.guild.get_member(int(split[1][:-1]))
    tempban_role = discord.utils.get(ctx.guild.roles, name="tempban")

    if member.top_role.permissions.administrator:
        return

    if discord.utils.get(ctx.guild.roles, name="tempban") not in ctx.guild.roles:
        await ctx.guild.create_role(
            name='tempban', permissions=discord.Permissions(send_messages=False))

    roles = {}
    roles[f'{member}'] = []

    for role in member.roles:
        if 'everyone' in role.name:
            continue

        roles[f'{member}'].append(role)
        await member.remove_roles(role)

    await member.add_roles(tempban_role)

    sleep(int(time))
    await member.remove_roles(tempban_role)
    for role in roles[f'{member}']:
        await member.add_roles(role)


bot.add_cog(Music(bot))
bot.run(os.getenv('TOKEN'))
