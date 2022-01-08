import discord
from time import sleep
from discord.ext import commands
from dotenv import load_dotenv
import os
import re
import cogs

load_dotenv()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=";", intents=intents)


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


bot.add_cog(cogs.Music(bot))
bot.add_cog(cogs.Wiki(bot))

bot.run(os.getenv('TOKEN'))
