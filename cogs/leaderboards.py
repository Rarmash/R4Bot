import json

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from modules.firebase import filter_records_by_quantity, get_all_records
from modules.server_config import respond_missing_server_config
from options import servers_data


def format_voice_duration(total_seconds):
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} ч {minutes} м"
    if minutes:
        return f"{minutes} м {seconds} с"
    return f"{seconds} с"


def generate_leaderboard_string(data_list, value_formatter=str):
    def get_place_icon(index):
        if index == 0:
            return "🥇"
        if index == 1:
            return "🥈"
        if index == 2:
            return "🥉"
        return f"{index + 1}."

    return "\n".join(
        f"{get_place_icon(index)} <@{user[0]}>: {value_formatter(user[1])}" for index, user in enumerate(data_list[:10])
    )


class Leaderboards(commands.Cog):
    leaderboard_cmd = SlashCommandGroup("leaderboard", "Таблицы лидеров")

    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    @leaderboard_cmd.command(description="Посмотреть таблицу лидеров по тайм-аутам")
    @discord.guild_only()
    async def timeouts(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
            return

        users = get_all_records(str(ctx.guild.id), "Users")
        leaderboard = [
            [user_id, user_data.get("timeouts", 0)]
            for user_id, user_data in users.items()
            if user_data.get("timeouts", 0) != 0
        ]
        leaderboard.sort(key=lambda items: items[1], reverse=True)

        total_timeouts = sum(user[1] for user in leaderboard)
        embed = discord.Embed(
            title="Лидеры по тайм-аутам",
            description=generate_leaderboard_string(leaderboard),
            color=int(server_data.get("accent_color"), 16),
        )
        embed.set_footer(text=f"Всего получено {total_timeouts} тайм-аутов")
        await ctx.respond(embed=embed)

    @leaderboard_cmd.command(description="Посмотреть таблицу лидеров по сообщениям")
    @discord.guild_only()
    async def messages(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
            return

        users = json.loads(filter_records_by_quantity(str(ctx.guild.id), "Users", "messages", 1))
        leaderboard = [[user_id, user_data.get("messages", 0)] for user_id, user_data in users.items()]
        leaderboard.sort(key=lambda items: items[1], reverse=True)

        total_messages = sum(user[1] for user in leaderboard)
        embed = discord.Embed(
            title="Лидеры по сообщениям",
            description=generate_leaderboard_string(leaderboard),
            color=int(server_data.get("accent_color"), 16),
        )

        author_id = str(ctx.author.id)
        author_position = next((index for index, user in enumerate(leaderboard) if user[0] == author_id), None)
        if author_position is not None and author_position >= 10:
            user = leaderboard[author_position]
            embed.add_field(
                name="Ваше положение в таблице",
                value=f"{author_position + 1}. <@{user[0]}>: {user[1]}\n",
            )

        if author_position is None or author_position < 10 or len(leaderboard) <= 10:
            embed.set_footer(text=f"Всего отправлено {total_messages} сообщений")
        else:
            tenth_place_messages = leaderboard[9][1]
            current_messages = leaderboard[author_position][1]
            embed.set_footer(text=f"Вам осталось {tenth_place_messages - current_messages + 1} сообщений до 10-го места")

        await ctx.respond(embed=embed)

    @leaderboard_cmd.command(description="Посмотреть таблицу лидеров по голосовой активности")
    @discord.guild_only()
    async def voice(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
            return

        users = get_all_records(str(ctx.guild.id), "Users") or {}
        leaderboard = [
            [user_id, user_data.get("voice", 0)]
            for user_id, user_data in users.items()
            if user_data.get("voice", 0) > 0
        ]
        leaderboard.sort(key=lambda items: items[1], reverse=True)

        total_voice_seconds = sum(user[1] for user in leaderboard)
        embed = discord.Embed(
            title="Лидеры по голосовой активности",
            description=generate_leaderboard_string(leaderboard, format_voice_duration),
            color=int(server_data.get("accent_color"), 16),
        )

        author_id = str(ctx.author.id)
        author_position = next((index for index, user in enumerate(leaderboard) if user[0] == author_id), None)
        if author_position is not None and author_position >= 10:
            user = leaderboard[author_position]
            embed.add_field(
                name="Ваше положение в таблице",
                value=f"{author_position + 1}. <@{user[0]}>: {format_voice_duration(user[1])}\n",
            )

        embed.set_footer(text=f"Всего наговорено {format_voice_duration(total_voice_seconds)}")
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Leaderboards(bot, servers_data))
