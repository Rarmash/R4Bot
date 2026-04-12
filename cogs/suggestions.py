import discord
from discord.ext import commands

from options import servers_data


class Suggest(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    @commands.slash_command(description="Предложить идею")
    @discord.option("suggestion", description="Ваше предложение")
    @discord.option("duration", description="Время голосования (в часах)", default=24)
    @discord.guild_only()
    async def suggest(self, ctx: discord.ApplicationContext, suggestion: str, duration: int):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        suggest_accept = discord.PollAnswer(text="За")
        suggest_deny = discord.PollAnswer(text="Против")
        suggest_poll = discord.Poll(
            question=suggestion,
            answers=[suggest_accept, suggest_deny],
            duration=duration,
            allow_multiselect=False,
        )
        await ctx.respond(poll=suggest_poll)


def setup(bot):
    bot.add_cog(Suggest(bot, servers_data))
