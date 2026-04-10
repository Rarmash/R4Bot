import datetime
import platform
import sys
import time
from math import ceil

import discord
from discord.ext import commands

from cogs.fortnite import get_fortnite_username_to_profile
from cogs.xbox import get_xbox_gamertag_to_profile
from modules.firebase import get_from_record
from options import applicationID, servers_data, version


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


class Profile(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data

    @commands.slash_command(description="Посмотреть карточку профиля")
    @discord.option("user", description="Пользователь", required=False)
    async def profile(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        date_format = "%#d.%#m.%Y в %H:%M:%S"
        if user is None:
            user = ctx.author

        await ctx.defer()

        status = get_status_emoji(user.status)
        user_data = get_from_record(str(ctx.guild.id), "Users", str(user.id))

        if user.id != self.Bot.user.id:
            time_out = "(в тайм-ауте)" if user.timed_out else ""
            embed = discord.Embed(
                title=f"Привет, я {user.name}",
                description=f"<@{user.id}> — {status} {time_out}",
                color=int(server_data.get("accent_color"), 16),
            )
            embed.add_field(
                name="Регистрация",
                value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.created_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>",
            )
            embed.add_field(
                name="На сервере с",
                value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.joined_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>",
            )
            if not user.bot:
                embed.add_field(name="Сообщений", value=user_data["messages"])
                embed.add_field(name="Всего тайм-аутов", value=user_data["timeouts"])
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
                    embed.add_field(
                        name="Профиль Steam",
                        value=f"[Тык](https://steamcommunity.com/profiles/{user_data['steam']})",
                    )
            if discord.utils.get(ctx.guild.roles, id=server_data.get("insider_id")) in user.roles:
                embed.set_footer(text="Принимает участие в тестировании и помогает серверу стать лучше")
            embed.set_thumbnail(url=user.avatar)
            await ctx.respond(embed=embed)

        if user.id == self.Bot.user.id:
            embed = discord.Embed(
                title=f"Привет, я {user.name}",
                description=f"Тег: <@{user.id}>",
                color=int(server_data.get("accent_color"), 16),
            )
            embed.add_field(name="Владелец", value=f"<@{server_data.get('admin_id')}>")
            embed.add_field(name="Сервер бота", value="RU Xbox Shit Force")
            embed.add_field(
                name="Создан",
                value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.created_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>",
            )
            embed.add_field(
                name="На сервере с",
                value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.joined_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>",
            )
            embed.add_field(name="Статус", value=status)
            embed.add_field(name="ОС", value=sys.platform)
            embed.add_field(name="Версия бота", value=version)
            embed.add_field(name="Версия Python", value=platform.python_version())
            embed.add_field(name="Версия Pycord", value=discord.__version__)
            embed.set_thumbnail(url=user.avatar)
            await ctx.respond(embed=embed, view=BotLink())


def setup(bot):
    bot.add_cog(Profile(bot, servers_data))
