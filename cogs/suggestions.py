import discord
from discord.ext import commands

from options import servers_data


class Suggest(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    @commands.slash_command(description="Предложить идею")
    @discord.option("suggestion", description="Ваше предложение")
    @discord.option("duration", description="Время голосования (в часах)", default=24)
    @discord.guild_only()
    async def suggest(self, ctx: discord.ApplicationContext, suggestion: str, duration: int):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        suggestAccept = discord.PollAnswer(text="За")
        suggestDeny = discord.PollAnswer(text="Против")
        suggestPoll = discord.Poll(question=suggestion,
                                   answers=[suggestAccept, suggestDeny],
                                   duration=duration,
                                   allow_multiselect=False)
        await ctx.respond(poll=suggestPoll)


def setup(bot):
    bot.add_cog(Suggest(bot, servers_data))
