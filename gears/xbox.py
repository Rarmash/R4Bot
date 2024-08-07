import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
from xpa import ErrorHandler as Xbox_err
from xpa import XPA

from modules.firebase import get_from_record, update_record, search_record_id
from options import xboxapi

xpa = XPA(xboxapi)


# Helper function to get the amount of games played by the user (max 1000)
def get_games_amount(xuid):
    games_list = xpa.get_user_achievements(xuid)

    title_count = len(games_list)
    if title_count == 1000:
        title_count = "1000+"

    recentgame = games_list[0]["name"]
    curscoreonrecgame = games_list[0]["achievement"]["currentGamerscore"]
    totalscoreonrecgame = games_list[0]["achievement"]["totalGamerscore"]
    return title_count, recentgame, curscoreonrecgame, totalscoreonrecgame


# Helper function to get the Xbox gamertag of the user
def get_xbox_gamertag(ctx, gamertag):
    if not gamertag:
        author_id = str(ctx.author.id)
        user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
        if user_data:
            gamertag = xpa.get_account_info_xuid(user_data.get("xbox")).Gamertag

    return gamertag


class Xbox(commands.Cog):
    def __init__(self, bot):
        self.Bot = bot

    xbox = SlashCommandGroup("xbox", "Команды Xbox")

    @xbox.command(description='Посмотреть статистику по пользователю')
    @discord.option("gamertag", description="Gamertag пользователя", required=False)
    async def stats(self, ctx: discord.ApplicationContext, gamertag: str):
        await ctx.defer()
        gamertag = get_xbox_gamertag(ctx, gamertag)
        if not gamertag:
            await ctx.respond(
                "Вы не привязали профиль Xbox к учётной записи Discord. Сделайте это, используя команду `/xbox "
                "connect <Gamertag>`!",
                ephemeral=True)
            return
        try:
            gamer_info = xpa.get_account_info_gamertag(gamertag)
            embed = discord.Embed(title=f"Карточка игрока {gamer_info.gamertag}",
                                  color=int(gamer_info.preferredColor["primaryColor"], 16))
            embed.add_field(name="Gamerscore", value=f"🅖 {gamer_info.gamerScore}")
            if gamer_info.accountTier == "Gold":
                gold_status = "Активен"
            else:
                gold_status = "Не активен"
            embed.add_field(name="Статус Game Pass Core", value=gold_status)
            embed.add_field(name="Фолловеров", value=gamer_info.followerCount)
            embed.add_field(name="Друзей", value=gamer_info.followingCount)
            try:
                title_count, recent_game, currentScoreOnRecentGame, totalScoreOnRecentGame = get_games_amount(
                    gamer_info.xuid)
                embed.add_field(name="Сыграно игр", value=str(title_count))
                embed.add_field(name="Недавно играл в",
                                value=f"{recent_game} (🅖 {currentScoreOnRecentGame}/{totalScoreOnRecentGame})")
            except IndexError:
                embed.add_field(name="Игровая статистика", value="Отсутствует, либо скрыта")
            embed.add_field(name="Ссылка на профиль",
                            value=f"[Тык](https://www.xbox.com/ru-RU/play/user/{str(gamer_info.gamertag).replace(' ', '%20')})")
            try:
                embed.add_field(name="Владелец профиля",
                                value=f"<@{search_record_id(str(ctx.guild.id), 'Users', 'xbox', gamertag)}>")
            except IndexError:
                pass
            if gamer_info.isXbox360Gamerpic:  # TODO: rewrite, cuz this method is deprecated
                embed.set_thumbnail(
                    url=f"http://avatar.xboxlive.com/avatar/{str(gamer_info.gamertag).replace(' ', '%20')}/avatarpic-l.png")
            else:
                embed.set_thumbnail(url=gamer_info.displayPicRaw)
            await ctx.respond(embed=embed)
        except Xbox_err.XboxApiNotFoundError:
            await ctx.respond("❗ Игрок не найден...", ephemeral=True)
        except KeyError as e:
            await ctx.respond(f"❓ Возникла ошибка {e}...", ephemeral=True)

    @xbox.command(description='Привязать профиль Xbox к учётной записи Discord')
    @discord.option("gamertag", description="Gamertag пользователя")
    @discord.guild_only()
    async def connect(self, ctx: discord.ApplicationContext, gamertag: str):
        await ctx.defer()
        author = str(ctx.author.id)
        try:
            user_info = xpa.get_account_info_gamertag(gamertag)
            update_record(str(ctx.guild.id), "Users", str(author), {"xbox": str(user_info.xuid)})
            embed = discord.Embed(description=f"Аккаунт **{gamertag}** был успешно привязан к вашей учётной записи!\n"
                                              f"Если вы измените Gamertag, здесь его менять не будет нужно.",
                                  color=int(user_info.preferredColor["primaryColor"], 16))
            embed.set_thumbnail(url=user_info.displayPicRaw)
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"При добавлении возникла ошибка {e}.\nВозможно, вы неверно указали Gamertag.")


def setup(bot):
    bot.add_cog(Xbox(bot))
