import io

import discord
from discord.ext import commands

from modules.firebase import get_from_record, create_record, update_record
from options import servers_data


# Helper functions to check if a channel, user, or category is allowed
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

    # Listen for the on_message_delete event to log deleted messages
    @commands.Cog.listener()
    async def on_message_delete(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        # Check if the channel, user, and category are allowed
        if not is_channel_allowed(ctx.channel.id, server_data) or \
                not is_user_allowed(ctx.author.id, server_data) or \
                not is_category_allowed(ctx.channel.category_id, server_data):
            return

        # Get the log channel
        channel = self.bot.get_channel(server_data.get("log_channel"))
        author_id = str(ctx.author.id)
        user = get_from_record(str(ctx.guild.id), "Users", author_id)
        if user:
            # Reduce the user's message count by 1
            update_record(str(ctx.guild.id), "Users", author_id, {"messages": user.get("messages", 0) - 1})
        else:
            create_record(str(ctx.guild.id), "Users", author_id, {"messages": -1, "timeouts": 0})

        # Create an embed to log the deleted message
        embed = discord.Embed(
            title='Удалённое сообщение',
            description=ctx.content,
            color=int(server_data.get("accent_color"), 16)
        )
        embed.add_field(
            name='Автор',
            value=f'<@{author_id}>'
        )
        embed.add_field(
            name='Канал',
            value=f'<#{ctx.channel.id}>'
        )

        # If the message had attachments, send the attachment along with the embed
        if ctx.attachments:
            attach = ctx.attachments[0]
            imgn = attach.filename
            img = io.BytesIO(await attach.read())
            try:
                await channel.send(file=discord.File(img, imgn), embed=embed)
            except UnboundLocalError:
                await channel.send(embed=embed)
        else:
            await channel.send(embed=embed)

    # Listen for the on_message_edit event to log message edits
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        guild_id = str(before.guild.id)
        server_data = self.servers_data.get(guild_id)
        if not server_data:
            return

        # Check if the channel, user, and category are allowed, and the content is changed
        if not is_channel_allowed(before.channel.id, server_data) or \
                not is_user_allowed(before.author.id, server_data) or \
                not is_category_allowed(before.channel.category_id, server_data) or \
                before.content == after.content:
            return

        # Get the log channel
        channel = self.bot.get_channel(server_data.get("log_channel"))

        # Create an embed to log the message edit
        embed = discord.Embed(
            color=int(server_data.get("accent_color"), 16)
        )
        embed.add_field(
            name="Редактированное сообщение",
            value=after.content,
            inline=False
        )
        embed.add_field(
            name="Оригинальное сообщение",
            value=before.content,
            inline=False
        )
        embed.add_field(
            name='Автор',
            value=f'<@{before.author.id}>'
        )
        embed.add_field(
            name='Канал',
            value=f'<#{before.channel.id}>'
        )

        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Logger(bot, servers_data))
