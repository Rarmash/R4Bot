import asyncio
import re
import tempfile
import unicodedata
from asyncio import Queue
from contextlib import nullcontext
from pathlib import Path

import discord
from discord.ext import commands
from gtts import gTTS

from options import servers_data

FFMPEG_OPTIONS = {
    "before_options": "-nostdin",
    "options": '-vn -filter:a "atempo=1.6"',
}
MAX_TTS_CHUNK_LENGTH = 180
EMPTY_CHANNEL_DISCONNECT_DELAY = 3
GTTS_GENERATION_TIMEOUT = 20
PLAYBACK_TIMEOUT = 45
TEXT_EMOJI_PATTERN = re.compile(r":[a-z0-9_+\-]+:", re.IGNORECASE)
GIF_URL_PATTERN = re.compile(r"(?:https?://|www\.)\S*gif\S*", re.IGNORECASE)
MP4_URL_PATTERN = re.compile(r"https?://\S+?\.mp4(?:\?\S*)?|www\.\S+?\.mp4(?:\?\S*)?", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def is_emoji_character(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x1F300 <= codepoint <= 0x1F5FF
        or 0x1F600 <= codepoint <= 0x1F64F
        or 0x1F680 <= codepoint <= 0x1F6FF
        or 0x1F700 <= codepoint <= 0x1F77F
        or 0x1F780 <= codepoint <= 0x1F7FF
        or 0x1F800 <= codepoint <= 0x1F8FF
        or 0x1F900 <= codepoint <= 0x1F9FF
        or 0x1FA00 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x26FF
        or 0x2700 <= codepoint <= 0x27BF
        or 0xFE00 <= codepoint <= 0xFE0F
        or 0x1F1E6 <= codepoint <= 0x1F1FF
        or 0x1F3FB <= codepoint <= 0x1F3FF
        or codepoint in {0x200D, 0x20E3}
    )


def replace_unicode_emojis(text: str) -> str:
    result = []
    in_emoji_sequence = False

    for char in text:
        if is_emoji_character(char):
            if not in_emoji_sequence:
                if result and not result[-1].endswith(" "):
                    result.append(" ")
                result.append("Эмодзи")
                in_emoji_sequence = True
            continue

        if unicodedata.category(char) == "So":
            if not in_emoji_sequence:
                if result and not result[-1].endswith(" "):
                    result.append(" ")
                result.append("Эмодзи")
                in_emoji_sequence = True
            continue

        in_emoji_sequence = False
        result.append(char)

    return "".join(result)


def strip_discord_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " код ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", text)
    text = re.sub(r"(?m)^\s*>>> ?", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"(?m)^\s*#{1,3}\s+", "", text)
    text = re.sub(r"(?m)^\s*-#\s+", "", text)
    text = re.sub(r"(?m)^\s*(?:[-*]|\d+\.)\s+", "", text)
    text = text.replace("||", "")
    text = text.replace("~~", "")
    text = text.replace("__", "")
    text = text.replace("***", "")
    text = text.replace("**", "")
    text = text.replace("*", "")
    text = text.replace("_", "")
    return text


def get_attachment_tts_labels(message) -> list[str]:
    labels = []

    for attachment in getattr(message, "attachments", []):
        content_type = (attachment.content_type or "").lower()
        filename = (attachment.filename or "").lower()
        if "gif" in content_type or filename.endswith(".gif"):
            labels.append("Гифка")
        elif content_type.startswith("image/"):
            labels.append("Изображение")
        elif content_type.startswith("video/"):
            labels.append("Видео")
        elif content_type.startswith("audio/"):
            labels.append("Аудио")
        else:
            labels.append("Файл")

    for embed in getattr(message, "embeds", []):
        embed_type = (getattr(embed, "type", "") or "").lower()
        if embed_type == "gifv":
            labels.append("Гифка")
        elif embed_type in {"image", "video"}:
            labels.append("Изображение" if embed_type == "image" else "Видео")

    return labels


def sanitize_tts_content(content: str) -> str:
    content_without_mentions = re.sub(r"<@[!&]?\d+>|<#\d+>", "", content)
    content_without_markdown = strip_discord_markdown(content_without_mentions)
    content_without_emojis = re.sub(r"<a?:\w+:\d+>", "кастомный эмодзи", content_without_markdown)
    content_with_text_emojis = TEXT_EMOJI_PATTERN.sub("Эмодзи", content_without_emojis)
    content_with_unicode_emojis = replace_unicode_emojis(content_with_text_emojis)
    content_without_channels = re.sub(r"<#\d+>", "канал", content_with_unicode_emojis)
    content_with_gif_labels = GIF_URL_PATTERN.sub("Гифка", content_without_channels)
    content_with_video_labels = MP4_URL_PATTERN.sub("Видео", content_with_gif_labels)
    content_without_urls = URL_PATTERN.sub("ссылка", content_with_video_labels)
    content_with_collapsed_emojis = re.sub(r"(?:Эмодзи\s*){2,}", "Эмодзи ", content_without_urls)
    return content_with_collapsed_emojis.strip()


def sanitize_tts_name(name: str) -> str:
    sanitized_name = sanitize_tts_content(name)
    return sanitized_name or "Пользователь"


def detect_tts_language(text: str) -> str:
    latin_letters = len(re.findall(r"[A-Za-z]", text))
    cyrillic_letters = len(re.findall(r"[А-Яа-яЁё]", text))
    return "en" if latin_letters > cyrillic_letters else "ru"


