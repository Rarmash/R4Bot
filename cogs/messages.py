import datetime
import time
from math import ceil

import discord
from discord.ext import commands

from modules.firebase import create_record, delete_record, get_from_record, update_record
from options import servers_data


class MessagesCounter(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.guild is None or ctx.author.bot:
            return

        author = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        server_data = self.servers_data.get(guild_id)
        if not server_data:
            return

        if ctx.channel.id in server_data.get("trash_channels", []):
            return

        user = get_from_record(guild_id, "Users", author)
        if user:
            messages = user.get("messages", 0) + 1
            update_record(guild_id, "Users", author, {"messages": messages})
        else:
            create_record(guild_id, "Users", author, {"messages": 1, "timeouts": 0})

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        member_id = member.id
        guild_id = str(member.guild.id)
        server_data = self.servers_data.get(guild_id)
        if not server_data:
            return

        date_format = "%#d.%#m.%Y в %H:%M:%S"
        user = get_from_record(guild_id, "Users", str(member_id))
        channel = self.bot.get_channel(server_data.get("admin_channel"))
        if user and channel:
            joined_at_timestamp = ceil(
                time.mktime(
                    (
                        datetime.datetime.strptime(
                            str(member.joined_at.strftime(date_format)),
                            "%d.%m.%Y в %H:%M:%S",
                        )
                        + datetime.timedelta(hours=3)
                    ).timetuple()
                )
            )
            embed = discord.Embed(
                description=f"<@{member.id}> ({member.display_name}) вышел с сервера.",
                color=int(server_data.get("accent_color"), 16),
            )
            embed.add_field(
                name="Дата захода на сервер",
                value=f"<t:{joined_at_timestamp}:f>",
            )
            embed.add_field(name="Сообщений", value=user.get("messages", 0))
            embed.add_field(name="Таймаутов", value=user.get("timeouts", 0))

            if user["timeouts"] == 0:
                delete_record(guild_id, "Users", str(member_id))
            else:
                update_record(guild_id, "Users", str(member_id), {"messages": 0})

            await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(MessagesCounter(bot, servers_data))
