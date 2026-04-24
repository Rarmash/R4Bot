from __future__ import annotations

from datetime import datetime

import discord

from core.module_loader import ModuleLoader
from modules.firebase import create_firebase_app
from modules.versionChecker import VersionChecker
from services.config_service import ConfigService


class R4BotApplication:
    def __init__(self, config_service: ConfigService | None = None):
        self.config = config_service or ConfigService()

        if self.config.firebase_project_id:
            create_firebase_app(self.config.firebase_project_id)

        intents = discord.Intents.all()
        intents.presences = True
        intents.members = True
        intents.messages = True

        self.bot = discord.Bot(case_insensitive=True, intents=intents)
        self.loader = ModuleLoader(self.bot, self.config)
        VersionChecker(self.bot)
        self._register_events()

    def _register_events(self):
        @self.bot.event
        async def on_ready():
            try:
                await self.bot.sync_commands()
                print(f"Synced {len(self.bot.pending_application_commands)} pending application commands")
            except Exception as exc:
                print(f"Failed to sync application commands: {exc}")

            print("------")
            print(f"Текущее время: {datetime.now()}")
            print(f"{self.bot.user.name} запущен!")
            print(f"Версия: {self.config.version}")
            print(f"ID бота: {self.bot.user.id}")
            for guild in self.bot.guilds:
                print(f"Подключились к серверу: {guild}")
            print("------")

            status = discord.Status.dnd if self.config.debug_mode else discord.Status.online
            status_text = f"v{self.config.version} debug" if self.config.debug_mode else f"v{self.config.version}"
            await self.bot.change_presence(status=status, activity=discord.CustomActivity(name=status_text))

    def run(self):
        self.loader.load_enabled_modules()
        self.bot.run(self.config.token)
