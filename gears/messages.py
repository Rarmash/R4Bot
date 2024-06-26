import datetime
import time
from math import ceil

import discord
from discord.ext import commands

from modules.firebase import create_record, update_record, get_from_record, delete_record
from options import servers_data


class MessagesCounter(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    # Listen for the on_message event to count messages
    @commands.Cog.listener()
    async def on_message(self, ctx):
        author = str(ctx.author.id)
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        # Check if the message is from a bot or in a trash channel
        if not ctx.author.bot and ctx.channel.id not in server_data.get("trash_channels", []):
            # Update or create the user's data in the database
            user = get_from_record(str(ctx.guild.id), "Users", author)
            if user:
                messages = user.get("messages", 0) + 1
                update_record(str(ctx.guild.id), "Users", author, {"messages": messages})
            else:
                create_record(str(ctx.guild.id), "Users", author, {"messages": 1, "timeouts": 0})

    # Listen for the on_member_remove event to handle user removal
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        member_id = member.id
        server_data = self.servers_data.get(str(member.guild.id))
        if not server_data:
            return
        date_format = "%#d.%#m.%Y в %H:%M:%S"
        user = get_from_record(str(member.guild.id), "Users", str(member_id))
        channel = self.bot.get_channel(server_data.get("admin_channel"))
        if user:
            # Create an embed with user data and send it to the admin channel
            embed = discord.Embed(
                description=f"<@{member.id}> ({member.display_name}) вышел с сервера.",
                color=int(server_data.get("accent_color"), 16)
            )
            embed.add_field(name="Дата захода на сервер",
                            value=f"<t:{ceil(time.mktime((datetime.datetime.strptime(str(member.joined_at.strftime(date_format)), '%d.%m.%Y в %H:%M:%S') + datetime.timedelta(hours=3)).timetuple()))}:f>")
            embed.add_field(name="Сообщений", value=user.get("messages", 0))
            embed.add_field(name="Таймаутов", value=user.get("timeouts", 0))
            # Delete the user's data from the database if there are no timeouts, otherwise reset the message count
            if user["timeouts"] == 0:
                delete_record(str(member.guild.id), "Users", str(member_id))
            else:
                update_record(str(member.guild.id), "Users", str(member_id), {"messages": 0})
            await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(MessagesCounter(bot, servers_data))
