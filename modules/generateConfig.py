import json
from time import sleep


def check_servers_file():
    servers_template = {
        "cogs": ["events"],
        "server_id": {
            "accent_color": "0xFFFFFF",
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
            "tts_voice_limit": {
                "channel_id": 0,
                "limit": 4,
            },
            "tempvoice": {
                "trigger_channel_id": 0,
                "category_id": 0,
                "channel_name_template": "Канал {display_name}",
                "user_limit": 0,
                "bitrate": None,
                "delete_empty_channels": True,
            },
        },
    }

    with open("servers.json", "w", encoding="utf8") as file:
        json.dump(servers_template, file, indent=4, ensure_ascii=False)

    print("Для продолжения заполните файл servers.json.")
    sleep(5)
    exit()
