import re
from asyncio import Queue
from pathlib import Path

import discord
from discord.ext import commands
from gtts import gTTS
from pydub import AudioSegment
from pydub.effects import speedup

from options import servers_data

FFMPEG_OPTIONS = {'options': '-vn'}

class Tts(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data
        self.message_queue = Queue()
        self.is_playing = False

    @commands.Cog.listener()
    async def on_message(self, ctx):
        try:
            server_data = self.servers_data.get(str(ctx.guild.id))
            if not server_data:
                return

            user = ctx.author
            vc = user.voice.channel

            banned_TTS_role = discord.utils.get(ctx.guild.roles, id=server_data.get("banned_TTS_role"))

            if ctx.flags.suppress_notifications:
                return

            if banned_TTS_role in user.roles:
                return

            if ctx.channel.id == vc.id and ctx.channel.id not in server_data.get("bannedTTSChannels", []):
                content_without_mentions = re.sub(r"<@[!&]?\d+>|<#\d+>", "", ctx.content)
                content_without_emojis = re.sub(r"<a?:\w+:\d+>", "кастомный эмодзи", content_without_mentions)
                content_without_channels = re.sub(r"<#\d+>", "канал", content_without_emojis)

                speech = f"{user.display_name} пишет: {content_without_channels}"
                await self.message_queue.put((vc, speech))

                if not self.is_playing:
                    await self.process_queue()
        except Exception as e:
            print(f"Error in on_message: {e}")

    async def process_queue(self):
        self.is_playing = True
        vc = None  # Инициализация переменной vc

        while not self.message_queue.empty():
            temp_file = Path("speech.mp3")

            try:
                vc, speech = await self.message_queue.get()

                tts = gTTS(speech, lang="ru")
                tts.save(temp_file)

                audio = AudioSegment.from_mp3(temp_file)
                new_file = speedup(audio, 1.3, 130)
                new_file.export(temp_file, format="mp3")

                def after_playback(error=None):
                    if error:
                        print(f"Error during playback: {error}")
                    self.Bot.loop.call_soon_threadsafe(self.Bot.loop.create_task, self.process_queue())

                if not vc.guild.voice_client:
                    await vc.connect()
                elif vc.guild.voice_client.channel != vc:
                    await vc.guild.voice_client.move_to(vc)

                vc.guild.voice_client.play(
                    discord.FFmpegPCMAudio(executable="ffmpeg", source=temp_file, **FFMPEG_OPTIONS),
                    after=after_playback
                )

                return  # Exit the current loop iteration; next will be triggered by `after_playback`

            except Exception as e:
                print(f"Error during playback: {e}")

        self.is_playing = False

        if vc and vc.guild and vc.guild.voice_client and vc.guild.voice_client.is_connected():
            await vc.guild.voice_client.disconnect()


def setup(bot):
    bot.add_cog(Tts(bot, servers_data))
