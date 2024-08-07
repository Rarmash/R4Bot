import discord
import requests
from discord.commands import SlashCommandGroup
from discord.ext import commands

from modules.firebase import update_record, get_from_record, search_record_id
from options import fortniteapi, servers_data


# Helper function to make a request to the Fortnite API
def fortnite_api_request_by_id(accountId):
    request_url = f"https://fortnite-api.com/v2/stats/br/v2/{accountId}"
    response = requests.get(request_url, headers={"Authorization": fortniteapi})
    response_data = response.json()
    return response_data.get("data"), response_data.get("status")


# Helper function to make a request to the Fortnite API
def fortnite_api_request_by_username(username):
    request_url = f"https://fortnite-api.com/v2/stats/br/v2?name={username}"
    response = requests.get(request_url, params={"displayName": username}, headers={"Authorization": fortniteapi})
    response_data = response.json()
    return response_data.get("data"), response_data.get("status")


# Helper function to get the Fortnite ID for the user
def get_fortnite_id(username):
    request_url = f"https://fortnite-api.com/v2/stats/br/v2?name={username}"
    response = requests.get(request_url, params={"displayName": username}, headers={"Authorization": fortniteapi})
    response_data = response.json()
    print(response_data)
    return response_data.get("data").get("account").get("id"), response_data.get("status")


# Helper function to get the Fortnite username for the user
def get_fortnite_record(ctx, username):
    if not username:
        author_id = str(ctx.author.id)
        user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
        if user_data:
            username = user_data.get("fortnite")

    return username


class Fortnite(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    fortnite = SlashCommandGroup("fortnite", "Команды по Fortnite")

    # Command to view Fortnite stats for a player
    @fortnite.command(description='Посмотреть статистику по игроку')
    @discord.option("username", description="Имя игрока", required=False)
    async def stats(self, ctx: discord.ApplicationContext, username: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        await ctx.defer()

        if not username:
            flag = True
        else:
            flag = False

        # Get the Fortnite username for the player
        username = get_fortnite_record(ctx, username)
        # Check if the Fortnite username is available
        if not username:
            await ctx.respond(
                "Вы не привязали профиль Fortnite к учётной записи Discord. Сделайте это, используя команду "
                "`/fortnite connect <username>`!")
            return

        # Make a request to the Fortnite API for the stats data
        if flag:
            stats_data, status = fortnite_api_request_by_id(username)
        else:
            stats_data, status = fortnite_api_request_by_username(username)

        # Handle different status codes
        if status == 403:
            guide_files = [discord.File(f'resources/fortnite/fortnitestatsguide{i}.png') for i in range(1, 4)]
            await ctx.respond(
                f"❗ Данные игрока **{username}** скрыты (ошибка **{status}**).\nЕсли это ваш аккаунт, откройте статистику в настройках игры.",
                files=guide_files)
            return
        elif status == 404:
            await ctx.respond(f"❗ Игрок **{username}** не найден (ошибка **{status}**).")
            return
        elif status != 200:
            await ctx.respond(f"❓ Возникла ошибка **{status}**...")
            return
        try:
            print(stats_data)
            # Create and send the stats embed
            embed = discord.Embed(title=f'Статистика игрока {stats_data["account"]["name"]}',
                                  color=int(server_data.get("accent_color"), 16))
            embed.add_field(name="🎟️ Уровень боевого пропуска", value=f'{stats_data["battlePass"]["level"]}')
            embed.add_field(name="🎮 Всего матчей сыграно", value=f'{stats_data["stats"]["all"]["overall"]["matches"]}')
            embed.add_field(name="👑 Всего побед", value=f'{stats_data["stats"]["all"]["overall"]["wins"]}')
            embed.add_field(name="🎖 Всего топ-3", value=f'{stats_data["stats"]["all"]["overall"]["top3"]}')
            embed.add_field(name="🎖 Всего топ-5", value=f'{stats_data["stats"]["all"]["overall"]["top5"]}')
            embed.add_field(name="🎖 Всего топ-10", value=f'{stats_data["stats"]["all"]["overall"]["top10"]}')
            embed.add_field(name="🎖 Всего топ-25", value=f'{stats_data["stats"]["all"]["overall"]["top25"]}')
            embed.add_field(name="💀 Всего убийств", value=f'{stats_data["stats"]["all"]["overall"]["kills"]}')
            embed.add_field(name="☠️ Убийств в минуту", value=f'{stats_data["stats"]["all"]["overall"]["killsPerMin"]}')
            embed.add_field(name="☠️ Убийств за матч",
                            value=f'{stats_data["stats"]["all"]["overall"]["killsPerMatch"]}')
            embed.add_field(name="⚰️ Всего смертей", value=f'{stats_data["stats"]["all"]["overall"]["deaths"]}')
            embed.add_field(name="📈 Общее K/D", value=f'{stats_data["stats"]["all"]["overall"]["kd"]}')
            embed.add_field(name="📉 % побед", value=f'{stats_data["stats"]["all"]["overall"]["winRate"]}')
            embed.add_field(name="🕓 Всего сыграно минут",
                            value=f'{stats_data["stats"]["all"]["overall"]["minutesPlayed"]}')
            embed.add_field(name="🙋‍♂️ Всего игроков пережито",
                            value=f'{stats_data["stats"]["all"]["overall"]["playersOutlived"]}')

            # Add the owner of the profile if available in the database
            try:
                embed.add_field(name="Владелец профиля",
                                value=f"<@{search_record_id(str(ctx.guild.id), 'Users', 'fortnite', username)}>")
            except IndexError:
                pass
            await ctx.respond(embed=embed)
        except KeyError:
            await ctx.respond("Ошибка при получении статистики.")

    # Command to view the Fortnite map
    @fortnite.command(description='Посмотреть карту')
    async def map(self, ctx: discord.ApplicationContext):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        request_url = "https://fortnite-api.com/v1/map"
        response = requests.get(request_url, headers={"Authorization": fortniteapi})
        map_data = response.json().get("data", {}).get("images", {}).get("pois", None)

        if not map_data:
            await ctx.respond("Ошибка при получении данных карты.")
            return

        embed = discord.Embed(title='Карта Fortnite', color=int(server_data.get("accent_color"), 16))
        embed.set_image(url=map_data)
        await ctx.respond(embed=embed)

    @fortnite.command(description='Привязать профиль Fortnite к учётной записи Discord')
    @discord.option("username", description="Имя игрока")
    @discord.guild_only()
    async def connect(self, ctx: discord.ApplicationContext, username: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        await ctx.defer()
        author_id = str(ctx.author.id)

        user_id, status = get_fortnite_id(username)
        if status != 200 or not user_id:
            await ctx.respond(f"При добавлении возникла ошибка **{status}**.\nВозможно, вы неверно указали никнейм.")
            return

        update_record(str(ctx.guild.id), "Users", author_id, {"fortnite": user_id})
        embed = discord.Embed(
            description=f"Аккаунт **{username}** был успешно привязан к вашей учётной записи!\n"
                        f"Если вы измените никнейм, здесь его менять не будет нужно.",
            color=int(server_data.get("accent_color"), 16))
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Fortnite(bot, servers_data))
