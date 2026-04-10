import asyncio

from discord.ext import commands


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            # If the error is a CommandOnCooldown error, respond to the user with the error message
            await ctx.respond(error, delete_after=5.0)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        voice_state = member.guild.voice_client
        if voice_state is None:
            return

        if member.bot:
            return

        await asyncio.sleep(1)

        voice_state = member.guild.voice_client
        if voice_state is None or not voice_state.channel:
            return

        human_members = [channel_member for channel_member in voice_state.channel.members if not channel_member.bot]
        if not human_members:
            await voice_state.disconnect(force=True)


def setup(bot):
    bot.add_cog(Events(bot))
