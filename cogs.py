import discord
from discord.ext import commands
from dicio import Dicio
import urllib.request
import json
import wikipedia
from translate import Translator
import youtube_dl
import asyncio

wikipedia.set_lang("pt")


def get_meaning(word):
    word_search = Dicio().search(word)

    try:
        meanings = word_search.meaning
    except AttributeError:
        return [None, None]

    if ";" in meanings:
        meanings = meanings.split(";")
        meanings = "\n".join(meanings)

    return meanings, word_search.url


def get_synonyms(word):
    word_search = Dicio().search(word)

    try:
        synonyms = word_search.synonyms
    except AttributeError:
        return [None, None]

    for c in range(0, len(synonyms)):
        synonyms[c] = str(synonyms[c])

    synonyms = ', '.join(synonyms)

    return synonyms, word_search.url


def get_examples(word):
    word_search = Dicio().search(word)

    try:
        examples = word_search.examples
    except AttributeError:
        return [None, None]

    examples = "\n".join(examples)
    return examples, word_search.url


def get_response(word):
    api_res = urllib.request.urlopen(
        f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}')

    api_res = api_res.read()
    api_res = json.loads(api_res.decode("utf-8"))

    return api_res


def format_entry(raw_entry):
    disc_message_template = f'** {raw_entry[0]["word"].capitalize()} \n'

    for word in raw_entry:
        for meaning in word["meanings"]:
            disc_message_template = disc_message_template + \
                f'-> {meaning["partOfSpeech"].capitalize()}: \n'

            for definition in meaning['definitions']:
                disc_message_template = disc_message_template + \
                    f'\tDefinition: {definition["definition"].capitalize()} \n\tExample: {definition["example"].capitalize() if "example" in definition.keys() else "Couldnt find an example..."}\n'

                disc_message_template = disc_message_template + "-" * 87 + '\n'

    return disc_message_template


def get_dictionary_entry(word):
    try:
        raw_entry = get_response(word)
    except urllib.error.HTTPError:
        return None

    formatted_entry = format_entry(raw_entry)
    return formatted_entry


def get_summary(topic):
    try:
        summary = wikipedia.summary(topic, sentences=5)
    except wikipedia.exceptions.DisambiguationError:
        return "Termo ambíguo, possui várias possíveis páginas"
    page = wikipedia.page(topic)
    url = page.url

    return [str(summary), url]


def translate(text, from_lang='en-us', to_lang='pt-br'):
    translator = Translator(from_lang=from_lang, to_lang=to_lang)
    translation = translator.translate(text)
    return str(translation)


class Wiki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def significado(self, ctx, argument):
        word = argument
        meaning, url = get_meaning(word)

        await ctx.trigger_typing()
        try:
            await ctx.send(f'{word} é uma palavra inválida, tente novamente!') if not meaning else await ctx.send(f"Significado de {word}:\n \n{meaning}\nReferência: {url}")
        except discord.errors.HTTPException:
            await ctx.send(f"Definição muito extensa! Você pode encontrá-la por completo em: {url}")

    @commands.command()
    async def sinonimos(self, ctx, argument):
        word = argument
        synonyms, url = get_synonyms(word)

        await ctx.trigger_typing()
        await ctx.send(f'{word} é uma palavra inválida, tente novamente!') if not synonyms else await ctx.send(f"Sinônimos de {word.capitalize()}:\n \n {synonyms}")

    @commands.command()
    async def exemplos(self, ctx, argument):
        word = argument
        examples, url = get_examples(word)

        await ctx.trigger_typing()
        await ctx.send(f'{word} é uma palavra inválida, tente novamente!') if not examples else await ctx.send(f'Exemplos usando {word}:\n \n{examples}')

    @commands.command()
    async def resumo(self, ctx):
        topic = ctx.message.content.split(
            f"{self.bot.command_prefix}resumo")[1]
        summary, url = get_summary(topic)

        await ctx.trigger_typing()
        await ctx.send(f'{topic} é um termo inválido, tente novamente!') if not summary else await ctx.send(f'Segundo a wikipedia:\n \n{summary.capitalize().strip()}\n \nReferência: {url}')

    @commands.command()
    async def meaning(self, ctx, argument):
        word = argument
        entry = get_dictionary_entry(word)

        await ctx.trigger_typing()
        await ctx.send(entry if entry else f"{word.capitalize()} é uma palavra inválida, tente novamente!")

    @commands.command()
    async def translate(self, ctx, *argument):
        try:
            sentence, to_lang, from_lang = argument
        except ValueError:
            sentence = argument[0]
            from_lang = 'en-us'
            to_lang = 'pt-br'

        translated = translate(sentence, to_lang, from_lang)
        await ctx.send(translated)


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
