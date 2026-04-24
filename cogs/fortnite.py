import discord
import requests
from discord.commands import SlashCommandGroup
from discord.ext import commands

from modules.firebase import get_from_record, search_record_id, update_record
from options import fortniteapi, servers_data

FORTNITE_API_BASE = "https://fortnite-api.com"
FORTNITE_HEADERS = {"Authorization": fortniteapi}


def fortnite_api_request(endpoint, **params):
    response = requests.get(
        f"{FORTNITE_API_BASE}/{endpoint}",
        params=params,
        headers=FORTNITE_HEADERS,
        timeout=30,
    )
    payload = response.json()
    return payload.get("data"), payload.get("status")


def fortnite_api_request_by_id(account_id):
    return fortnite_api_request(f"v2/stats/br/v2/{account_id}")


def fortnite_api_request_by_username(username):
    return fortnite_api_request("v2/stats/br/v2", name=username, displayName=username)


def get_fortnite_id(username):
    data, status = fortnite_api_request_by_username(username)
    account = (data or {}).get("account", {})
    return account.get("id"), status


def get_fortnite_record(ctx, username):
    if username:
        return username

    author_id = str(ctx.author.id)
    user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
    return user_data.get("fortnite") if user_data else None


def get_fortnite_username_to_profile(account_id):
    data, _ = fortnite_api_request_by_id(account_id)
    return (data or {}).get("account", {}).get("name")


class Fortnite(commands.Cog):
    fortnite = SlashCommandGroup("fortnite", "Команды по Fortnite")

    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    @fortnite.command(description="Посмотреть статистику по игроку")
    @discord.option("username", description="Имя игрока", required=False)
    async def stats(self, ctx: discord.ApplicationContext, username: str):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        await ctx.defer()

        use_account_id = not bool(username)
        username = get_fortnite_record(ctx, username)
        if not username:
            await ctx.respond(
                "Вы не привязали профиль Fortnite к учётной записи Discord. Сделайте это, используя команду "
                "`/fortnite connect <username>`!",
            )
            return

        if use_account_id:
            stats_data, status = fortnite_api_request_by_id(username)
        else:
            stats_data, status = fortnite_api_request_by_username(username)

        if status == 403:
            guide_files = [discord.File(f"resources/fortnite/fortnitestatsguide{i}.png") for i in range(1, 4)]
            await ctx.respond(
                f"❗ Данные игрока **{username}** скрыты (ошибка **{status}**).\n"
                "Если это Ваш аккаунт, откройте статистику в настройках игры.",
                files=guide_files,
            )
            return
        if status == 404:
            await ctx.respond(f"❗ Игрок **{username}** не найден (ошибка **{status}**).")
            return
        if status == 503:
            await ctx.respond("❗ Модуль Fortnite в данный момент перезагружается, обычно это занимает несколько минут. Пожалуйста, подождите...")
            return
        if status != 200 or not stats_data:
            await ctx.respond(f"❓ Возникла ошибка **{status}**...")
            return

        try:
            overall = stats_data["stats"]["all"]["overall"]
            embed = discord.Embed(
                title=f'Статистика игрока {stats_data["account"]["name"]}',
                color=int(server_data.get("accent_color"), 16),
            )
            embed.add_field(name="🎟️ Уровень боевого пропуска", value=f'{stats_data["battlePass"]["level"]}')
            embed.add_field(name="🎮 Всего матчей сыграно", value=f'{overall["matches"]}')
            embed.add_field(name="👑 Всего побед", value=f'{overall["wins"]}')
            embed.add_field(name="🎖 Всего топ-3", value=f'{overall["top3"]}')
            embed.add_field(name="🎖 Всего топ-5", value=f'{overall["top5"]}')
            embed.add_field(name="🎖 Всего топ-10", value=f'{overall["top10"]}')
            embed.add_field(name="🎖 Всего топ-25", value=f'{overall["top25"]}')
            embed.add_field(name="💀 Всего убийств", value=f'{overall["kills"]}')
            embed.add_field(name="☠️ Убийств в минуту", value=f'{overall["killsPerMin"]}')
            embed.add_field(name="☠️ Убийств за матч", value=f'{overall["killsPerMatch"]}')
            embed.add_field(name="⚰️ Всего смертей", value=f'{overall["deaths"]}')
            embed.add_field(name="📈 Общее K/D", value=f'{overall["kd"]}')
            embed.add_field(name="📉 % побед", value=f'{overall["winRate"]}')
            embed.add_field(name="🕓 Всего сыграно минут", value=f'{overall["minutesPlayed"]}')
            embed.add_field(name="🙋‍♂️ Всего игроков пережито", value=f'{overall["playersOutlived"]}')

            try:
                embed.add_field(
                    name="Владелец профиля",
                    value=f"<@{search_record_id(str(ctx.guild.id), 'Users', 'fortnite', stats_data['account']['id'])}>",
                )
            except IndexError:
                pass

            await ctx.respond(embed=embed)
        except KeyError:
            await ctx.respond("Ошибка при получении статистики.")

    @fortnite.command(description="Посмотреть карту")
    async def map(self, ctx: discord.ApplicationContext):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        try:
            response = requests.get(f"{FORTNITE_API_BASE}/v1/map", headers=FORTNITE_HEADERS, timeout=30)
            payload = response.json()
            map_data = payload.get("data", {}).get("images", {}).get("pois")
        except requests.RequestException:
            map_data = None

        if not map_data:
            await ctx.respond("Ошибка при получении данных карты.")
            return

        embed = discord.Embed(title="Карта Fortnite", color=int(server_data.get("accent_color"), 16))
        embed.set_image(url=map_data)
        await ctx.respond(embed=embed)

    @fortnite.command(description="Привязать профиль Fortnite к учётной записи Discord")
    @discord.option("username", description="Имя игрока")
    @discord.guild_only()
    async def connect(self, ctx: discord.ApplicationContext, username: str):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        await ctx.defer()
        author_id = str(ctx.author.id)

        user_id, status = get_fortnite_id(username)
        if status == 503:
            await ctx.respond("❗ Модуль Fortnite в данный момент перезагружается, обычно это занимает несколько минут. Пожалуйста, подождите...")
            return
        if status != 200 or not user_id:
            await ctx.respond(f"При добавлении возникла ошибка **{status}**.\nВозможно, Вы неверно указали никнейм.")
            return

        update_record(str(ctx.guild.id), "Users", author_id, {"fortnite": user_id})
        embed = discord.Embed(
            description=(
                f"Аккаунт **{username}** был успешно привязан к Вашей учётной записи!\n"
                "Если Вы измените никнейм, здесь его менять не будет нужно."
            ),
            color=int(server_data.get("accent_color"), 16),
        )
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Fortnite(bot, servers_data))
