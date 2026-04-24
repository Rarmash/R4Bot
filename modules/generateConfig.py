import json
from time import sleep

from modules.server_config import build_default_servers_payload

def check_servers_file():
    servers_template = build_default_servers_payload()

    with open("servers.json", "w", encoding="utf8") as file:
        json.dump(servers_template, file, indent=4, ensure_ascii=False)

    print("Для продолжения заполните файл servers.json.")
    sleep(5)
    exit()
