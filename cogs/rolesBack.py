import discord
from discord.ext import commands

from modules.firebase import get_from_record, update_record


class RolesBack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        author_id = str(member.id)
        server_id = str(member.guild.id)
        roles_data = get_from_record(server_id, "UserRoles", author_id)

        # If the user has saved role data, restore the roles
        if roles_data:
            roles = [int(role_id) for role_id in roles_data["roles"] if role_id and role_id != str(member.guild.id)]
            roles_to_add = [discord.utils.get(member.guild.roles, id=role_id) for role_id in roles if
                            discord.utils.get(member.guild.roles, id=role_id)]
            await member.add_roles(*roles_to_add)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        roles_ids = [str(role.id) for role in member.roles if role.id != member.guild.id]
        author_id = str(member.id)
        server_id = str(member.guild.id)
        update_record(server_id, "UserRoles", author_id, {"roles": roles_ids})


def setup(bot):
    bot.add_cog(RolesBack(bot))