def split_tts_text(text: str, chunk_size: int = MAX_TTS_CHUNK_LENGTH) -> list[str]:
    normalized_text = " ".join(text.split())
    if len(normalized_text) <= chunk_size:
        return [normalized_text]

    chunks = []
    current_chunk = []
    current_length = 0

    for word in normalized_text.split():
        word_length = len(word) + (1 if current_chunk else 0)
        if current_chunk and current_length + word_length > chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += word_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


class Tts(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data
        self.message_queue = Queue()
        self.is_playing = False
        self.worker_task = None
        self.last_user_message = {}
        self.pending_disconnects = {}

    async def disconnect_if_channel_empty(self, guild):
        voice_client = guild.voice_client
        if voice_client is None or voice_client.channel is None:
            return

        if self.is_playing or not self.message_queue.empty():
            return

        human_members = [member for member in voice_client.channel.members if not member.bot]
        if human_members:
            return

        await voice_client.disconnect(force=True)

    async def schedule_disconnect_check(self, guild):
        guild_id = guild.id

        existing_task = self.pending_disconnects.get(guild_id)
        if existing_task and not existing_task.done():
            existing_task.cancel()

        async def delayed_disconnect():
            try:
                await asyncio.sleep(EMPTY_CHANNEL_DISCONNECT_DELAY)
                await self.disconnect_if_channel_empty(guild)
            except asyncio.CancelledError:
                return
            finally:
                self.pending_disconnects.pop(guild_id, None)

        self.pending_disconnects[guild_id] = self.Bot.loop.create_task(delayed_disconnect())

    async def safe_typing_context(self, channel):
        if hasattr(channel, "typing"):
            try:
                return channel.typing()
            except Exception:
                return nullcontext()
        return nullcontext()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        voice_client = member.guild.voice_client
        if voice_client is None:
            return

        await self.schedule_disconnect_check(member.guild)

    @commands.Cog.listener()
    async def on_message(self, ctx):
        try:
            if not ctx.guild or ctx.author.bot:
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

            clean_content = sanitize_tts_content(ctx.content or "")
            attachment_labels = get_attachment_tts_labels(ctx)
            content_parts = [part for part in [clean_content, *attachment_labels] if part]
            if not content_parts:
                return
            clean_content = ". ".join(content_parts)

            current_time = discord.utils.utcnow()
            last_message_info = self.last_user_message.get(user.id, {"time": None})

            if last_message_info["time"] and (current_time - last_message_info["time"]).total_seconds() < 10:
                speech = clean_content
            else:
                speech = f"{sanitize_tts_name(user.display_name)} пишет: {clean_content}"

            self.last_user_message[user.id] = {"time": current_time}
            await self.message_queue.put((voice_channel, ctx.channel, speech))

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

        pending_disconnect = self.pending_disconnects.get(channel.guild.id)
        if pending_disconnect and not pending_disconnect.done():
            pending_disconnect.cancel()

        for _ in range(20):
            if voice_client.is_connected():
                return voice_client
            await asyncio.sleep(0.25)

        if hasattr(voice_client, "_connected"):
            await asyncio.to_thread(voice_client._connected.wait, 5)

        return voice_client

    async def play_audio_file(self, voice_client, temp_file: Path):
        playback_started = False
        last_error = None

        for attempt in range(3):
            if not voice_client:
                last_error = RuntimeError("Voice client was not created.")
                await asyncio.sleep(1)
                continue

            if voice_client.is_playing():
                voice_client.stop()

            await asyncio.sleep(0.25 + attempt * 0.25)

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
                    error = await asyncio.wait_for(playback, timeout=PLAYBACK_TIMEOUT)
                    if error:
                        raise error

                playback_started = True
                break
            except asyncio.TimeoutError:
                last_error = TimeoutError("TTS playback timed out.")
                if voice_client.is_playing():
                    voice_client.stop()
                print(f"TTS playback attempt {attempt + 1}/3 timed out.")
                await asyncio.sleep(1)
            except Exception as playback_error:
                last_error = playback_error
                print(f"TTS playback attempt {attempt + 1}/3 failed: {playback_error}")
                await asyncio.sleep(1)

        if not playback_started and last_error:
            raise last_error

    async def process_speech_chunks(self, voice_channel, source_channel, speech: str):
        language = detect_tts_language(speech)
        chunks = split_tts_text(speech)
        voice_client = await self.ensure_voice_client(voice_channel)

        typing_context = await self.safe_typing_context(source_channel)
        async with typing_context:
            for chunk in chunks:
                temp_file = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                        temp_file = Path(temp_audio.name)

                    await asyncio.wait_for(
                        asyncio.to_thread(gTTS(chunk, lang=language).save, str(temp_file)),
                        timeout=GTTS_GENERATION_TIMEOUT,
                    )
                    voice_client = await self.ensure_voice_client(voice_channel)
                    await self.play_audio_file(voice_client, temp_file)
                except asyncio.TimeoutError:
                    print("TTS chunk generation timed out, skipping chunk.")
                finally:
                    if temp_file and temp_file.exists():
                        temp_file.unlink(missing_ok=True)

    async def process_queue(self):
        if self.is_playing:
            return

        self.is_playing = True

        try:
            while not self.message_queue.empty():
                try:
                    voice_channel, source_channel, speech = await self.message_queue.get()
                    await self.process_speech_chunks(voice_channel, source_channel, speech)
                except Exception as exc:
                    print(f"Error during playback: {exc}")
                finally:
                    self.message_queue.task_done()

            for guild in self.Bot.guilds:
                await self.schedule_disconnect_check(guild)
        finally:
            self.is_playing = False


def setup(bot):
    bot.add_cog(Tts(bot, servers_data))
