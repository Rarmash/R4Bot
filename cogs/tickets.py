import asyncio
import os
from pathlib import Path

import discord
from discord.ext import commands

from options import servers_data


class TicketButtons(discord.ui.View):
    def __init__(self, bot, servers_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool | None:
        server_data = self.get_server_data(interaction.guild.id)
        if not server_data:
            return

        if interaction.user.id == interaction.guild.owner_id:
            return True

        mod_role = discord.utils.get(interaction.guild.roles, id=server_data.get("mod_role_id"))
        admin_role = discord.utils.get(interaction.guild.roles, id=server_data.get("admin_role_id"))
        if mod_role in interaction.user.roles or admin_role in interaction.user.roles:
            return True

        await interaction.response.send_message("У вас нет прав для выполнения данной команды.", ephemeral=True)
        return False

    @discord.ui.select(
        placeholder="Добавить пользователя",
        min_values=1,
        max_values=1,
        select_type=discord.ComponentType.user_select,
        custom_id="adduser",
    )
    async def add_user_select_callback(self, select, interaction):
        target_user = select.values[0]
        await interaction.channel.set_permissions(
            target_user,
            speak=True,
            send_messages=True,
            read_message_history=True,
            read_messages=True,
        )
        await interaction.response.send_message(f"<@{target_user.id}>, вас добавили в чат Тикета для решения вопроса.")

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.red, emoji="🔒", custom_id="closeticket")
    async def close_button_callback(self, button, interaction):
        server_data = self.get_server_data(interaction.guild.id)
        if not server_data:
            return

        self.disable_all_items()
        await interaction.response.edit_message(view=self)

        embed = discord.Embed(
            description="Удаление Тикета через 10 секунд.",
            color=int(server_data.get("accent_color"), 16),
        )
        await interaction.followup.send(embed=embed)
        await asyncio.sleep(10)

        filename = Path(f"{interaction.channel.name}.txt")
        with filename.open("w", encoding="utf8") as file:
            async for msg in interaction.channel.history(limit=None, oldest_first=True):
                msg_time = str(msg.created_at)[:-13]
                file.write(f"{msg_time} - {msg.author.display_name}: {msg.content}\n")

        admin_channel = self.bot.get_channel(server_data.get("admin_channel"))
        if admin_channel is not None:
            await admin_channel.send(f"{interaction.channel.name} закрыт.", file=discord.File(filename))

        os.remove(filename)
        await interaction.channel.delete()


class Support(commands.Cog):
    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    @commands.slash_command(description="Отправить Тикет")
    @discord.option("text", description="Причина")
    async def ticket(self, ctx, text: str):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            return

        embed = discord.Embed(
            description=(
                f"**<@{ctx.author.id}> открывает Тикет**\n"
                f"**Причина:** {text}\n"
                f"**В канале:** <#{ctx.channel.id}>"
            ),
            color=int(server_data.get("accent_color"), 16),
        )
        ticket_category = discord.utils.get(ctx.guild.categories, id=server_data.get("ticket_category"))
        channel = await ctx.guild.create_text_channel(f"Ticket-<@{ctx.author.name}>", topic=text, category=ticket_category)
        await channel.set_permissions(
            ctx.author,
            speak=True,
            send_messages=True,
            read_message_history=True,
            read_messages=True,
        )
        await channel.send(
            f"<@&{server_data.get('mod_role_id')}>ы, надо обкашлять пару вопросиков.",
            embed=embed,
            view=TicketButtons(self.bot, servers_data),
        )
        await channel.send(f"<@{ctx.author.id}>, вам слово.")

        response_embed = discord.Embed(
            description="Ваш Тикет был успешно отправлен!",
            color=int(server_data.get("accent_color"), 16),
        )
        await ctx.respond(embed=response_embed, ephemeral=True)


def setup(bot):
    bot.add_cog(Support(bot, servers_data))
