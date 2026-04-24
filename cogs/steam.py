import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import discord
import requests
from discord.commands import SlashCommandGroup
from discord.ext import commands

import options
from modules.firebase import get_from_record, search_record_id, update_record
from modules.server_config import respond_missing_server_config
from options import servers_data

STEAM_API_BASE = "https://api.steampowered.com"
ENGLISH_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
STEAM_COMMUNITY_HEADERS = {
    "User-Agent": "R4Bot/1.0",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_steam_id(ctx, steamid64, url_or_username=None):
    if steamid64:
        return steamid64
    if url_or_username:
        return None

    author_id = str(ctx.author.id)
    user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
    return user_data.get("steam") if user_data else None


def parse_steam_identity(steamid64=None, url_or_username=None):
    if steamid64:
        return steamid64, None
    if not url_or_username:
        return None, None

    url_or_username = str(url_or_username).strip().rstrip("/")

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


def resolve_vanity_via_community(vanity: str):
    response = requests.get(
        f"https://steamcommunity.com/id/{vanity}/?xml=1",
        timeout=30,
        headers=STEAM_COMMUNITY_HEADERS,
    )
    response.raise_for_status()

    match = re.search(r"<steamID64>\s*(\d+)\s*</steamID64>", response.text)
    return match.group(1) if match else None


def resolve_steam_id(steamid64=None, url_or_username=None):
    direct_steam_id, vanity = parse_steam_identity(steamid64=steamid64, url_or_username=url_or_username)
    if direct_steam_id:
        return str(direct_steam_id)
    if not vanity:
        return None

    try:
        payload = steam_api_get("ISteamUser/ResolveVanityURL/v0001/", vanityurl=vanity)
        response = payload.get("response", {})
        if response.get("success") == 1:
            return response.get("steamid")
    except requests.ConnectionError:
        pass

    return resolve_vanity_via_community(vanity)


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
    return payload.get("response", {}).get("player_level")


def normalize_profile_url(summary, steam_id):
    profile_url = summary.get("profileurl")
    return profile_url or (f"https://steamcommunity.com/profiles/{steam_id}" if steam_id else None)


def parse_english_date_to_timestamp(member_since: str):
    date_match = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", member_since)
    if not date_match:
        return None

    month_name, day, year = date_match.groups()
    month = ENGLISH_MONTHS.get(month_name.casefold())
    if month is None:
        return None

    try:
        created_at = datetime(int(year), month, int(day), tzinfo=timezone.utc)
    except ValueError:
        return None

    return int(created_at.timestamp())


def extract_creation_timestamp_from_text(text: str):
    patterns = [
        r"<memberSince>\s*([^<]+)\s*</memberSince>",
        r"Member since[^A-Za-z0-9]+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        r"member_since[^A-Za-z0-9]+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        timestamp = parse_english_date_to_timestamp(match.group(1).strip())
        if timestamp:
            return timestamp

    return None


def get_profile_creation_timestamp(summary, steam_id):
    time_created = summary.get("timecreated")
    if time_created:
        return time_created

    profile_url = normalize_profile_url(summary, steam_id)
    if not profile_url:
        return None

    xml_response = requests.get(
        f"{profile_url.rstrip('/')}/?xml=1",
        timeout=30,
        headers=STEAM_COMMUNITY_HEADERS,
    )
    xml_response.raise_for_status()

    timestamp = extract_creation_timestamp_from_text(xml_response.text)
    if timestamp:
        return timestamp

    html_response = requests.get(
        profile_url,
        timeout=30,
        headers=STEAM_COMMUNITY_HEADERS,
    )
    html_response.raise_for_status()
    return extract_creation_timestamp_from_text(html_response.text)


class Steam(commands.Cog):
    steam = SlashCommandGroup("steam", "Команды по Steam")

    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

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
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
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
            embed.add_field(name="Дата выпуска", value=app_data.get("release_date", {}).get("date", "Неизвестно"))
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
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
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

        profile_url = normalize_profile_url(summary, steam_id)
        is_private_profile = summary.get("communityvisibilitystate", 1) != 3

        economy_ban = bans.get("EconomyBan", "none")

        embed.add_field(name="VAC-баны", value="Имеются" if bans.get("NumberOfVACBans", 0) != 0 else "Отсутствуют")
        embed.add_field(name="Игровые баны", value="Имеются" if bans.get("NumberOfGameBans", 0) != 0 else "Отсутствуют")
        embed.add_field(name="Trade-бан", value="Есть" if str(economy_ban).lower() not in {"none", "0", ""} else "Отсутствует")
        embed.add_field(name="Ссылка на профиль", value=f"[Тык]({profile_url})" if profile_url else "Отсутствует")

        if is_private_profile:
            embed.add_field(name="Статус профиля", value="Приватный")
        else:
            try:
                time_created = get_profile_creation_timestamp(summary, steam_id)
            except requests.RequestException:
                time_created = summary.get("timecreated")

            embed.add_field(name="Аккаунт создан", value=f"<t:{time_created}:D>" if time_created else "Отсутствует")
            embed.add_field(name="Настоящее имя", value=summary.get("realname") or "Отсутствует")
            embed.add_field(name="Местоположение", value=summary.get("loccountrycode") or "Отсутствует")
            embed.add_field(name="Лимит на аккаунте ($5)", value="Имеется" if (player_level or 0) == 0 else "Отсутствует")

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
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
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
