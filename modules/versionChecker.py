import aiohttp
import discord
from discord.ext import commands, tasks

from options import version, servers_data


class VersionChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_version = version
        self.repo = "Rarmash/R4Bot"
        self.servers_data = servers_data
        self.check_version.start()

    @tasks.loop(minutes=10)
    async def check_version(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/repos/{self.repo}/releases/latest") as response:
                if response.status == 200:
                    data = await response.json()
                    remote_version = data["tag_name"]
                    if self.is_newer_version(remote_version.strip('v')):
                        await self.notify_new_version(remote_version.strip())

    def is_newer_version(self, remote_version):
        current_version_parts = list(map(int, self.current_version.split('.')))
        remote_version_parts = list(map(int, remote_version.split('.')))
        return remote_version_parts > current_version_parts

    async def notify_new_version(self, new_version):
        embed = discord.Embed(
            title="Новая версия бота доступна!",
            description=f"Текущая версия: **{self.current_version}**\nНовая версия: **{new_version.strip('v')}**",
            color=discord.Color.green()
        )

        for server in self.servers_data:
            server_data = self.servers_data.get(server)
            if not server_data:
                continue
            channel = self.bot.get_channel(server_data.get("log_channel"))
            if channel:
                await channel.send(embed=embed)

    @check_version.before_loop
    async def before_check_version(self):
        await self.bot.wait_until_ready()
