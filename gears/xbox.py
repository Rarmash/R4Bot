import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
from xpa import XPA

from modules.firebase import get_from_record, update_record, search_record_id
from options import xboxapi

xpa = XPA(xboxapi)


def get_games_amount(xuid):
    games_list = xpa.get_user_achievements(xuid)

    title_count = len(games_list)
    recentgame = games_list[0]["name"]
    curscoreonrecgame = games_list[0]["achievement"]["currentGamerscore"]
    totalscoreonrecgame = games_list[0]["achievement"]["totalGamerscore"]
    return title_count, recentgame, curscoreonrecgame, totalscoreonrecgame


def get_xbox_gamertag(ctx, gamertag):
    if not gamertag:
        author_id = str(ctx.author.id)
        user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
        if user_data:
            gamertag = user_data.get("xbox")

    return gamertag


class Xbox(commands.Cog):
    def __init__(self, bot):
        self.Bot = bot

    xbox = SlashCommandGroup("xbox", "Команды Xbox")

    @xbox.command(description='Посмотреть статистику по пользователю')
    async def stats(self, ctx: discord.ApplicationContext, gamertag=None):
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
                goldstatus = "Активен"
            else:
                goldstatus = "Не активен"
            embed.add_field(name="Статус Game Pass Core", value=goldstatus)
            embed.add_field(name="Фолловеров", value=gamer_info.followerCount)
            embed.add_field(name="Друзей", value=gamer_info.followingCount)
            try:
                title_count, recentgame, curscoreonrecgame, totalscoreonrecgame = get_games_amount(gamer_info.xuid)
                embed.add_field(name="Сыграно игр", value=str(title_count))
                embed.add_field(name="Недавно играл в",
                                value=f"{recentgame} (🅖 {curscoreonrecgame}/{totalscoreonrecgame})")
            except IndexError:
                embed.add_field(name="Игровая статистика", value="Отсутствует, либо скрыта")
            embed.add_field(name="Ссылка на профиль",
                            value=f"[Тык](https://account.xbox.com/ru-ru/Profile?Gamertag={str(gamer_info.gamertag).replace(' ', '%20')})")
            try:
                embed.add_field(name="Владелец профиля", value=f"<@{search_record_id(str(ctx.guild.id), "Users", "xbox", gamertag)}>")
            except IndexError:
                pass
            if gamer_info.isXbox360Gamerpic:
                embed.set_thumbnail(
                    url=f"http://avatar.xboxlive.com/avatar/{str(gamer_info.gamertag).replace(' ', '%20')}/avatarpic-l.png")
            else:
                embed.set_thumbnail(url=gamer_info.displayPicRaw)
            await ctx.respond(embed=embed)
        except KeyError as e:
            await ctx.respond(f"❓ Возникла ошибка {e}...", ephemeral=True)

    @xbox.command(description='Привязать профиль Xbox к учётной записи Discord')
    async def connect(self, ctx: discord.ApplicationContext, gamertag):
        await ctx.defer()
        author = str(ctx.author.id)
        try:
            user_info = xpa.get_account_info_gamertag(gamertag)
            update_record(str(ctx.guild.id), "Users", str(author), {"xbox": gamertag})
            embed = discord.Embed(description=f"Аккаунт {gamertag} был успешно привязан к вашей учётной записи!",
                                  color=int(user_info.preferredColor["primaryColor"], 16))
            embed.set_thumbnail(url=user_info.displayPicRaw)
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"При добавлении возникла ошибка {e}.\nВозможно, вы неверно указали Gamertag.")


def setup(bot):
    bot.add_cog(Xbox(bot))
