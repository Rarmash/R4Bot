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

from modules.server_config import respond_missing_server_config
from options import servers_data

FFMPEG_OPTIONS = {
    "before_options": "-nostdin",
    "options": '-vn -filter:a "atempo=1.6"',
}
MAX_TTS_CHUNK_LENGTH = 180
EMPTY_CHANNEL_DISCONNECT_DELAY = 3
GTTS_GENERATION_TIMEOUT = 20
PLAYBACK_TIMEOUT = 45
TTS_MESSAGE_TIMEOUT = 150
PLAYBACK_START_TIMEOUT = 3

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
        if is_emoji_character(char) or unicodedata.category(char) == "So":
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


def sanitize_tts_content(content: str) -> str:
    content = re.sub(r"<@[!&]?\d+>", "", content)
    content = re.sub(r"<#\d+>", "канал", content)
    content = strip_discord_markdown(content)
    content = re.sub(r"<a?:\w+:\d+>", "кастомный эмодзи", content)
    content = TEXT_EMOJI_PATTERN.sub("Эмодзи", content)
    content = replace_unicode_emojis(content)
    content = GIF_URL_PATTERN.sub("Гифка", content)
    content = MP4_URL_PATTERN.sub("Видео", content)
    content = URL_PATTERN.sub("ссылка", content)
    content = re.sub(r"(?:Эмодзи\s*){2,}", "Эмодзи ", content)
    return " ".join(content.split()).strip()


def sanitize_tts_name(name: str) -> str:
    sanitized = sanitize_tts_content(name)
    return sanitized or "Пользователь"


def detect_tts_language(text: str) -> str:
    latin_letters = len(re.findall(r"[A-Za-z]", text))
    cyrillic_letters = len(re.findall(r"[А-Яа-яЁё]", text))
    return "en" if latin_letters > cyrillic_letters else "ru"


def split_tts_text(text: str, chunk_size: int = MAX_TTS_CHUNK_LENGTH) -> list[str]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []
    if len(normalized_text) <= chunk_size:
        return [normalized_text]

    sentence_parts = re.split(r"(?<=[.!?])\s+", normalized_text)
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentence_parts:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) <= chunk_size:
            sentence_length = len(sentence) + (1 if current_chunk else 0)
            if current_chunk and current_length + sentence_length > chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = len(sentence)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
            continue

        for word in sentence.split():
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


def deduplicate_tts_parts(parts: list[str]) -> list[str]:
    unique_parts = []
    seen = set()

    for part in parts:
        normalized_part = " ".join(str(part).split()).strip()
        if not normalized_part:
            continue

        dedupe_key = normalized_part.casefold()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        unique_parts.append(normalized_part)

    return unique_parts


def get_message_tts_parts(message: discord.Message) -> list[str]:
    parts = []

    clean_content = sanitize_tts_content(message.content or "")
    if clean_content:
        parts.append(clean_content)

    for _sticker in getattr(message, "stickers", []):
        parts.append("Стикер")

    for attachment in getattr(message, "attachments", []):
        content_type = (attachment.content_type or "").lower()
        filename = (attachment.filename or "").lower()

        if "gif" in content_type or filename.endswith(".gif"):
            parts.append("Гифка")
        elif content_type.startswith("image/"):
            parts.append("Изображение")
        elif content_type.startswith("video/"):
            parts.append("Видео")
        elif content_type.startswith("audio/"):
            parts.append("Аудио")
        else:
            parts.append("Файл")

    for embed in getattr(message, "embeds", []):
        embed_type = (getattr(embed, "type", "") or "").lower()
        if embed_type == "gifv":
            parts.append("Гифка")
        elif embed_type in {"image", "video"}:
            parts.append("Изображение" if embed_type == "image" else "Видео")

    return deduplicate_tts_parts(parts)


