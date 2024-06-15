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
        # Check if the member's voice state has changed and if they were in a voice channel before the update
        voice_state = member.guild.voice_client
        if voice_state is None:
            return

            # Check if the voice channel is empty (only the bot remains in the channel)
        if len(voice_state.channel.members) == 1:
            # If the voice channel is empty, disconnect the bot from the voice channel
            await voice_state.disconnect()


def setup(bot):
    bot.add_cog(Events(bot))
