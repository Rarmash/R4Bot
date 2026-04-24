from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

CONFIG_NOT_INITIALIZED_MESSAGE = (
    "Сервер ещё не настроен. Владелец сервера может выполнить `/service initserver`."
)

DEFAULT_ACCENT_COLOR = "0x209af8"

DEFAULT_SERVER_CONFIG = {
    "accent_color": DEFAULT_ACCENT_COLOR,
    "log_channel": 0,
    "admin_channel": 0,
    "ticket_category": 0,
    "suggestions_channel": 0,
    "media_channel": 0,
    "media_pins": 1,
    "admin_id": 0,
    "mod_role_id": 0,
    "insider_id": 0,
    "admin_role_id": 0,
    "trash_channels": [],
    "bannedChannels": [],
    "bannedUsers": [],
    "bannedCategories": [],
    "bannedTTSChannels": [],
    "banned_TTS_role": 0,
}


def build_default_servers_payload() -> dict:
    return {
        "cogs": ["events", "module_manager"],
        "server_id": deepcopy(DEFAULT_SERVER_CONFIG),
    }


def build_server_config(admin_id: int) -> dict:
    payload = deepcopy(DEFAULT_SERVER_CONFIG)
    payload["admin_id"] = admin_id
    return payload


def load_servers_config(path: str | Path = "servers.json") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {"cogs": []}

    with config_path.open("r", encoding="utf8") as file:
        return json.load(file)


def save_servers_config(payload: dict, path: str | Path = "servers.json"):
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf8") as file:
        json.dump(payload, file, indent=4, ensure_ascii=False)


def initialize_server_config(
    guild_id: int,
    admin_id: int,
    path: str | Path = "servers.json",
    overwrite: bool = False,
) -> tuple[dict, bool]:
    payload = load_servers_config(path)
    guild_key = str(guild_id)
    already_exists = guild_key in payload

    if already_exists and not overwrite:
        return payload[guild_key], False

    payload[guild_key] = build_server_config(admin_id)
    save_servers_config(payload, path)
    return payload[guild_key], True


async def respond_missing_server_config(target):
    if hasattr(target, "respond"):
        await target.respond(CONFIG_NOT_INITIALIZED_MESSAGE, ephemeral=True)
        return

    response = getattr(target, "response", None)
    if response is not None and not response.is_done():
        await response.send_message(CONFIG_NOT_INITIALIZED_MESSAGE, ephemeral=True)
        return

    followup = getattr(target, "followup", None)
    if followup is not None:
        await followup.send(CONFIG_NOT_INITIALIZED_MESSAGE, ephemeral=True)
