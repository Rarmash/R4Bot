from __future__ import annotations

import discord
from discord.ext import commands

from options import servers_data


class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.created_channel_ids: set[int] = set()
        self.owner_by_channel_id: dict[int, int] = {}

    def get_guild_config(self, guild_id: int) -> dict:
        server_data = servers_data.get(str(guild_id), {})
        return server_data.get("tempvoice", {})

    @staticmethod
    def get_config_int(config: dict, key: str) -> int | None:
        value = config.get(key)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def build_channel_name(member: discord.Member, template: str) -> str:
        safe_template = template or "Канал {display_name}"
        try:
            return safe_template.format(
                display_name=member.display_name,
                name=member.name,
                id=member.id,
            )[:100]
        except (KeyError, ValueError):
            return f"Канал {member.display_name}"[:100]

    async def create_temp_channel(self, member: discord.Member, config: dict) -> discord.VoiceChannel | None:
        category_id = self.get_config_int(config, "category_id")
        if not category_id:
            return None

        category = member.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return None

        channel_name = self.build_channel_name(
            member,
            str(config.get("channel_name_template") or "Канал {display_name}"),
        )
        user_limit = self.get_config_int(config, "user_limit") or 0
        bitrate = self.get_config_int(config, "bitrate")

        create_kwargs = {
            "name": channel_name,
            "user_limit": user_limit,
            "reason": f"R4Bot TempVoice channel for {member} ({member.id})",
        }
        if bitrate:
            create_kwargs["bitrate"] = bitrate

        try:
            channel = await category.create_voice_channel(**create_kwargs)
        except discord.DiscordException:
            return None

        self.created_channel_ids.add(channel.id)
        self.owner_by_channel_id[channel.id] = member.id
        return channel

    async def delete_if_empty_temp_channel(self, channel: discord.VoiceChannel | None, config: dict | None = None):
        if channel is None:
            return
        if channel.id not in self.created_channel_ids:
            return
        if channel.members:
            return
        if config is not None and config.get("delete_empty_channels") is False:
            return

        self.created_channel_ids.discard(channel.id)
        self.owner_by_channel_id.pop(channel.id, None)

        try:
            await channel.delete(reason="R4Bot TempVoice channel is empty")
        except discord.DiscordException:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.created_channel_ids.clear()
        self.owner_by_channel_id.clear()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or member.guild is None:
            return

        config = self.get_guild_config(member.guild.id)
        trigger_channel_id = self.get_config_int(config, "trigger_channel_id")
        if not trigger_channel_id:
            return

        before_channel = before.channel
        after_channel = after.channel

        if after_channel is not None and after_channel.id == trigger_channel_id:
            channel = await self.create_temp_channel(member, config)
            if channel is None:
                return

            try:
                await member.move_to(channel, reason="R4Bot TempVoice channel created")
            except discord.DiscordException:
                await self.delete_if_empty_temp_channel(channel, config)
                return

        if isinstance(before_channel, discord.VoiceChannel):
            await self.delete_if_empty_temp_channel(before_channel, config)


def setup(bot):
    bot.add_cog(TempVoice(bot))
