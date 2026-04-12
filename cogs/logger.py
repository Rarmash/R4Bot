import io

import discord
from discord.ext import commands

from modules.firebase import create_record, get_from_record, update_record
from options import servers_data


def is_channel_allowed(channel_id, server_data):
    return channel_id not in server_data.get("bannedChannels", [])


def is_user_allowed(user_id, server_data):
    return user_id not in server_data.get("bannedUsers", [])


def is_category_allowed(category_id, server_data):
    return category_id not in server_data.get("bannedCategories", [])


class Logger(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    def should_log_message(self, message, server_data) -> bool:
        return (
            is_channel_allowed(message.channel.id, server_data)
            and is_user_allowed(message.author.id, server_data)
            and is_category_allowed(message.channel.category_id, server_data)
        )

    @commands.Cog.listener()
    async def on_message_delete(self, ctx):
        if ctx.guild is None or ctx.author.bot:
            return

        server_data = self.get_server_data(ctx.guild.id)
        if not server_data or not self.should_log_message(ctx, server_data):
            return

        channel = self.bot.get_channel(server_data.get("log_channel"))
        if channel is None:
            return

        author_id = str(ctx.author.id)
        user = get_from_record(str(ctx.guild.id), "Users", author_id)
        if user:
            update_record(str(ctx.guild.id), "Users", author_id, {"messages": user.get("messages", 0) - 1})
        else:
            create_record(str(ctx.guild.id), "Users", author_id, {"messages": -1, "timeouts": 0})

        embed = discord.Embed(
            title="Удалённое сообщение",
            description=ctx.content,
            color=int(server_data.get("accent_color"), 16),
        )
        embed.add_field(name="Автор", value=f"<@{author_id}>")
        embed.add_field(name="Канал", value=f"<#{ctx.channel.id}>")

        if not ctx.attachments:
            await channel.send(embed=embed)
            return

        attachment = ctx.attachments[0]
        attachment_bytes = io.BytesIO(await attachment.read())
        await channel.send(file=discord.File(attachment_bytes, attachment.filename), embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild is None or before.author.bot:
            return

        server_data = self.get_server_data(before.guild.id)
        if not server_data:
            return

        if not self.should_log_message(before, server_data) or before.content == after.content:
            return

        channel = self.bot.get_channel(server_data.get("log_channel"))
        if channel is None:
            return

        embed = discord.Embed(color=int(server_data.get("accent_color"), 16))
        embed.add_field(name="Редактированное сообщение", value=after.content, inline=False)
        embed.add_field(name="Оригинальное сообщение", value=before.content, inline=False)
        embed.add_field(name="Автор", value=f"<@{before.author.id}>")
        embed.add_field(name="Канал", value=f"<#{before.channel.id}>")
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Logger(bot, servers_data))
