import datetime
import platform
import sys
import time
from math import ceil

import discord
from discord.ext import commands

from modules.firebase import get_from_record
from options import version, servers_data, applicationID


class BotLink(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Create an invitation button with a link to invite the bot to a guild
        invite_button = discord.ui.Button(label="Приглашение", style=discord.ButtonStyle.link, emoji="🤩",
                                          url=f"https://discord.com/oauth2/authorize?client_id={applicationID}&permissions=8&scope=bot%20applications.commands")
        self.add_item(invite_button)


class Profile(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data

    # Define the profile slash command
    @commands.slash_command(description='Посмотреть карточку профиля')
    async def profile(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        date_format = "%#d.%#m.%Y в %H:%M:%S"
        if user is None:
            user = ctx.author

        # Get the status emoji based on the user's status
        status = self.get_status_emoji(user.status)

        # Fetch user data from the database
        user_data = get_from_record(str(ctx.guild.id), "Users", str(user.id))

        # If the user is not the bot itself, display the user's profile information
        if user.id != self.Bot.user.id:
            time_out = '(в тайм-ауте)' if user.timed_out else ''
            embed = discord.Embed(title=f'Привет, я {user.name}', description=f"<@{user.id}> — {status} {time_out}",
                                  color=int(server_data.get("accent_color"), 16))
            embed.add_field(name="Регистрация",
                            value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.created_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>")
            embed.add_field(name="На сервере с",
                            value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.joined_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>")
            if not user.bot:
                embed.add_field(name="Сообщений", value=user_data['messages'])
                embed.add_field(name="Всего тайм-аутов", value=user_data['timeouts'])
                if "xbox" in user_data:
                    embed.add_field(name="Профиль Xbox",
                                    value=f"[{user_data['xbox']}](https://account.xbox.com/ru-ru/Profile?Gamertag={str(user_data['xbox']).replace(' ', '%20')})")
                if "fortnite" in user_data:
                    embed.add_field(name="Профиль Fortnite", value=user_data['fortnite'])
            if discord.utils.get(ctx.guild.roles, id=server_data.get("insider_id")) in user.roles:
                embed.set_footer(text="Принимает участие в тестировании и помогает серверу стать лучше")
            embed.set_thumbnail(url=user.avatar)
            await ctx.respond(embed=embed)
        # If the user is the bot itself, display the bot's profile information
        if user.id == self.Bot.user.id:
            embed = discord.Embed(title=f'Привет, я {user.name}', description=f"Тег: <@{user.id}>",
                                  color=int(server_data.get("accent_color"), 16))
            embed.add_field(name="Владелец", value=f"<@{server_data.get('admin_id')}>")
            embed.add_field(name="Сервер бота", value="RU Xbox Shit Force")
            embed.add_field(name="Создан",
                            value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.created_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>")
            embed.add_field(name="На сервере с",
                            value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(user.joined_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>")
            embed.add_field(name="Статус", value=status)
            embed.add_field(name="ОС", value=sys.platform)
            embed.add_field(name="Версия бота", value=version)
            embed.add_field(name="Версия Python", value=platform.python_version())
            embed.add_field(name="Версия Pycord", value=discord.__version__)
            embed.set_thumbnail(url=user.avatar)
            await ctx.respond(embed=embed, view=BotLink())

    # Function to get the status emoji based on the user's status
    def get_status_emoji(self, status):
        if status == discord.Status.online:
            return "🟢 в сети"
        elif status == discord.Status.offline:
            return "⚪ не в сети"
        elif status == discord.Status.idle:
            return "🌙 не активен"
        elif status == discord.Status.dnd:
            return "⛔ не беспокоить"


def setup(bot):
    bot.add_cog(Profile(bot, servers_data))
