import discord
from discord.ext import commands

from options import servers_data


class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Отправить сообщение от имени бота")
    @discord.default_permissions(manage_messages=True)
    @discord.guild_only()
    @discord.option("text", description="Текст сообщения")
    @discord.option("channel", description="Канал для отправки")
    async def say(self, ctx, text: str, channel: discord.TextChannel):
        server_data = servers_data.get(str(ctx.guild.id))
        if not server_data:
            await ctx.respond("Сервер ещё не настроен.", ephemeral=True)
            return

        try:
            await channel.send(text)
        except discord.Forbidden:
            await ctx.respond("У меня нет прав отправлять сообщения в этот канал.", ephemeral=True)
            return
        except discord.HTTPException:
            await ctx.respond("Не удалось отправить сообщение.", ephemeral=True)
            return

        await ctx.respond(f"Сообщение отправлено в {channel.mention}.", ephemeral=True)


def setup(bot):
    bot.add_cog(Say(bot))
