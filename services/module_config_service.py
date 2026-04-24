from __future__ import annotations

from modules.module_config import get_guild_module_config, load_module_config, save_module_config


class ModuleConfigService:
    def load(self, module_id: str) -> dict:
        return load_module_config(module_id)

    def save(self, module_id: str, payload: dict):
        save_module_config(module_id, payload)

    def get_guild_config(self, module_id: str, guild_id: int | str) -> dict | None:
        return get_guild_module_config(module_id, guild_id)
