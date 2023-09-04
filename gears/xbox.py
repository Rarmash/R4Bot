import requests
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from options import xboxapi, debugmode, myclient

class Xbox(commands.Cog):
    def __init__(self, bot):
        self.Bot = bot

    xbox = SlashCommandGroup("xbox", "Команды Xbox")
    
    def get_xbox_gamertag(self, ctx, gamertag):
        if not gamertag:
            author_id = str(ctx.author.id)
            user_data = myclient[f"{str(ctx.guild.id)}"]["Users"].find_one({"_id": author_id})
            if user_data:
                gamertag = user_data.get("xbox")

        return gamertag
    
    def get_user_stats(self, gamertag):
        response = requests.get(f'https://xbl.io/api/v2/search/{gamertag}', headers={'x-authorization': xboxapi})
        response_data = response.json().get("people", [{}])[0]
        return response_data
    
    def get_games_amount(self, xuid):
        response = requests.get(f'https://xbl.io/api/v2/achievements/player/{xuid}', headers={'x-authorization': xboxapi}).json()
        title_count = len(response["titles"])
        recentgame = response["titles"][0]["name"]
        curscoreonrecgame = response["titles"][0]["achievement"]["currentGamerscore"]
        totalscoreonrecgame = response["titles"][0]["achievement"]["totalGamerscore"]
        return title_count, recentgame, curscoreonrecgame, totalscoreonrecgame

    @xbox.command(description='Посмотреть статистику по пользователю')
    async def stats(self, ctx: discord.ApplicationContext, gamertag = None):
        Collection = myclient[f"{str(ctx.guild.id)}"]["Users"]
        await ctx.defer()
        gamertag = self.get_xbox_gamertag(ctx, gamertag)
        if not gamertag:
            await ctx.respond("Вы не привязали профиль Xbox к учётной записи Discord. Сделайте это, используя команду `/xbox connect <Gamertag>`!", ephemeral=True)
            return
        try:
            stats_data = self.get_user_stats(gamertag)
            embed = discord.Embed(title=f'Карточка игрока {stats_data["gamertag"]}', color=int(stats_data["preferredColor"]["primaryColor"], 16))
            embed.add_field(name="Gamerscore", value=f'🅖 {stats_data["gamerScore"]}')
            if stats_data["detail"]["accountTier"] == "Gold":
                goldstatus = "Активен"
            else:
                goldstatus = "Не активен"
            embed.add_field(name="Статус Game Pass Core", value=goldstatus)
            embed.add_field(name="Фолловеров", value=f'{stats_data["detail"]["followerCount"]}')
            embed.add_field(name="Друзей", value=f'{stats_data["detail"]["followingCount"]}')
            try:
                title_count, recentgame, curscoreonrecgame, totalscoreonrecgame = self.get_games_amount(stats_data["xuid"])
                embed.add_field(name="Сыграно игр", value=title_count)
                embed.add_field(name="Недавно играл в", value=f"{recentgame} (🅖 {curscoreonrecgame}/{totalscoreonrecgame})")
            except IndexError:
                embed.add_field(name="Игровая статистика", value="Отсутствует, либо скрыта")
            embed.add_field(name = "Ссылка на профиль", value = f"[Тык](https://account.xbox.com/ru-ru/Profile?Gamertag={str(stats_data['gamertag']).replace(' ', '%20')})")
            try:
                embed.add_field(name = "Владелец профиля", value=f"<@{Collection.find_one({'xbox': gamertag})['_id']}>")
            except TypeError:
                pass
            if stats_data["isXbox360Gamerpic"] == True:
                embed.set_thumbnail(url=f"http://avatar.xboxlive.com/avatar/{str(stats_data['gamertag']).replace(' ', '%20')}/avatarpic-l.png")
            else:
                embed.set_thumbnail(url=stats_data["displayPicRaw"])
            await ctx.respond(embed = embed)
        except KeyError as e:
            await ctx.respond(f"❓ Возникла ошибка {e}...", ephemeral=True)

    @xbox.command(description='Привязать профиль Xbox к учётной записи Discord')
    async def connect(self, ctx: discord.ApplicationContext, gamertag):
        Collection = myclient[f"{str(ctx.guild.id)}"]["Users"]
        await ctx.defer()
        author = str(ctx.author.id)
        try:
            stats_data = self.get_user_stats(gamertag)
            Collection.update_one({"_id": author}, {"$set": {"xbox": gamertag}})
            embed = discord.Embed(description=f"Аккаунт {gamertag} был успешно привязан к вашей учётной записи!", color=int(stats_data["preferredColor"]["primaryColor"], 16))
            embed.set_thumbnail(url=stats_data["displayPicRaw"])
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"При добавлении возникла ошибка {e}.\nВозможно, вы неверно указали Gamertag.")
    
def setup(bot):
    bot.add_cog(Xbox(bot))