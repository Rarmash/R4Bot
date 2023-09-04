from dotenv import load_dotenv
from os import environ
import pymongo
import certifi
import json
from modules.generateConfig import *

# Load environment variables from .env file
load_dotenv()

version = "1.0"

# Get environment variables
token = environ.get('TOKEN')
applicationID = environ.get('APPLICATIONID')
fortniteapi = environ.get('FORTNITEAPI')
xboxapi = environ.get('XBOXAPI')
mongodb_link = environ.get('MONGODB')
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

try:
    # Try to create a MongoDB client with the provided MongoDB link
    myclient = pymongo.MongoClient(mongodb_link)
except:
    # If an exception occurs (e.g., connection failure), try to create a MongoDB client with TLS/SSL using certifi
    myclient = pymongo.MongoClient(mongodb_link, tlsCAFile=certifi.where())