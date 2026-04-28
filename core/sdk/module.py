from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from discord.ext import commands

from core.sdk.hooks import (
    collect_hook_results,
    list_hook_providers,
    register_hook_provider,
    subscribe_hook_events,
    unregister_hook_provider,
    unsubscribe_hook_events,
)
from core.runtime_context import RuntimeServices
from services.config_service import ConfigService
from services.firebase_service import FirebaseService
from services.module_config_service import ModuleConfigService
from services.module_resource_service import ModuleResourceService
from services.module_state_service import ModuleStateService
from services.secret_service import SecretService


class ModuleServices(Protocol):
    config: ConfigService
    firebase: FirebaseService
    module_config: ModuleConfigService
    resources: ModuleResourceService
    module_state: ModuleStateService
    secrets: SecretService


@dataclass(frozen=True)
class ModuleContext:
    module_id: str
    services: RuntimeServices


class R4BotModule(commands.Cog):
    module_id = ""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.services: RuntimeServices = bot.r4_services
        self.context = ModuleContext(module_id=self.module_id, services=self.services)

    def get_server_data(self, guild_id: int) -> dict | None:
        return self.services.config.get_servers_data().get(str(guild_id))

    def get_module_config(self, guild_id: int) -> dict | None:
        return self.services.module_config.get_guild_config(self.module_id, guild_id)

    def get_module_secrets(self) -> dict:
        return self.services.secrets.load(self.module_id)

    def get_secret(self, key: str, default=None):
        return self.services.secrets.get(self.module_id, key, default)

    def get_resource_path(self, *parts: str) -> Path:
        return self.services.resources.get_resource_path(self.module_id, *parts)

    def is_module_enabled(self, module_id: str) -> bool:
        return self.services.module_state.is_module_enabled(module_id)

    def register_hook_provider(self, hook_name: str, provider):
        register_hook_provider(self.bot, hook_name, self.module_id, provider)

    def unregister_hook_provider(self, hook_name: str):
        unregister_hook_provider(self.bot, hook_name, self.module_id)

    def list_hook_providers(self, hook_name: str) -> dict[str, object]:
        return list_hook_providers(self.bot, hook_name)

    async def collect_hook_results(self, hook_name: str, **payload) -> list[tuple[str, object]]:
        return await collect_hook_results(self.bot, hook_name, **payload)

    def subscribe_hook_events(self, hook_name: str, listener):
        subscribe_hook_events(self.bot, hook_name, listener)

    def unsubscribe_hook_events(self, hook_name: str, listener):
        unsubscribe_hook_events(self.bot, hook_name, listener)
