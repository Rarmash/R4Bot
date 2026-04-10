import json

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from modules.firebase import get_all_records, filter_records_by_quantity
from options import servers_data


# Helper function to generate a leaderboard string for display
def generate_leaderboard_string(data_list):
    # Create a formatted leaderboard string with medals for the top 3 users
    # and numbering for others (up to 10 users).
    desk = '\n'.join(
        [f'{("🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else str(i + 1) + ".")} <@{user[0]}>: {user[1]}'
         for i, user in enumerate(data_list[:10])])
    return desk


class Leaderboards(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    leaderboard_cmd = SlashCommandGroup("leaderboard", "Таблицы лидеров")

    # Slash command to view the leaderboard for timeouts
    @leaderboard_cmd.command(description='Посмотреть таблицу лидеров по тайм-аутам')
    @discord.guild_only()
    async def timeouts(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        users = get_all_records(str(ctx.guild.id), "Users")
        new_leaderboard = []

        # Filter users with non-zero timeouts and store them in a new leaderboard
        for user_id, user_data in users.items():
            if user_data.get("timeouts", 0) != 0:
                new_leaderboard.append([user_id, user_data.get("timeouts", 0)])

        # Sort the new leaderboard based on the number of timeouts in descending order
        new_leaderboard.sort(key=lambda items: items[1], reverse=True)

        # Calculate the total number of timeouts
        kolvo = sum(user[1] for user in new_leaderboard)

        # Generate the formatted leaderboard string
        data_list = generate_leaderboard_string(new_leaderboard)

        # Create and send the leaderboard embed
        embed = discord.Embed(title='Лидеры по тайм-аутам',
                              description=data_list, color=int(server_data.get("accent_color"), 16))
        embed.set_footer(text=f"Всего получено {kolvo} тайм-аутов")
        await ctx.respond(embed=embed)

    # Command to view the leaderboard for messages
    @leaderboard_cmd.command(description='Посмотреть таблицу лидеров по сообщениям')
    @discord.guild_only()
    async def messages(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        users = json.loads(filter_records_by_quantity(str(ctx.guild.id), "Users", "messages", 1))
        new_leaderboard = [[user_id, user_data.get("messages", 0)] for user_id, user_data in users.items()]

        # Sort the new leaderboard based on the number of messages in descending order
        new_leaderboard.sort(key=lambda items: items[1], reverse=True)

        # Calculate the total number of messages
        kolvo = sum(user[1] for user in new_leaderboard)

        # Generate the formatted leaderboard string
        data_list = generate_leaderboard_string(new_leaderboard)
        embed = discord.Embed(title='Лидеры по сообщениям',
                              description=data_list, color=int(server_data.get("accent_color"), 16))

        # Create and send the leaderboard embed
        embed = discord.Embed(title='Лидеры по сообщениям', description=data_list,
                              color=int(server_data.get("accent_color"), 16))

        # Check the author's position in the leaderboard and display accordingly
        user_id = str(ctx.author.id)
        for i, user in enumerate(new_leaderboard):
            if user[0] == user_id and i >= 10:
                embed.add_field(name="Ваше положение в таблице", value=f'{i + 1}. <@{user[0]}>: {user[1]}\n')
                break
            elif user[0] == user_id:
                break

        # Set the footer text based on the number of users in the leaderboard
        if len(new_leaderboard) <= 10 or i + 1 <= 10:
            embed.set_footer(text=f"Всего отправлено {kolvo} сообщений")
        else:
            place10 = new_leaderboard[9][1]
            urplace = new_leaderboard[i][1] if i >= 10 else 0
            embed.set_footer(text=f"Вам осталось {place10 - urplace + 1} сообщений до 10-го места")

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Leaderboards(bot, servers_data))
