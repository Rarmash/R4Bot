import datetime
import platform
import sys
import time
from math import ceil

import discord
import requests
from discord.ext import commands
from xpa import ErrorHandler as XboxErrorHandler
from xpa import XPA

from cogs.steam import get_player_summary
from modules.firebase import get_from_record
from modules.server_config import respond_missing_server_config
from options import applicationID, servers_data, version
from services.secret_service import SecretService

DATE_FORMAT = "%#d.%#m.%Y в %H:%M:%S"
FORTNITE_API_BASE = "https://fortnite-api.com"
_xbox_client = None


class BotLink(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        invite_button = discord.ui.Button(
            label="Приглашение",
            style=discord.ButtonStyle.link,
            emoji="🤩",
            url=f"https://discord.com/oauth2/authorize?client_id={applicationID}&permissions=8&scope=bot%20applications.commands",
        )
        self.add_item(invite_button)


def get_status_emoji(status):
    if status == discord.Status.online:
        return "🟢 в сети"
    if status == discord.Status.offline:
        return "⚪ не в сети"
    if status == discord.Status.idle:
        return "🌙 не активен"
    if status == discord.Status.dnd:
        return "⛔ не беспокоить"
    return "❔ неизвестно"


def get_timestamp(value: datetime.datetime) -> int:
    return ceil(
        time.mktime(
            (
                datetime.datetime.strptime(
                    str(value.strftime(DATE_FORMAT)),
                    "%d.%m.%Y в %H:%M:%S",
                )
                + datetime.timedelta(hours=3)
            ).timetuple()
        )
    )


def format_voice_duration(total_seconds):
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} ч {minutes} м"
    if minutes:
        return f"{minutes} м {seconds} с"
    return f"{seconds} с"


def get_xbox_client():
    global _xbox_client
    if _xbox_client is not None:
        return _xbox_client

    api_key = SecretService().get("xbox", "api_key")
    if not api_key:
        return None

    _xbox_client = XPA(api_key)
    return _xbox_client


def get_xbox_gamertag_to_profile(xuid):
    xbox_client = get_xbox_client()
    if xbox_client is None:
        return str(xuid)

    try:
        return xbox_client.get_account_info_xuid(xuid).Gamertag
    except XboxErrorHandler.XboxApiError:
        return str(xuid)


def get_fortnite_headers():
    api_key = SecretService().get("fortnite", "api_key")
    if not api_key:
        return None
    return {"Authorization": api_key}


def get_fortnite_username_to_profile(account_id):
    headers = get_fortnite_headers()
    if headers is None:
        return str(account_id)

    try:
        response = requests.get(
            f"{FORTNITE_API_BASE}/v2/stats/br/v2/{account_id}",
            headers=headers,
            timeout=30,
        )
        payload = response.json()
        return (payload.get("data") or {}).get("account", {}).get("name") or str(account_id)
    except requests.RequestException:
        return str(account_id)


class Profile(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    @commands.slash_command(description="Посмотреть карточку профиля")
    @discord.option("user", description="Пользователь", required=False)
    async def profile(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
            return

        user = user or ctx.author
        await ctx.defer()

        status = get_status_emoji(user.status)
        user_data = get_from_record(str(ctx.guild.id), "Users", str(user.id))

        if user.id != self.bot.user.id:
            timeout_suffix = "(в тайм-ауте)" if user.timed_out else ""
            embed = discord.Embed(
                title=f"Привет, я {user.name}",
                description=f"<@{user.id}> — {status} {timeout_suffix}".strip(),
                color=int(server_data.get("accent_color"), 16),
            )
            embed.add_field(name="Регистрация", value=f"<t:{get_timestamp(user.created_at)}:f>")
            embed.add_field(name="На сервере с", value=f"<t:{get_timestamp(user.joined_at)}:f>")

            if not user.bot and user_data:
                embed.add_field(name="Сообщений", value=user_data.get("messages", 0))
                embed.add_field(name="Всего тайм-аутов", value=user_data.get("timeouts", 0))
                embed.add_field(name="Голосовая активность", value=format_voice_duration(user_data.get("voice", 0)))

                if "xbox" in user_data:
                    gamertag = get_xbox_gamertag_to_profile(user_data["xbox"])
                    embed.add_field(
                        name="Профиль Xbox",
                        value=f"[{gamertag}](https://www.xbox.com/play/user/{str(gamertag).replace(' ', '%20')})",
                    )
                if "fortnite" in user_data:
                    nickname = get_fortnite_username_to_profile(user_data["fortnite"])
                    embed.add_field(name="Профиль Fortnite", value=nickname)
                if "steam" in user_data:
                    steam_id = str(user_data["steam"])
                    steam_label = steam_id
                    try:
                        steam_summary = get_player_summary(steam_id)
                        if steam_summary and steam_summary.get("personaname"):
                            steam_label = steam_summary["personaname"]
                    except Exception:
                        pass

                    embed.add_field(
                        name="Профиль Steam",
                        value=f"[{steam_label}](https://steamcommunity.com/profiles/{steam_id})",
                    )

            insider_role = discord.utils.get(ctx.guild.roles, id=server_data.get("insider_id"))
            if insider_role in user.roles:
                embed.set_footer(text="Принимает участие в тестировании и помогает серверу стать лучше")

            embed.set_thumbnail(url=user.avatar)
            await ctx.respond(embed=embed)
            return

        embed = discord.Embed(
            title=f"Привет, я {user.name}",
            description=f"Тег: <@{user.id}>",
            color=int(server_data.get("accent_color"), 16),
        )
        embed.add_field(name="Владелец", value=f"<@{server_data.get('admin_id')}>")
        embed.add_field(name="Сервер бота", value=ctx.guild.name)
        embed.add_field(name="Создан", value=f"<t:{get_timestamp(user.created_at)}:f>")
        embed.add_field(name="На сервере с", value=f"<t:{get_timestamp(user.joined_at)}:f>")
        embed.add_field(name="Статус", value=status)
        embed.add_field(name="ОС", value=sys.platform)
        embed.add_field(name="Версия бота", value=version)
        embed.add_field(name="Версия Python", value=platform.python_version())
        embed.add_field(name="Версия Pycord", value=discord.__version__)
        embed.set_thumbnail(url=user.avatar)
        await ctx.respond(embed=embed, view=BotLink())


def setup(bot):
    bot.add_cog(Profile(bot, servers_data))
