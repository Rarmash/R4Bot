import asyncio
import re
import tempfile
from asyncio import Queue
from pathlib import Path

import discord
from discord.ext import commands
from gtts import gTTS

from options import servers_data

FFMPEG_OPTIONS = {
    "before_options": "-nostdin",
    "options": '-vn -filter:a "atempo=1.3"',
}


class Tts(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data
        self.message_queue = Queue()
        self.is_playing = False
        self.worker_task = None
        self.last_user_message = {}

    async def disconnect_if_channel_empty(self, guild):
        voice_client = guild.voice_client
        if voice_client is None or voice_client.channel is None:
            return

        human_members = [member for member in voice_client.channel.members if not member.bot]
        if not human_members:
            await voice_client.disconnect(force=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        voice_client = member.guild.voice_client
        if voice_client is None:
            return

        await asyncio.sleep(1)
        await self.disconnect_if_channel_empty(member.guild)

    @commands.Cog.listener()
    async def on_message(self, ctx):
        try:
            if not ctx.guild or ctx.author.bot or not ctx.content:
                return

            server_data = self.servers_data.get(str(ctx.guild.id))
            if not server_data:
                return

            user = ctx.author
            if not user.voice or not user.voice.channel:
                return

            voice_channel = user.voice.channel
            banned_tts_role = discord.utils.get(ctx.guild.roles, id=server_data.get("banned_TTS_role"))

            if ctx.flags.suppress_notifications:
                return

            if banned_tts_role and banned_tts_role in user.roles:
                return

            if ctx.channel.id != voice_channel.id:
                return

            if ctx.channel.id in server_data.get("bannedTTSChannels", []):
                return

            content_without_mentions = re.sub(r"<@[!&]?\d+>|<#\d+>", "", ctx.content)
            content_without_emojis = re.sub(r"<a?:\w+:\d+>", "кастомный эмодзи", content_without_mentions)
            content_without_channels = re.sub(r"<#\d+>", "канал", content_without_emojis).strip()

            if not content_without_channels:
                return

            current_time = discord.utils.utcnow()
            last_message_info = self.last_user_message.get(user.id, {"time": None})

            if last_message_info["time"] and (current_time - last_message_info["time"]).total_seconds() < 10:
                speech = content_without_channels
            else:
                speech = f"{user.display_name} пишет: {content_without_channels}"

            self.last_user_message[user.id] = {"time": current_time}
            await self.message_queue.put((voice_channel, speech))

            if not self.worker_task or self.worker_task.done():
                self.worker_task = self.Bot.loop.create_task(self.process_queue())
        except Exception as exc:
            print(f"Error in on_message: {exc}")

    async def ensure_voice_client(self, channel):
        voice_client = channel.guild.voice_client

        if voice_client and not voice_client.is_connected():
            await voice_client.disconnect(force=True)
            voice_client = None

        if voice_client is None:
            voice_client = await channel.connect(timeout=30.0, reconnect=True)
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        for _ in range(20):
            if voice_client.is_connected():
                return voice_client
            await asyncio.sleep(0.25)

        if hasattr(voice_client, "_connected"):
            await asyncio.to_thread(voice_client._connected.wait, 5)

        return voice_client

    async def process_queue(self):
        if self.is_playing:
            return

        self.is_playing = True

        try:
            while not self.message_queue.empty():
                temp_file = None

                try:
                    last_channel, speech = await self.message_queue.get()

                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                        temp_file = Path(temp_audio.name)

                    await asyncio.to_thread(gTTS(speech, lang="ru").save, str(temp_file))

                    playback_started = False
                    last_error = None

                    for attempt in range(3):
                        voice_client = await self.ensure_voice_client(last_channel)

                        if not voice_client:
                            last_error = RuntimeError("Voice client was not created.")
                            await asyncio.sleep(1)
                            continue

                        if voice_client.is_playing():
                            voice_client.stop()

                        await asyncio.sleep(1 + attempt * 0.5)

                        try:
                            playback = voice_client.play(
                                discord.FFmpegOpusAudio(
                                    executable="ffmpeg",
                                    source=str(temp_file),
                                    **FFMPEG_OPTIONS,
                                ),
                                wait_finish=True,
                            )

                            if playback:
                                error = await playback
                                if error:
                                    raise error

                            playback_started = True
                            break
                        except Exception as playback_error:
                            last_error = playback_error
                            print(f"TTS playback attempt {attempt + 1}/3 failed: {playback_error}")
                            await asyncio.sleep(1)

                    if not playback_started and last_error:
                        raise last_error
                except Exception as exc:
                    print(f"Error during playback: {exc}")
                finally:
                    if temp_file and temp_file.exists():
                        temp_file.unlink(missing_ok=True)
                    self.message_queue.task_done()

            for guild in self.Bot.guilds:
                await self.disconnect_if_channel_empty(guild)
        finally:
            self.is_playing = False


def setup(bot):
    bot.add_cog(Tts(bot, servers_data))
