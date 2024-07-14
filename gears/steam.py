import discord
import requests
from discord.commands import SlashCommandGroup
from discord.ext import commands

from options import servers_data


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


def setup(bot):
    bot.add_cog(Steam(bot, servers_data))
