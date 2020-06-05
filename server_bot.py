import asyncio
import discord
import multiprocessing as mp
import multiprocessing.connection as mpc
import os
import threading


from dotenv import load_dotenv


# Load Env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
BOT_CHAN=int(os.getenv('BOT_CHAN'))
MC_LOG_CHAN=int(os.getenv('MC_LOG_CHAN'))
SECRET = str.encode(os.getenv('SECRET'))
MCC_PORT= int(os.getenv('MCC_PORT'))


# Globals
client = discord.Client()
myguild = None
mc_conn = None


# Ready handler
@client.event
async def on_ready():
    global myguild

    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        print(f'Connected to {guild.name}({guild.id})!')
        #TODO: This is horrible and bad
        myguild = guild

    # We're all loaded up. Init minecraft
    Minecraft.init()


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

    if channel.id != BOT_CHAN:
        # Wrong channel, ignore
        return

    # Check for command and permissions. Silently ignore failed authN because it could be a message
    # meant for a different bot
    if (guild.id == GUILD_ID) and (len(content) > 0) and (content[0] == '!') and ('RCON' in roles):
        tokens = content.split(' ', 1)
        command = tokens[0][1:]
        args = None
        if len(tokens) > 1:
            args = tokens[1]
        await process_cmd(command, args, channel, roles)


async def process_cmd(command, args, channel, roles):
    if command == 'halp':
        help_msg = ('ServerBot commands:\n'
                    '!halp - print this message\n'
                    '!mc - minecraft command ("!mc help" for more info)')
        await channel.send(help_msg)
    elif command == 'mc':
        Minecraft.send(args)
    else:
        # Ignore unknown commands
        return

class Minecraft:
    def send(msg):
        #TODO: handle errors
        mc_conn.send(msg)


    def init():
        global mc_conn

        # Connect to MC Controller
        mc_conn = mpc.Client(('localhost', MCC_PORT), authkey=SECRET)

        # Create loop

        # TODO: Error handling
        def read_thread():
            mlc = myguild.get_channel(MC_LOG_CHAN)
            bc = myguild.get_channel(BOT_CHAN)
            while not mc_conn.closed:
                line = mc_conn.recv()
                [status, msg] = line.split('|', 1)
                status = status.strip()
                if status == 'LOG':
                    asyncio.run_coroutine_threadsafe(mlc.send(msg), client.loop)
                elif status == 'OK':
                    asyncio.run_coroutine_threadsafe(bc.send(msg), client.loop)
                else:
                    asyncio.run_coroutine_threadsafe(bc.send(f'{status}: {msg}'), client.loop)

        reader = threading.Thread(target=read_thread)
        reader.daemon = True
        reader.start()

#TODO: Main is below. Fix this shit

# Run the client
client.run(TOKEN)
