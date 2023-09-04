import json
from time import sleep

# Function to check and create the servers file template if it doesn't exist
def check_servers_file():
    servers_template = {
        "gears": ["events"],
        "server_id": {
            "accent_color": "0xFFFFFF",
            "log_channel": 0,
            "admin_channel": 0,
            "ticket_category": 0,
            "suggestions_channel": 0,
            "media_channel": 0,
            "media_pins": 1,
            "admin_id": 0,
            "elder_mod_role_id": 0,
            "junior_mod_role_id": 0,
            "insider_id": 0,
            "admin_role_id": 0,
            "trash_channels": [],
            "bannedChannels": [],
            "bannedUsers": [],
            "bannedCategories": [],
            "bannedTTSChannels": []
        }
    }
    # Create and write the servers template to servers.json
    with open('servers.json', 'w') as f:
        json.dump(servers_template, f, indent=4)
    print('Для продолжения, заполните файл servers.json.') # Print instructions for the user
    sleep(5) # Sleep for 5 seconds to give the user time to read the instructions
    exit() # Exit the program