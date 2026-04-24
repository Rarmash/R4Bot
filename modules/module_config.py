from __future__ import annotations

import json
from pathlib import Path


MODULE_CONFIG_DIR = Path("config/modules")


def get_module_config_path(module_id: str) -> Path:
    return MODULE_CONFIG_DIR / f"{module_id}.json"


def load_module_config(module_id: str) -> dict:
    config_path = get_module_config_path(module_id)
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def save_module_config(module_id: str, payload: dict):
    config_path = get_module_config_path(module_id)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8-sig") as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)


def get_guild_module_config(module_id: str, guild_id: int | str) -> dict | None:
    return load_module_config(module_id).get(str(guild_id))
