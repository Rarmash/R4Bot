import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from options import myclient, servers_data

class Leaderboards(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data
    
    leaderboardcmd = SlashCommandGroup("leaderboard", "Таблицы лидеров")
    
    # Helper function to generate a leaderboard string for display
    def generate_leaderboard_string(self, data_list):
        # Create a formatted leaderboard string with medals for the top 3 users
        # and numbering for others (up to 10 users).
        desk = '\n'.join([f'{("🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else str(i+1)+".")} <@{user[0]}>: {user[1]}' for i, user in enumerate(data_list[:10])])
        return desk
    
    # Slash command to view the leaderboard for timeouts
    @leaderboardcmd.command(description='Посмотреть таблицу лидеров по тайм-аутам')
    async def timeouts(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        
        Collection = myclient[f"{str(ctx.guild.id)}"]["Users"]
        users = Collection.find({})
        new_leaderboard = []
        
        # Filter users with non-zero timeouts and store them in a new leaderboard
        for user in users:
            if user.get("timeouts", 0) != 0:
                new_leaderboard.append([user["_id"], user.get("timeouts", 0)])
                
        # Sort the new leaderboard based on the number of timeouts in descending order
        new_leaderboard.sort(key=lambda items: items[1], reverse=True)
        
        # Calculate the total number of timeouts
        kolvo = sum(user[1] for user in new_leaderboard)
        
        # Generate the formatted leaderboard string
        data_list = self.generate_leaderboard_string(new_leaderboard)
        
        # Create and send the leaderboard embed
        embed = discord.Embed(title='Лидеры по тайм-аутам',
                              description=data_list, color=int(server_data.get("accent_color"), 16))
        embed.set_footer(text=f"Всего получено {kolvo} тайм-аутов")
        await ctx.respond(embed=embed)
        
    # Command to view the leaderboard for messages
    @leaderboardcmd.command(description='Посмотреть таблицу лидеров по сообщениям')
    async def messages(self, ctx):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        
        Collection = myclient[f"{str(ctx.guild.id)}"]["Users"]
        users = Collection.find({"messages": {"$ne": 0}})
        new_leaderboard = [[user["_id"], user.get("messages", 0)] for user in users]
        
         # Sort the new leaderboard based on the number of messages in descending order
        new_leaderboard.sort(key=lambda items: items[1], reverse=True)
        
        # Calculate the total number of messages
        kolvo = sum(user[1] for user in new_leaderboard)
        
        # Generate the formatted leaderboard string
        data_list = self.generate_leaderboard_string(new_leaderboard)
        embed = discord.Embed(title='Лидеры по сообщениям',
                              description=data_list, color=int(server_data.get("accent_color"), 16))
        
        # Create and send the leaderboard embed
        embed = discord.Embed(title='Лидеры по сообщениям', description=data_list, color=int(server_data.get("accent_color"), 16))
        
        # Check the author's position in the leaderboard and display accordingly
        user_id = str(ctx.author.id)
        for i, user in enumerate(new_leaderboard):
            if user[0] == user_id and i >= 10:
                embed.add_field(name="Ваше положение в таблице", value=f'{i+1}. <@{user[0]}>: {user[1]}\n')
                break
        
        # Set the footer text based on the number of users in the leaderboard
        if len(new_leaderboard) <= 10:
            embed.set_footer(text=f"Всего отправлено {kolvo} сообщений")
        else:
            place10 = new_leaderboard[9][1]
            urplace = new_leaderboard[i][1] if i >= 10 else 0
            embed.set_footer(text=f"Вам осталось {place10-urplace+1} сообщений до 10-го места")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Leaderboards(bot, servers_data))