class Tts(commands.Cog):
    def __init__(self, bot, servers_data):
        self.Bot = bot
        self.servers_data = servers_data
        self.message_queue = Queue()
        self.is_playing = False
        self.worker_task = None
        self.last_announced_author_by_channel = {}
        self.pending_disconnects = {}
        self.current_tts_id = None
        self.skipped_tts_ids = set()

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

    def can_skip_tts(self, ctx, server_data) -> bool:
        if ctx.author.id == ctx.guild.owner_id:
            return True

        admin_role = discord.utils.get(ctx.guild.roles, id=server_data.get("admin_role_id"))
        mod_role = discord.utils.get(ctx.guild.roles, id=server_data.get("mod_role_id"))
        return (
            (admin_role is not None and admin_role in ctx.author.roles)
            or (mod_role is not None and mod_role in ctx.author.roles)
        )

    async def reset_voice_client(self, guild):
        voice_client = guild.voice_client
        if voice_client is None:
            return

        try:
            if voice_client.is_playing():
                voice_client.stop()
        except Exception:
            pass

        try:
            await voice_client.disconnect(force=True)
        except Exception as exc:
            print(f"Error while resetting voice client: {exc}")

    async def safe_unlink_temp_file(self, temp_file: Path | None):
        if temp_file is None:
            return

        for attempt in range(5):
            try:
                temp_file.unlink(missing_ok=True)
                return
            except PermissionError:
                if attempt == 4:
                    print(f"Failed to remove temp TTS file after retries: {temp_file}")
                    return
                await asyncio.sleep(0.3 * (attempt + 1))
            except FileNotFoundError:
                return

    async def wait_for_playback_start(self, voice_client, playback, timeout: float) -> tuple[bool, object | None]:
        elapsed = 0.0
        step = 0.1

        while elapsed < timeout:
            if voice_client.is_playing():
                return True, None

            if playback and playback.done():
                return False, playback.result()

            await asyncio.sleep(step)
            elapsed += step

        if playback and playback.done():
            return False, playback.result()

        return False, None

    def build_speech_text(self, message: discord.Message) -> str | None:
        message_parts = get_message_tts_parts(message)
        if not message_parts:
            return None

        base_speech = ". ".join(message_parts)
        channel_id = message.channel.id
        previous_author_id = self.last_announced_author_by_channel.get(channel_id)
        should_include_author = previous_author_id != message.author.id
        self.last_announced_author_by_channel[channel_id] = message.author.id

        if should_include_author:
            return f"{sanitize_tts_name(message.author.display_name)} пишет: {base_speech}"

        return base_speech

    async def safe_typing_context(self, channel):
        if hasattr(channel, "typing"):
            try:
                return channel.typing()
            except Exception:
                return nullcontext()
        return nullcontext()

    @commands.slash_command(description="Пропустить текущее TTS-сообщение")
    @discord.guild_only()
    async def skiptts(self, ctx: discord.ApplicationContext):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await respond_missing_server_config(ctx)
            return

        if not self.can_skip_tts(ctx, server_data):
            await ctx.respond("Недостаточно прав для выполнения данной команды.", ephemeral=True)
            return

        if self.current_tts_id is None:
            await ctx.respond("Сейчас нет активного TTS-сообщения.", ephemeral=True)
            return

        self.skipped_tts_ids.add(self.current_tts_id)

        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()

        await ctx.respond("Текущее TTS-сообщение пропущено.", ephemeral=True)

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

            server_data = self.get_server_data(ctx.guild.id)
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

            speech = self.build_speech_text(ctx)
            if not speech:
                return

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

    async def play_audio_file(self, voice_channel, temp_file: Path, tts_id: int | None = None):
        playback_started = False
        last_error = None

        for attempt in range(3):
            if tts_id is not None and tts_id in self.skipped_tts_ids:
                return

            voice_client = await self.ensure_voice_client(voice_channel)
            if not voice_client:
                last_error = RuntimeError("Voice client was not created.")
                await asyncio.sleep(1)
                continue

            if not temp_file.exists() or temp_file.stat().st_size == 0:
                raise RuntimeError("TTS audio file was not created correctly.")

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

                started, early_error = await self.wait_for_playback_start(
                    voice_client,
                    playback,
                    timeout=PLAYBACK_START_TIMEOUT,
                )
                if not started:
                    if early_error:
                        raise early_error

                    if playback and playback.done():
                        playback_started = True
                        break

                    raise RuntimeError("Voice playback did not start.")

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
                if attempt == 2:
                    await self.reset_voice_client(voice_channel.guild)
                print(f"TTS playback attempt {attempt + 1}/3 timed out.")
                await asyncio.sleep(1)
            except Exception as playback_error:
                last_error = playback_error
                if attempt == 2:
                    await self.reset_voice_client(voice_channel.guild)
                print(f"TTS playback attempt {attempt + 1}/3 failed: {playback_error}")
                await asyncio.sleep(1)

        if not playback_started and last_error:
            raise last_error

    async def generate_tts_file(self, chunk: str, language: str) -> Path | None:
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                temp_file = Path(temp_audio.name)

            await asyncio.wait_for(
                asyncio.to_thread(gTTS(chunk, lang=language).save, str(temp_file)),
                timeout=GTTS_GENERATION_TIMEOUT,
            )
            return temp_file
        except asyncio.TimeoutError:
            print("TTS chunk generation timed out, skipping chunk.")
        except Exception as exc:
            print(f"TTS chunk generation failed: {exc}")

        await self.safe_unlink_temp_file(temp_file)
        return None

    async def process_speech_chunks(self, voice_channel, source_channel, speech: str, tts_id: int):
        chunks = split_tts_text(speech)
        if not chunks:
            return

        language = detect_tts_language(speech)

        typing_context = await self.safe_typing_context(source_channel)
        async with typing_context:
            next_file_task = asyncio.create_task(self.generate_tts_file(chunks[0], language))

            for index, _chunk in enumerate(chunks):
                temp_file = None
                try:
                    if tts_id in self.skipped_tts_ids:
                        break

                    temp_file = await next_file_task
                    if index + 1 < len(chunks):
                        next_file_task = asyncio.create_task(self.generate_tts_file(chunks[index + 1], language))
                    else:
                        next_file_task = None

                    if temp_file is None:
                        continue

                    await self.play_audio_file(voice_channel, temp_file, tts_id=tts_id)
                finally:
                    await self.safe_unlink_temp_file(temp_file)

            if next_file_task is not None and not next_file_task.done():
                next_file_task.cancel()

    async def process_queue(self):
        if self.is_playing:
            return

        self.is_playing = True
        try:
            while not self.message_queue.empty():
                try:
                    voice_channel, source_channel, speech = await self.message_queue.get()
                    current_tts_id = id((voice_channel.id, speech, discord.utils.utcnow().timestamp()))
                    self.current_tts_id = current_tts_id
                    await asyncio.wait_for(
                        self.process_speech_chunks(voice_channel, source_channel, speech, current_tts_id),
                        timeout=TTS_MESSAGE_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    print("TTS message processing timed out, resetting voice client and continuing.")
                    await self.reset_voice_client(voice_channel.guild)
                except Exception as exc:
                    print(f"Error during playback: {exc}")
                finally:
                    if self.current_tts_id is not None:
                        self.skipped_tts_ids.discard(self.current_tts_id)
                    self.current_tts_id = None
                    self.message_queue.task_done()

            for guild in self.Bot.guilds:
                await self.schedule_disconnect_check(guild)
        finally:
            self.is_playing = False


def setup(bot):
    bot.add_cog(Tts(bot, servers_data))
