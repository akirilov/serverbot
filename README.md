# serverbot
Discord Bot for server management

This is a Discord bot that will allow you to start, stop and control your Minecraft server from Discord

This is still a very early version so you're going to have to understand a little python to understand what it's doing.
Someday, this will all be nice and polished. Today is not that day.
In essence, clone all this stuff and modify your .env file with the necessary server/channel IDs and secrets.

At this stage there should be at least some error handling on both processes. If you're wondering
why I did it this way, the idea was to handle discord connection issues gracefully without crashing
the minecraft server

## Installation

1. Clone the repo and copy all the files into your preferred location (I like `/opt/serverbot` because I'm too lazy to type long paths)
2. Make a bot with the discord API
3. Make any changes you need to your Discord server
4. Fill out the .env file

## Usage

As minecraft user:

```
python3 minecraft.py
```

As serverbot user:

```
python3 serverbot.py
```

## Requirements

I dunno, just try to run it and see what fails

## Env file breakdown

- DISCORD_TOKEN - The Discord API token for your bot
- GUILD_ID - The Discord id number of your server
- SECRET - Used for the python multiprocessing authkey
- BOT_CHAN - The Discord channel id of your bot channel. The bot will only accept messages from this channel
- MC_DIR - The directory where minecraft should run from
- MC_LOG_CHAN - The Discord channel id of the channel where you want your minecraft log to be spammed
- MCC_PORT - The port you want minecraft.py to run on

A note on security: I use the python multiprocessing lib because it was easy (hah) and at least appears to provide some security.
I haven't done a deep dive (but if you have and want to tell me about, it, I'd love to hear from you!) but the attack surface here
is pretty minimal - an unauthorized user on your server binds the minecraft.py port before minecraft.py can and spams your discord
server bot/log channels OR the attacker connects to minecraft.py before the serverbot can and uses commands.
Both of these assume you don't notice the failure and don't do anything about it.

## Assumptions

- Your server contains an 'RCON' role which will be used to restict who can control the server
- You know how to create your own bot using the Discord developer webapp. It's pretty simple. The only permissions this bot
  should need are reading text channels (if you want to talk to it) and posting to them (if you want it to talk back),
  but since you'll be running your own bot, do whatever. Give it admin. Go crazy.
- Probably something else. I really don't know.

## FAQ

**Q: Are you going to update this for people that want something that just works?**

A: Probably maybe if I am sufficiently bored and/or somebody cares

**Q: Your coding style sucks!**

A: That's not a question

**Q: Why would you do this?**

A: So I can give my friends the ability to start/stop my minecraftr server and invite new people without 
giving them accounts on my linux server and teaching them how to use it

**Q: Something doesn't work!**

A: haha Discord-powered rcon bot go brrr
