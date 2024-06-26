import re
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

    @commands.Cog.listener()
    async def on_message(self, ctx):
        try:
            # Try to get server_data based on the guild id from servers_data
            server_data = self.servers_data.get(str(ctx.guild.id))
            if not server_data:
                return
            user = ctx.author
            try:
                vc = user.voice.channel  # Get the voice channel of the user
                if ctx.channel.id == vc.id and ctx.channel.id not in server_data.get("bannedTTSChannels", []):
                    # If the channel ID of the message matches the voice channel ID of the user
                    # and the channel ID is not in the bannedTTSChannels list, proceed with TTS
                    tempfile = "speech.mp3"
                    try:
                        ch = await vc.connect()
                    except discord.errors.ClientException:
                        # If the bot is already connected to a voice channel, disconnect and reconnect
                        await ctx.guild.voice_client.disconnect()
                        ch = await vc.connect()
                    # Remove any mentions from the message content to avoid reading them out in TTS
                    content_without_mentions = re.sub(r"<@[!&]?\d+>|<#\d+>", "", ctx.content)
                    # Create the TTS speech with the user's display name and the content without mentions
                    speech = f"{user.display_name} пишет: {content_without_mentions}"
                    tts = gTTS(speech, lang="ru")
                    tts.save(tempfile)

                    audio = AudioSegment.from_mp3(tempfile)
                    # Speed up the audio by 30%
                    new_file = speedup(audio, 1.3, 130)
                    new_file.export(tempfile, format="mp3")
                    ch.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=Path(".") / tempfile, **FFMPEG_OPTIONS))
            except:
                pass
        except:
            pass


def setup(bot):
    bot.add_cog(Tts(bot, servers_data))
