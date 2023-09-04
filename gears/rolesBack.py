import discord
from discord.ext import commands
from options import myclient

class RolesBack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        author_id = str(member.id)
        server_id = str(member.guild.id)
        roles_collection = myclient[f"{server_id}"]["UserRoles"]
        roles_data = roles_collection.find_one({"_id": author_id})

        # If the user has saved role data, restore the roles
        if roles_data:
            roles = [int(role_id) for role_id in roles_data["roles"].split("-") if role_id and role_id != str(member.guild.id)]
            roles_to_add = [discord.utils.get(member.guild.roles, id=role_id) for role_id in roles if discord.utils.get(member.guild.roles, id=role_id)]
            await member.add_roles(*roles_to_add)
        
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        roles_ids = [str(role.id) for role in member.roles if role.id != member.guild.id]
        roles_to_save = "-".join(roles_ids)
        author_id = str(member.id)
        server_id = str(member.guild.id)
        roles_collection = myclient[f"{server_id}"]["UserRoles"]
        roles_collection.update_one({"_id": author_id}, {"$set": {"roles": roles_to_save}}, upsert=True)
        
def setup(bot):
    bot.add_cog(RolesBack(bot))
