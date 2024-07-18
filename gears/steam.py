import discord
import requests
from discord.commands import SlashCommandGroup
from discord.ext import commands

import options
from modules.firebase import update_record, get_from_record, search_record_id
from options import servers_data


def get_steam_id(ctx, steamid64):
    if not steamid64:
        author_id = str(ctx.author.id)
        user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
        if user_data:
            steamid64 = user_data.get("steam")

    return steamid64


class Steam(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    steam = SlashCommandGroup("steam", "Команды по Steam")

    # Command to get the price and information about a game with the given appid and countrycode
    @steam.command(description='Посмотреть данные об игре')
    @discord.option("appid", description="ID игры в Steam")
    @discord.option("countrycode", description="Код страны", choices=['RU', 'US', 'TR', 'AR', 'DE', 'UA', 'KZ'])
    async def price(self, ctx: discord.ApplicationContext, appid: int, countrycode: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        # Build the Steam API URL for the given appid and countrycode
        steam_url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc={countrycode}&l=ru"
        try:
            response = requests.get(steam_url)
            response.raise_for_status()

            # Parse the response JSON and extract the relevant data for the appid
            if not response.json()[f"{appid}"]["success"]:
                await ctx.respond(
                    f"Такой игры не существует, либо она недоступна в данном регионе (**{countrycode}**).")
                return

            app_data = response.json()[f"{appid}"]["data"]

            # Create an embed with information about the game
            embed = discord.Embed(
                title=app_data.get("name"),
                description=app_data.get("short_description"),
                color=int(server_data.get("accent_color"), 16)
            )
            embed.set_thumbnail(url=app_data.get("header_image"))
            embed.add_field(name="Дата выпуска", value=app_data.get("release_date", {}).get("date", "Неизвестно"))
            embed.add_field(name="Разработчик", value=", ".join(app_data.get("developers", [])))
            embed.add_field(name="Издатель", value=", ".join(app_data.get("publishers", [])))

            is_free = app_data.get("is_free", False)
            if is_free:
                embed.add_field(name="Стоимость", value="Бесплатно")
            else:
                price_data = app_data.get("price_overview", {})
                discount_percent = price_data.get("discount_percent", 0)
                final_price = price_data.get("final_formatted", "Неизвестно")
                if discount_percent != 0:
                    embed.add_field(name="Стоимость", value=f"{final_price} (-{discount_percent}%)")
                else:
                    embed.add_field(name="Стоимость", value=final_price)

            # Add links to the Steam and SteamDB pages for the game
            steam_url = f"https://store.steampowered.com/app/{appid}/"
            steamdb_url = f"https://steamdb.info/app/{appid}/"
            embed.add_field(name="Страница в Steam", value=f"[Тык]({steam_url})")
            embed.add_field(name="SteamDB", value=f"[Тык]({steamdb_url})")
            await ctx.respond(embed=embed)

        except requests.RequestException:
            await ctx.respond("Ошибка при запросе к API Steam.")

    @steam.command(description="Посмотреть информацию по пользователю Steam")
    @discord.option("steamid64", description="SteamID64", required=False)
    @discord.option("url_or_username", description="Ссылка на профиль, либо имя пользователя (после ../id/)",
                    required=False)
    async def profile(self, ctx: discord.ApplicationContext, steamid64: str, url_or_username: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        await ctx.defer()

        steamid64 = get_steam_id(ctx, steamid64)
        if not steamid64 and not url_or_username:
            await ctx.respond(
                "Вы не привязали профиль Steam к учётной записи Discord. Сделайте это, используя команду "
                "`/steam connect`!")
            return

        response = requests.get("https://www.steamwebapi.com/steam/api/profile", params={
            'steam_id': steamid64,
            'url': url_or_username,
            'key': options.steamapi
        })
        if response.status_code == 200:
            response = response.json()
        else:
            await ctx.respond(f"При получении данных возникла ошибка **{response.status_code}**.\nВозможно, вы неверно указали данные.")
            return

        embed = discord.Embed(
            title=f"Карточка игрока {response['personaname']}",
            color=int(server_data.get("accent_color"), 16)
        )
        embed.add_field(name="SteamID64", value=f"`{response['steamid']}`")
        embed.set_thumbnail(url=response['avatarfull'])
        embed.add_field(name="Аккаунт создан", value=f"<t:{response['timecreated']}:D>")
        embed.add_field(name="Настоящее имя",
                        value=response['realname'] if response['realname'] != '' else "Отсутствует")
        embed.add_field(name="Местоположение",
                        value=response['loccountrycode'] if response['loccountrycode'] is not None else "Отсутствует")
        embed.add_field(name="VAC-баны", value="Имеются" if response['vac'] != 0 else "Отсутствуют")
        embed.add_field(name="Тrade-бан", value="Есть" if response['tradeban'] != 0 else "Отсутствует")
        embed.add_field(name="Лимит на аккаунте ($5)", value="Отсутствует" if response['islimited'] == 0 else "Имеется")
        embed.add_field(name="Ссылка на профиль", value=f"[Тык]({response['profileurl']})")
        # Add the owner of the profile if available in the database
        try:
            embed.add_field(name="Владелец профиля",
                            value=f"<@{search_record_id(str(ctx.guild.id), "Users", "steam", str(response['steamid']))}>")
        except IndexError:
            pass

        await ctx.respond(embed=embed)

    @steam.command(description="Привязать профиль Steam к учётной записи Discord")
    @discord.option("steamid64", description="SteamID64", required=False)
    @discord.option("url_or_username", description="Ссылка на профиль, либо имя пользователя (после ../id/)",
                    required=False)
    async def connect(self, ctx: discord.ApplicationContext, steamid64: str, url_or_username: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return

        await ctx.defer()
        author_id = str(ctx.author.id)

        response = requests.get("https://www.steamwebapi.com/steam/api/profile", params={
            'steam_id': steamid64,
            'url': url_or_username,
            'key': options.steamapi
        })
        if response.status_code == 200:
            response = response.json()
        else:
            await ctx.respond(f"При добавлении возникла ошибка **{response.status_code}**.\nВозможно, вы неверно указали данные.")
            return

        update_record(str(ctx.guild.id), "Users", author_id, {"steam": str(response["steamid"])})

        embed = discord.Embed(
            description=f"Аккаунт **{response["personaname"]}** был успешно привязан к вашей учётной записи!",
            color=int(server_data.get("accent_color"), 16))
        embed.set_thumbnail(url=response['avatarfull'])
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Steam(bot, servers_data))
