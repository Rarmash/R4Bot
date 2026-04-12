from discord.ext import commands
from discord.utils import get

from options import servers_data


class Starboard(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        server_data = self.get_server_data(payload.guild_id)
        if not server_data:
            return

        if payload.channel_id != server_data.get("media_channel") or payload.emoji.name != "📌":
            return

        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        reaction = get(message.reactions, emoji=payload.emoji.name)
        if reaction and reaction.count >= server_data.get("media_pins"):
            await message.pin()


def setup(bot):
    bot.add_cog(Starboard(bot, servers_data))
