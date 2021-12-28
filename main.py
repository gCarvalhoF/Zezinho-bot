import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=";", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


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
async def connect(ctx, message):
    await ctx.send(message)


@bot.command()
async def disconnect(ctx):
    await ctx.guild.server.disconnect()


@bot.event
async def on_message(message):
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

    if message.author.id != bot.user.id:
        bot_member = await message.guild.fetch_member(bot.user.id)
        if message.channel.id == request_channel_id:

            try:
                await message.author.voice.channel.connect()
                await bot_member.edit(deafen=True)

            except discord.errors.ClientException:
                members_on_channel = bot_member.voice.channel.members

                if len(members_on_channel) > 1 and message.author.voice.channel != bot_member.voice.channel:
                    await message.channel.send(
                        content='Eu já estou sendo usado em outra chamada, entre nela para ouvir junto com os outros :)')
                elif len(members_on_channel) == 1:
                    server = message.guild.voice_client
                    await server.disconnect()
                    await message.author.voice.channel.connect()
                    await bot_member.edit(deafen=True)


bot.run(os.getenv('TOKEN'))
