import json
from os import environ

from dotenv import load_dotenv

from modules.generateConfig import check_servers_file

load_dotenv()

version = "1.4.4"

token = environ.get("TOKEN")
applicationID = environ.get("APPLICATIONID")
fortniteapi = environ.get("FORTNITEAPI")
xboxapi = environ.get("XBOXAPI")
steamapi = environ.get("STEAMAPI")
debugmode = environ.get("DEBUGMODE")

with open("firebaseConfig.json", "r", encoding="utf8") as file:
    firebase_id = json.load(file).get("project_id")

try:
    with open("servers.json", "r", encoding="utf8") as file:
        servers_data = json.load(file)

    cogs_list = servers_data.pop("cogs", [])
except FileNotFoundError:
    check_servers_file()
