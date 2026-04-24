import discord
from discord.ext import commands


class DemoPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Проверочный ответ demo-модуля")
    async def demoping(self, ctx: discord.ApplicationContext):
        await ctx.respond("Demo-модуль установлен и работает.")


def setup(bot):
    bot.add_cog(DemoPing(bot))
