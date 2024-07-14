import os
from time import sleep

import discord
from discord.ext import commands

from options import servers_data


class TicketButtons(discord.ui.View):
    def __init__(self, bot, servers_data):
        super().__init__(timeout=None)
        self.Bot = bot
        self.servers_data = servers_data

    # Custom method to check if the user has the required roles to interact with the buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool | None:
        server_data = self.servers_data.get(str(interaction.guild.id))
        if not server_data:
            return
        # Check if the user has either the elder_mod_role_id or admin_role_id
        if not (discord.utils.get(interaction.guild.roles, id=server_data.get(
                "elder_mod_role_id")) in interaction.user.roles or discord.utils.get(interaction.guild.roles,
                                                                                     id=server_data.get(
                                                                                             "admin_role_id")) in interaction.user.roles):
            await interaction.response.send_message("У вас нет прав для выполнения данной команды.", ephemeral=True)
            return False
        return True

    # Select menu callback for adding a user to the ticket
    @discord.ui.select(placeholder="Добавить пользователя", min_values=1, max_values=1,
                       select_type=discord.ComponentType.user_select, custom_id="adduser")
    async def add_user_select_callback(self, select, interaction):
        await interaction.channel.set_permissions(select.values[0], speak=True, send_messages=True,
                                                  read_message_history=True, read_messages=True)
        await interaction.response.send_message(
            f'<@{select.values[0].id}>, вас добавили в чат Тикета для решения вопроса.')

    # Button callback for closing the ticket
    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.red, emoji="🔐", custom_id='closeticket')
    async def сlose_button_callback(self, button, interaction):
        server_data = self.servers_data.get(str(interaction.guild.id))
        if not server_data:
            return
        # Disable all items in the view to prevent further interaction
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        # Send an embed indicating that the ticket will be deleted in 10 seconds
        embed = discord.Embed(description='Удаление Тикета через 10 секунд.',
                              color=int(server_data.get("accent_color"), 16))
        await interaction.followup.send(embed=embed)
        sleep(10)
        filename = f'{interaction.channel.name}.txt'
        # Save the history of the ticket channel into a file
        with open(filename, "w") as file:
            async for msg in interaction.channel.history(limit=None, oldest_first=True):
                msg_time = str(msg.created_at)[:-13]
                file.write(f"{msg_time} - {msg.author.display_name}: {msg.content}\n")
        # Get the admin_channel and send the ticket history there as a file
        channel = self.Bot.get_channel(server_data.get("admin_channel"))
        await channel.send(f'{interaction.channel.name} закрыт.', file=discord.File(filename))
        os.remove(filename)
        await interaction.channel.delete()  # Delete the ticket channel


class Support(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data

    @commands.slash_command(description='Отправить Тикет')
    @discord.option("text", description="Причина")
    async def ticket(self, ctx, text: str):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        embed = discord.Embed(
            description=f'**<@{ctx.author.id}> открывает Тикет**\n**Причина:** {text}\n**В канале:** <#{ctx.channel.id}>',
            color=int(server_data.get("accent_color"), 16)
        )
        tcategory = discord.utils.get(ctx.guild.categories, id=server_data.get("ticket_category"))
        # Create a new text channel for the ticket
        channel = await ctx.guild.create_text_channel(f'Ticket-<@{ctx.author.name}>', topic=text, category=tcategory)
        # Set specific permissions for the author of the command in the ticket channel
        await channel.set_permissions(ctx.author, speak=True, send_messages=True, read_message_history=True,
                                      read_messages=True)
        # Send messages to the new ticket channel and add the TicketButtons view
        await channel.send(f'<@&{server_data.get("elder_mod_role_id")}>ы, надо обкашлять пару вопросиков.', embed=embed,
                           view=TicketButtons(self.Bot, servers_data))
        await channel.send(f'<@{ctx.author.id}>, вам слово.')
        # Send a response to the command author indicating the successful ticket creation
        embed = discord.Embed(description='Ваш Тикет был успешно отправлен!',
                              color=int(server_data.get("accent_color"), 16))
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(Support(bot, servers_data))
