from datetime import datetime

import discord

from core.module_loader import ModuleLoader
from core.runtime_context import RuntimeContext, RuntimeServices
from modules.firebase import create_firebase_app
from modules.versionChecker import VersionChecker
from options import debugmode, firebase_id, token, version
from services.config_service import ConfigService
from services.firebase_service import FirebaseService
from services.module_config_service import ModuleConfigService
from services.secret_service import SecretService

create_firebase_app(firebase_id)
config_service = ConfigService()
runtime_services = RuntimeServices(
    config=config_service,
    firebase=FirebaseService(),
    module_config=ModuleConfigService(),
    secrets=SecretService(config_service.paths.secrets_dir),
)
runtime_context = RuntimeContext(services=runtime_services)

intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.messages = True

bot = discord.Bot(case_insensitive=True, intents=intents)
bot.r4_context = runtime_context
bot.r4_services = runtime_services
module_loader = ModuleLoader(bot, config_service)
VersionChecker(bot)

commands_synced = False


@bot.event
async def on_ready():
    global commands_synced

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

    if not commands_synced:
        await bot.sync_commands()
        print("Слэш-команды синхронизированы.")
        commands_synced = True


module_loader.load_enabled_modules()


if __name__ == "__main__":
    bot.run(token)
