import discord

from modules.firebase import create_firebase_app
from options import token, debugmode, version, gearsList

create_firebase_app()

# Define intents for the bot to receive all available events
intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.messages = True

# Create the Discord bot instance with specified intents
bot = discord.Bot(case_insensitive=True, intents=intents)

# Gears are always cool

# Event that runs when the bot is ready and connected to Discord
@bot.event
async def on_ready():
    # Print bot information and connected guilds
    print("------")
    print(f"{bot.user.name} запущен!")
    print(f"Версия: {version}")
    print(f"ID бота: {str(bot.user.id)}")
    for guild in bot.guilds:
        print(f"Подключились к серверу: {guild}")
    print("------")
    
    # Set bot status and activity based on debug mode
    if debugmode == "ON":
        status = discord.Status.dnd
        activity = discord.Activity(type=discord.ActivityType.playing, name=f"debug-режиме (v{version})")
    else:
        status = discord.Status.online
        activity = discord.Activity(type=discord.ActivityType.listening, name=f"обиды участников (v{version})")
    await bot.change_presence(status=status, activity=activity)

for module_name in gearsList:
    try:
        bot.load_extension(f'gears.{module_name}')
        print(f"Загружен общий модуль '{module_name}'")
    except Exception as e:
        print(f"Не удалось загрузить общий модуль '{module_name}': {str(e)}")

# Run the bot with the provided token
if __name__ == "__main__":
    bot.run(token)
