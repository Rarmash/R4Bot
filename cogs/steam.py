from urllib.parse import urlparse

import discord
import requests
from discord.commands import SlashCommandGroup
from discord.ext import commands

import options
from modules.firebase import get_from_record, search_record_id, update_record
from options import servers_data

STEAM_API_BASE = "https://api.steampowered.com"


def get_steam_id(ctx, steamid64, url_or_username=None):
    if steamid64:
        return steamid64

    if url_or_username:
        return None

    author_id = str(ctx.author.id)
    user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
    if user_data:
        return user_data.get("steam")
    return None


def parse_steam_identity(steamid64=None, url_or_username=None):
    if steamid64:
        return steamid64, None

    if not url_or_username:
        return None, None

    parsed = urlparse(url_or_username)
    if parsed.netloc:
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] == "profiles":
            return path_parts[1], None
        if len(path_parts) >= 2 and path_parts[0] == "id":
            return None, path_parts[1]

    return (url_or_username, None) if str(url_or_username).isdigit() else (None, url_or_username)


def steam_api_get(endpoint, **params):
    response = requests.get(
        f"{STEAM_API_BASE}/{endpoint}",
        params={"key": options.steamapi, **params},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def resolve_steam_id(steamid64=None, url_or_username=None):
    direct_steam_id, vanity = parse_steam_identity(steamid64=steamid64, url_or_username=url_or_username)
    if direct_steam_id:
        return str(direct_steam_id)

    if not vanity:
        return None

    payload = steam_api_get("ISteamUser/ResolveVanityURL/v0001/", vanityurl=vanity)
    response = payload.get("response", {})
    if response.get("success") != 1:
        return None
    return response.get("steamid")


def get_player_summary(steam_id):
    payload = steam_api_get("ISteamUser/GetPlayerSummaries/v0002/", steamids=steam_id)
    players = payload.get("response", {}).get("players", [])
    return players[0] if players else None


def get_player_bans(steam_id):
    payload = steam_api_get("ISteamUser/GetPlayerBans/v1/", steamids=steam_id)
    players = payload.get("players", [])
    return players[0] if players else None


def get_player_level(steam_id):
    payload = steam_api_get("IPlayerService/GetSteamLevel/v1/", steamid=steam_id)
    response = payload.get("response", {})
    return response.get("player_level")


def normalize_profile_url(summary, steam_id):
    profile_url = summary.get("profileurl")
    if profile_url:
        return profile_url
    return f"https://steamcommunity.com/profiles/{steam_id}" if steam_id else None


class Steam(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    steam = SlashCommandGroup("steam", "Команды по Steam")

    @staticmethod
    def get_steam_error_message(error):
        if isinstance(error, requests.HTTPError) and error.response is not None:
            if error.response.status_code == 403:
                return (
                    "Официальный Steam Web API отклонил ключ доступа. "
                    "Сейчас в `STEAMAPI` нужен настоящий Steam Web API key, а не ключ стороннего сервиса."
                )
            return f"Steam Web API вернул ошибку **{error.response.status_code}**."
        return f"Не удалось получить данные Steam: {error}"

    @steam.command(description="Посмотреть данные об игре")
    @discord.option("appid", description="ID игры в Steam")
    @discord.option("countrycode", description="Код страны", choices=["RU", "US", "TR", "AR", "DE", "UA", "KZ"])
    async def price(self, ctx: discord.ApplicationContext, appid: int, countrycode: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        steam_url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc={countrycode}&l=ru"
        try:
            response = requests.get(steam_url, timeout=30)
            response.raise_for_status()
            payload = response.json()

            if not payload.get(f"{appid}", {}).get("success"):
                await ctx.respond(f"Такой игры не существует или она недоступна в регионе **{countrycode}**.")
                return

            app_data = payload[f"{appid}"]["data"]

            embed = discord.Embed(
                title=app_data.get("name"),
                description=app_data.get("short_description"),
                color=int(server_data.get("accent_color"), 16),
            )
            embed.set_thumbnail(url=app_data.get("header_image"))
            embed.add_field(
                name="Дата выпуска",
                value=app_data.get("release_date", {}).get("date", "Неизвестно"),
            )
            embed.add_field(name="Разработчик", value=", ".join(app_data.get("developers", [])) or "Неизвестно")
            embed.add_field(name="Издатель", value=", ".join(app_data.get("publishers", [])) or "Неизвестно")

            if app_data.get("is_free", False):
                embed.add_field(name="Стоимость", value="Бесплатно")
            else:
                price_data = app_data.get("price_overview", {})
                discount_percent = price_data.get("discount_percent", 0)
                final_price = price_data.get("final_formatted", "Неизвестно")
                embed.add_field(
                    name="Стоимость",
                    value=f"{final_price} (-{discount_percent}%)" if discount_percent else final_price,
                )

            embed.add_field(name="Страница в Steam", value=f"[Тык](https://store.steampowered.com/app/{appid}/)")
            embed.add_field(name="SteamDB", value=f"[Тык](https://steamdb.info/app/{appid}/)")
            await ctx.respond(embed=embed)
        except requests.RequestException:
            await ctx.respond("Ошибка при запросе к API Steam.")

    @steam.command(description="Посмотреть информацию по пользователю Steam")
    @discord.option("steamid64", description="SteamID64", required=False)
    @discord.option("url_or_username", description="Ссылка на профиль или имя пользователя после ../id/", required=False)
    async def profile(self, ctx: discord.ApplicationContext, steamid64: str, url_or_username: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        await ctx.defer()

        steamid64 = get_steam_id(ctx, steamid64, url_or_username)
        if not steamid64 and not url_or_username:
            await ctx.respond("Ты не привязал профиль Steam к учётной записи Discord. Сделай это командой `/steam connect`.")
            return

        try:
            steam_id = resolve_steam_id(steamid64=steamid64, url_or_username=url_or_username)
            if not steam_id:
                await ctx.respond("Профиль Steam не найден.")
                return

            summary = get_player_summary(steam_id)
            if not summary:
                await ctx.respond("Профиль Steam не найден.")
                return

            bans = get_player_bans(steam_id) or {}
            player_level = get_player_level(steam_id)
        except requests.RequestException as error:
            await ctx.respond(self.get_steam_error_message(error))
            return

        persona_name = summary.get("personaname", "Неизвестный пользователь")
        embed = discord.Embed(
            title=f"Карточка игрока {persona_name}",
            color=int(server_data.get("accent_color"), 16),
        )
        embed.add_field(name="SteamID64", value=f"`{steam_id}`")
        embed.set_thumbnail(url=summary.get("avatarfull"))

        time_created = summary.get("timecreated")
        embed.add_field(name="Аккаунт создан", value=f"<t:{time_created}:D>" if time_created else "Отсутствует")
        embed.add_field(name="Настоящее имя", value=summary.get("realname") or "Отсутствует")
        embed.add_field(name="Местоположение", value=summary.get("loccountrycode") or "Отсутствует")
        embed.add_field(
            name="VAC-баны",
            value="Имеются" if bans.get("NumberOfVACBans", 0) != 0 else "Отсутствуют",
        )
        economy_ban = bans.get("EconomyBan", "none")
        embed.add_field(
            name="Trade-бан",
            value="Есть" if str(economy_ban).lower() not in {"none", "0", ""} else "Отсутствует",
        )
        embed.add_field(
            name="Лимит на аккаунте ($5)",
            value="Имеется" if (player_level or 0) == 0 else "Отсутствует",
        )

        profile_url = normalize_profile_url(summary, steam_id)
        embed.add_field(name="Ссылка на профиль", value=f"[Тык]({profile_url})" if profile_url else "Отсутствует")

        try:
            embed.add_field(
                name="Владелец профиля",
                value=f"<@{search_record_id(str(ctx.guild.id), 'Users', 'steam', str(steam_id))}>",
            )
        except IndexError:
            pass

        await ctx.respond(embed=embed)

    @steam.command(description="Привязать профиль Steam к учётной записи Discord")
    @discord.option("steamid64", description="SteamID64", required=False)
    @discord.option("url_or_username", description="Ссылка на профиль или имя пользователя после ../id/", required=False)
    async def connect(self, ctx: discord.ApplicationContext, steamid64: str, url_or_username: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        await ctx.defer()
        author_id = str(ctx.author.id)

        try:
            steam_id = resolve_steam_id(steamid64=steamid64, url_or_username=url_or_username)
            if not steam_id:
                await ctx.respond("Профиль Steam не найден.")
                return

            summary = get_player_summary(steam_id)
            if not summary:
                await ctx.respond("Профиль Steam не найден.")
                return
        except requests.RequestException as error:
            await ctx.respond(self.get_steam_error_message(error))
            return

        update_record(str(ctx.guild.id), "Users", author_id, {"steam": str(steam_id)})

        embed = discord.Embed(
            description=f"Аккаунт **{summary.get('personaname', 'Неизвестный пользователь')}** был успешно привязан к твоей учётной записи!",
            color=int(server_data.get("accent_color"), 16),
        )
        embed.set_thumbnail(url=summary.get("avatarfull"))
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Steam(bot, servers_data))
