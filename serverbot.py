import asyncio
import discord
import minecraft as mc
import multiprocessing as mp
import multiprocessing.connection as mpc
import os
import threading

from dotenv import load_dotenv


# Load Env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
BOT_CHAN_ID=int(os.getenv('BOT_CHAN_ID'))
SECRET = str.encode(os.getenv('SECRET'))


# Globals
client = discord.Client()
controller_handlers = {}

# Ready handler
@client.event
async def on_ready():
    global mcc

    # Still a bit ugly
    myguild = None

    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        print(f'Connected to {guild.name}({guild.id})!')
        if guild.id == GUILD_ID:
            myguild = guild

    # Initialize our server controllers
    mcc = mc.Minecraft(client, myguild)
    controller_handlers[mcc.prefix] = mcc


# Message handler
@client.event
async def on_message(message):
    author = message.author
    content = message.content
    channel = message.channel
    guild = channel.guild
    roles = map(lambda x : x.name, author.roles)

    # Check for server identitiy, RCON role, prefix, and parse
    if guild.id != GUILD_ID:
        # Wrong server. WTF?
        await channel.send('I don\'t recognize this server. Why am I even in here?')
        return

    if channel.id != BOT_CHAN_ID:
        # Wrong channel, ignore
        return

    # Check for command and permissions. Silently ignore failed authN because it could be a message
    # meant for a different bot
    if (guild.id == GUILD_ID) and (len(content) > 0) and (content[0] == '!') and ('RCON' in roles):
        tokens = content.split(None, 1)
        prefix = tokens[0][1:]
        command = None
        if len(tokens) > 1:
            command = tokens[1]
        await process_cmd(prefix, command, channel, roles)


async def process_cmd(prefix, command, channel, roles):
    if prefix == 'halp':
        help_msg = ('ServerBot prefixs:\n'
                    '!halp - print this message\n'
                    '!mc - minecraft prefix ("!mc help" for more info)')
        await channel.send(help_msg)
    elif prefix in controller_handlers:
        controller_handlers[prefix].try_send(command)
    else:
        # Ignore unknown commands
        return


#TODO: Main is below. Fix this shit

# Run the client
client.run(TOKEN)
