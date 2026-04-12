import asyncio

from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(error, delete_after=5.0)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        voice_client = member.guild.voice_client
        if voice_client is None:
            return

        await asyncio.sleep(1)

        voice_client = member.guild.voice_client
        if voice_client is None or voice_client.channel is None:
            return

        human_members = [channel_member for channel_member in voice_client.channel.members if not channel_member.bot]
        if not human_members:
            await voice_client.disconnect(force=True)


def setup(bot):
    bot.add_cog(Events(bot))
