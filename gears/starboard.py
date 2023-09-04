from discord.ext import commands
from options import servers_data
from discord.utils import get

class Starboard(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        server_data = self.servers_data.get(str(payload.guild_id))
        if not server_data:
            return
        # Check if the reaction was added in the media_channel and is the 📌 emoji
        if payload.channel_id == server_data.get("media_channel") and payload.emoji.name == "📌":
            channel = await self.Bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            # Get the reaction object for the 📌 emoji
            reaction = get(message.reactions, emoji=payload.emoji.name)
            # Check if the reaction count is equal to or greater than the required media_pins count
            if reaction and reaction.count >= server_data.get("media_pins"):
                await message.pin()
        
def setup(bot):
    bot.add_cog(Starboard(bot, servers_data))