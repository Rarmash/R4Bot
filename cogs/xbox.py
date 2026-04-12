import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
from xpa import ErrorHandler as Xbox_err
from xpa import XPA

from modules.firebase import get_from_record, search_record_id, update_record
from options import xboxapi

xpa = XPA(xboxapi)


def get_games_amount(xuid):
    games_list = xpa.get_user_achievements(xuid)
    title_count = len(games_list)
    if title_count == 1000:
        title_count = "1000+"

    recent_game = games_list[0]["name"]
    current_score = games_list[0]["achievement"]["currentGamerscore"]
    total_score = games_list[0]["achievement"]["totalGamerscore"]
    return title_count, recent_game, current_score, total_score


def get_xbox_gamertag(ctx, gamertag):
    if gamertag:
        return gamertag

    author_id = str(ctx.author.id)
    user_data = get_from_record(str(ctx.guild.id), "Users", author_id)
    if not user_data:
        return None

    try:
        return xpa.get_account_info_xuid(user_data.get("xbox")).Gamertag
    except Xbox_err.XboxApiError:
        return None


def get_xbox_gamertag_to_profile(xuid):
    return xpa.get_account_info_xuid(xuid).Gamertag


class Xbox(commands.Cog):
    xbox = SlashCommandGroup("xbox", "Команды Xbox")

    def __init__(self, bot):
        self.bot = bot

    @xbox.command(description="Посмотреть статистику по пользователю")
    @discord.option("gamertag", description="Gamertag пользователя", required=False)
    async def stats(self, ctx: discord.ApplicationContext, gamertag: str):
        await ctx.defer()
        gamertag = get_xbox_gamertag(ctx, gamertag)
        if not gamertag:
            await ctx.respond(
                "Ты не привязал профиль Xbox к учётной записи Discord. Сделай это командой `/xbox connect <Gamertag>`.",
                ephemeral=True,
            )
            return

        try:
            gamer_info = xpa.get_account_info_gamertag(gamertag)
            embed = discord.Embed(
                title=f"Карточка игрока {gamer_info.gamertag}",
                color=int(gamer_info.preferredColor["primaryColor"], 16),
            )
            embed.add_field(name="Gamerscore", value=f"🅶 {gamer_info.gamerScore}")
            embed.add_field(
                name="Статус Game Pass Core",
                value="Активен" if gamer_info.accountTier == "Gold" else "Не активен",
            )
            embed.add_field(name="Фолловеров", value=gamer_info.followerCount)
            embed.add_field(name="Друзей", value=gamer_info.followingCount)

            try:
                title_count, recent_game, current_score, total_score = get_games_amount(gamer_info.xuid)
                embed.add_field(name="Сыграно игр", value=str(title_count))
                embed.add_field(name="Недавно играл в", value=f"{recent_game} (🅶 {current_score}/{total_score})")
            except IndexError:
                embed.add_field(name="Игровая статистика", value="Отсутствует или скрыта")

            embed.add_field(
                name="Ссылка на профиль",
                value=f"[Тык](https://www.xbox.com/ru-RU/play/user/{str(gamer_info.gamertag).replace(' ', '%20')})",
            )

            try:
                embed.add_field(
                    name="Владелец профиля",
                    value=f"<@{search_record_id(str(ctx.guild.id), 'Users', 'xbox', gamertag)}>",
                )
            except IndexError:
                pass

            if gamer_info.isXbox360Gamerpic:
                embed.set_thumbnail(
                    url=f"http://avatar.xboxlive.com/avatar/{str(gamer_info.gamertag).replace(' ', '%20')}/avatarpic-l.png",
                )
            else:
                embed.set_thumbnail(url=gamer_info.displayPicRaw)

            await ctx.respond(embed=embed)
        except Xbox_err.XboxApiNotFoundError:
            await ctx.respond("Игрок не найден.", ephemeral=True)
        except Xbox_err.XboxApiError as error:
            await ctx.respond(f"Не удалось получить данные Xbox: {error}", ephemeral=True)
        except KeyError as error:
            await ctx.respond(f"Возникла ошибка в данных ответа Xbox API: {error}", ephemeral=True)

    @xbox.command(description="Привязать профиль Xbox к учётной записи Discord")
    @discord.option("gamertag", description="Gamertag пользователя")
    @discord.guild_only()
    async def connect(self, ctx: discord.ApplicationContext, gamertag: str):
        await ctx.defer()
        author_id = str(ctx.author.id)

        try:
            user_info = xpa.get_account_info_gamertag(gamertag)
            update_record(str(ctx.guild.id), "Users", author_id, {"xbox": str(user_info.xuid)})
            embed = discord.Embed(
                description=(
                    f"Аккаунт **{gamertag}** был успешно привязан к твоей учётной записи.\n"
                    "Если ты изменишь Gamertag, здесь его менять не понадобится."
                ),
                color=int(user_info.preferredColor["primaryColor"], 16),
            )
            embed.set_thumbnail(url=user_info.displayPicRaw)
            await ctx.respond(embed=embed)
        except Xbox_err.XboxApiError as error:
            await ctx.respond(
                f"Не удалось привязать профиль Xbox: {error}.\nПроверь, что Gamertag указан верно.",
                ephemeral=True,
            )


def setup(bot):
    bot.add_cog(Xbox(bot))
