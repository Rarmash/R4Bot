from discord.ext import commands

from modules.firebase import get_from_record, update_record


class Timeouts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not after.timed_out:
            return

        author = str(after.id)
        timeout_count = get_from_record(str(after.guild.id), "Users", author)
        if timeout_count is None:
            timeout_count = {"timeouts": 1}
        else:
            timeout_count["timeouts"] += 1

        update_record(str(after.guild.id), "Users", author, timeout_count)


def setup(bot):
    bot.add_cog(Timeouts(bot))
