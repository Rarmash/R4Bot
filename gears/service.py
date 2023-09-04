import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from options import token, mongodb_link, fortniteapi, xboxapi, servers_data
import os
import time
import datetime
from math import ceil
class Service(commands.Cog):

    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data
    
    service = SlashCommandGroup("service", "Сервисные команды")
    
    # Slash command to view server information
    @commands.slash_command(description='Посмотреть карточку сервера')
    async def server(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        guild = ctx.guild
        embed = discord.Embed(title=f"Информация о сервере {guild}", color = int(server_data.get("accent_color"), 16))
        embed.set_thumbnail(url=guild.icon)
        embed.add_field(name="Описание", value=guild.description)
        embed.add_field(name="Каналов", value=len(guild.channels))
        embed.add_field(name="Ролей", value=len(guild.roles))
        embed.add_field(name="Бустеров", value=len(guild.premium_subscribers))
        embed.add_field(name="Участников", value=guild.member_count-len(([member for member in ctx.guild.members if member.bot])))
        embed.add_field(name="Ботов", value=len(([member for member in ctx.guild.members if member.bot])))
        embed.add_field(name="Создан", value=f"<t:{ceil(time.mktime(datetime.datetime.strptime(str(guild.created_at.strftime('%#d.%#m.%Y в %H:%M:%S')), '%d.%m.%Y в %H:%M:%S').timetuple()))}:f>")
        embed.add_field(name="Владелец", value=f"<@{guild.owner.id}>")
        await ctx.respond(embed=embed)

    # Subcommand to send bot information in a private message
    @service.command(description='Отправить инфу по боту')
    async def botsecret(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        if ctx.author.id == server_data.get("admin_id"):
            await ctx.respond("Скинул в ЛС.")
            await ctx.author.send(f'Токен бота: `{token}`\nБаза MongoDB: `{mongodb_link}`\nFortnite API: `{fortniteapi}`\nXbox API: `{xboxapi}`')
        else:
            await ctx.respond("Недостаточно прав для выполнения данной команды.")   

    # Subcommand to shut down the bot
    @service.command(description='Выключить бота')
    async def shutdown(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        if ctx.author.id == server_data.get("admin_id"):
            await ctx.respond("Завершение работы... :wave:")
            os.abort()
        else:
            await ctx.respond("Недостаточно прав для выполнения данной команды.")

    # Subcommand to unload a gear
    @service.command()
    async def unload(self, ctx, gear):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        if ctx.author.id == server_data.get("admin_id"):
            self.bot.unload_extension(f"gears.{gear}")
            await ctx.respond(f"**gears.{gear}** выгружается...")
        else:
            await ctx.respond("Недостаточно прав для выполнения данной команды.")

    # Subcommand to load a gear
    @service.command()
    async def load(self, ctx, gear):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        if ctx.author.id == server_data.get("admin_id"):
            self.bot.load_extension(f"gears.{gear}")
            await ctx.respond(f"**gears.{gear}** запускается...")
        else:
            await ctx.respond("Недостаточно прав для выполнения данной команды.")

    # Subcommand to reload a gear
    @service.command()
    async def reload(self, ctx, gear):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        if ctx.author.id == server_data.get("admin_id"):
            self.bot.unload_extension(f"gears.{gear}")
            self.bot.load_extension(f"gears.{gear}")
            await ctx.respond(f"**gears.{gear}** перезапускается...")
        else:
            await ctx.respond("Недостаточно прав для выполнения данной команды.")

def setup(bot):
    bot.add_cog(Service(bot, servers_data))