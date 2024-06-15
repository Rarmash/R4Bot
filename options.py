from os import environ

from dotenv import load_dotenv

from modules.generateConfig import *

# Load environment variables from .env file
load_dotenv()

version = "1.1"

# Get environment variables
token = environ.get('TOKEN')
applicationID = environ.get('APPLICATIONID')
fortniteapi = environ.get('FORTNITEAPI')
xboxapi = environ.get('XBOXAPI')
debugmode = environ.get('DEBUGMODE')

try:
    # Try to open and load the existing servers.json file
    with open('servers.json') as f:
        servers_data = json.load(f)
    if 'gears' in servers_data:
        gearsList = servers_data['gears']
        del servers_data['gears']
    else:
        gearsList = []
except FileNotFoundError:
    # If servers.json does not exist, call the function to create it
    check_servers_file()
