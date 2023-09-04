from discord.ext import commands
from options import myclient

class Timeouts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        Collection = myclient[f"{str(before.guild.id)}"]["Users"]
        # Check if the member (user) is timed out
        if after.timed_out:
            author = str(after.id)
            timeoutCount = Collection.find_one({"_id": author})
            if timeoutCount is None:
                # If the user is not found in the collection, create a new document for them
                timeoutCount = {"_id": author, "timeouts": 1}
                Collection.insert_one(timeoutCount)
            else:
                # If the user is already in the collection, update their timeouts count
                timeoutCount["timeouts"] += 1
                Collection.update_one({"_id": author}, {"$set": {"timeouts": timeoutCount["timeouts"]}})

def setup(bot):
    bot.add_cog(Timeouts(bot))
