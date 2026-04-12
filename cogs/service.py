import datetime
import os
import time
from math import ceil
from pathlib import Path

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from options import servers_data


def read_env_lines():
    env_path = Path(".env")
    if not env_path.exists():
        return []

    lines = []
    for raw_line in env_path.read_text(encoding="utf8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        lines.append((key.strip(), value.strip()))
    return lines


def get_servers_file():
    servers_path = Path("servers.json")
    return servers_path if servers_path.exists() else None


def get_timestamp(value: datetime.datetime) -> int:
    return ceil(
        time.mktime(
            datetime.datetime.strptime(
                value.strftime("%#d.%#m.%Y в %H:%M:%S"),
                "%d.%m.%Y в %H:%M:%S",
            ).timetuple()
        )
    )


class Service(commands.Cog):
    service = SlashCommandGroup("service", "Сервисные команды")

    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    async def deny_if_not_admin(self, ctx, server_data) -> bool:
        if ctx.author.id == server_data.get("admin_id"):
            return False

        await ctx.respond("Недостаточно прав для выполнения данной команды.")
        return True

    @commands.slash_command(description="Посмотреть карточку сервера")
    @discord.guild_only()
    async def server(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        guild = ctx.guild
        members = guild.members
        bot_count = len([member for member in members if member.bot])

        embed = discord.Embed(
            title=f"Информация о сервере {guild}",
            color=int(server_data.get("accent_color"), 16),
        )
        embed.set_thumbnail(url=guild.icon)
        embed.add_field(name="Описание", value=guild.description or "Отсутствует")
        embed.add_field(name="Каналов", value=str(len(guild.channels)))
        embed.add_field(name="Ролей", value=str(len(guild.roles)))
        embed.add_field(name="Бустеров", value=str(len(guild.premium_subscribers)))
        embed.add_field(name="Участников", value=str(guild.member_count - bot_count))
        embed.add_field(name="Ботов", value=str(bot_count))
        embed.add_field(name="Создан", value=f"<t:{get_timestamp(guild.created_at)}:f>")
        embed.add_field(name="Владелец", value=f"<@{guild.owner.id}>")
        await ctx.respond(embed=embed)

    @service.command(description="Отправить .env и servers.json")
    async def secrets(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        if await self.deny_if_not_admin(ctx, server_data):
            return

        env_lines = read_env_lines()
        servers_file = get_servers_file()

        if not env_lines and not servers_file:
            await ctx.respond("Файлы `.env` и `servers.json` не найдены.", ephemeral=True)
            return

        await ctx.respond("Скинул секреты в ЛС.")

        if env_lines:
            secret_text = "\n".join(f"{key}={value}" for key, value in env_lines)
            if servers_file:
                await ctx.author.send(f"```env\n{secret_text}\n```", file=discord.File(servers_file))
            else:
                await ctx.author.send(f"```env\n{secret_text}\n```")
            return

        await ctx.author.send(file=discord.File(servers_file))

    @service.command(description="Выключить бота")
    async def shutdown(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        if await self.deny_if_not_admin(ctx, server_data):
            return

        await ctx.respond("Завершение работы... :wave:")
        os.abort()

    @service.command(description="Выгрузить модуль")
    @discord.option("cog", description="Название модуля")
    async def unload(self, ctx, cog: str):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        if await self.deny_if_not_admin(ctx, server_data):
            return

        self.bot.unload_extension(f"cogs.{cog}")
        await ctx.respond(f"**cogs.{cog}** выгружается...")

    @service.command(description="Загрузить модуль")
    @discord.option("cog", description="Название модуля")
    async def load(self, ctx, cog: str):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        if await self.deny_if_not_admin(ctx, server_data):
            return

        self.bot.load_extension(f"cogs.{cog}")
        await ctx.respond(f"**cogs.{cog}** запускается...")

    @service.command(description="Перезагрузить модуль")
    @discord.option("cog", description="Название модуля")
    async def reload(self, ctx, cog: str):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        if await self.deny_if_not_admin(ctx, server_data):
            return

        self.bot.unload_extension(f"cogs.{cog}")
        self.bot.load_extension(f"cogs.{cog}")
        await ctx.respond(f"**cogs.{cog}** перезапускается...")


def setup(bot):
    bot.add_cog(Service(bot, servers_data))
