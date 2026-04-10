from discord.ext import commands

from modules.firebase import get_from_record, update_record


class Timeouts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Check if the member (user) is timed out
        if after.timed_out:
            author = str(after.id)
            timeoutCount = get_from_record(str(after.guild.id), "Users", author)
            if timeoutCount is None:
                # If the user is not found in the collection, create a new document for them
                timeoutCount = {"timeouts": 1}
                update_record(str(after.guild.id), "Users", author, timeoutCount)
            else:
                # If the user is already in the collection, update their timeouts count
                timeoutCount["timeouts"] += 1
                update_record(str(after.guild.id), "Users", author, timeoutCount)


def setup(bot):
    bot.add_cog(Timeouts(bot))
