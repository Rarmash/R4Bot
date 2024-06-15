import discord
from discord.ext import commands

from modules.firebase import create_record, update_record, get_all_records
from options import servers_data


class SuggestButtons(discord.ui.View):
    def __init__(self, suggestion_message_id, data):
        super().__init__(timeout=None)
        self.suggestion_message_id = suggestion_message_id
        self.data = data

    # Method to update the labels of the buttons based on the votes
    def update_buttons(self):
        accept_button = [x for x in self.children if x.custom_id == "accept"][0]
        deny_button = [x for x in self.children if x.custom_id == "deny"][0]
        accept_button.label = f"За ({self.data['accept_count']})"
        deny_button.label = f"Против ({self.data['deny_count']})"

    # Custom method to check if the user has already voted on this suggestion
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Check if the user has already voted on this suggestion
        if interaction.user.id in self.data["voted_users"]:
            await interaction.response.send_message("Вы уже проголосовали.", ephemeral=True)
            return False
        return True

    # Button callback for voting "За"
    @discord.ui.button(label="За", style=discord.ButtonStyle.green, emoji="<:MinecraftAccept:936636758135828502>",
                       custom_id='accept')
    async def accept_button_callback(self, button, interaction):
        self.data["accept_count"] += 1
        self.data["voted_users"].append(interaction.user.id)
        self.update_buttons()
        await interaction.response.edit_message(view=self)

        update_record(str(interaction.guild.id), "Suggestions", str(self.suggestion_message_id), self.data)

    # Button callback for voting "Против"
    @discord.ui.button(label="Против", style=discord.ButtonStyle.red, emoji="<:MinecraftDeny:936636758127439883>",
                       custom_id='deny')
    async def deny_button_callback(self, button, interaction):
        self.data["deny_count"] += 1
        self.data["voted_users"].append(interaction.user.id)
        self.update_buttons()
        await interaction.response.edit_message(view=self)

        update_record(str(interaction.guild.id), "Suggestions", self.suggestion_message_id, self.data)


class Suggest(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data

    @commands.Cog.listener()
    async def on_ready(self):
        # Fetch existing suggestion data from the database and add views for each suggestion
        for server_id, server_data in servers_data.items():
            channel = self.Bot.get_channel(server_data["suggestions_channel"])
            if channel:
                all_suggestions = get_all_records(str(server_id), "Suggestions")
                for key, suggestion_data in all_suggestions.items():
                    suggestion_message_id = key
                    try:
                        suggestion_message = await channel.fetch_message(suggestion_message_id)
                        suggest_buttons = SuggestButtons(suggestion_message_id, suggestion_data)
                        await suggestion_message.edit(view=suggest_buttons)
                    except discord.NotFound:
                        print(f"Suggestion message with ID {suggestion_message_id} not found.")

    @commands.slash_command(description='Предложить идею')
    async def suggest(self, ctx: discord.ApplicationContext, question):
        server_data = self.servers_data.get(str(ctx.guild.id))
        if not server_data:
            return
        suggestEmbed = discord.Embed(title="Новое предложение", description=f"{question}",
                                     color=int(server_data.get("accent_color"), 16))
        suggestEmbed.add_field(
            name='Автор',
            value=f'<@{ctx.author.id}>'
        )
        # Send a message with the suggestion embed and get the response object
        suggestions_msg = await ctx.respond(embed=suggestEmbed)
        suggestions_message = await suggestions_msg.original_response()
        # Prepare the data for the suggestion and insert it into the database
        suggestion_data = {
            "accept_count": 0,
            "deny_count": 0,
            "voted_users": []
        }
        create_record(str(ctx.guild.id), "Suggestions", str(suggestions_message.id), suggestion_data)
        # Create the SuggestButtons view for the suggestion message and edit the message with it
        suggest_buttons = SuggestButtons(suggestions_message.id, suggestion_data)
        await suggestions_message.edit(view=suggest_buttons)
        suggest_buttons.update_buttons()


def setup(bot):
    bot.add_cog(Suggest(bot, servers_data))
