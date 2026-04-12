from datetime import datetime

import discord

from modules.firebase import create_firebase_app
from modules.versionChecker import VersionChecker
from options import cogs_list, debugmode, firebase_id, token, version

create_firebase_app(firebase_id)

intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.messages = True

bot = discord.Bot(case_insensitive=True, intents=intents)
VersionChecker(bot)


@bot.event
async def on_ready():
    print("------")
    print(f"Текущее время: {datetime.now()}")
    print(f"{bot.user.name} запущен!")
    print(f"Версия: {version}")
    print(f"ID бота: {bot.user.id}")
    for guild in bot.guilds:
        print(f"Подключились к серверу: {guild}")
    print("------")

    is_debug = debugmode == "ON"
    status = discord.Status.dnd if is_debug else discord.Status.online
    status_text = f"v{version} debug" if is_debug else f"v{version}"
    activity = discord.CustomActivity(name=status_text)
    await bot.change_presence(status=status, activity=activity)


for module_name in cogs_list:
    try:
        bot.load_extension(f"cogs.{module_name}")
        print(f"Загружен общий модуль '{module_name}'")
    except Exception as exc:
        print(f"Не удалось загрузить общий модуль '{module_name}': {exc}")


if __name__ == "__main__":
    bot.run(token)
