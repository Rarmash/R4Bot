import asyncio
import re
import tempfile
import unicodedata
from asyncio import Queue
from contextlib import nullcontext
from pathlib import Path
from time import monotonic

import discord
from discord.ext import commands
from gtts import gTTS

from options import servers_data

FFMPEG_OPTIONS = {
    "before_options": "-nostdin",
    "options": '-vn -filter:a "atempo=1.6"',
}
MAX_TTS_CHUNK_LENGTH = 140
MIN_TTS_RETRY_CHUNK_LENGTH = 45
EMPTY_CHANNEL_DISCONNECT_DELAY = 3
TTS_VOICE_LIMIT_CONFIG_KEY = "tts_voice_limit"
GTTS_GENERATION_TIMEOUT = 35
GTTS_GENERATION_ATTEMPTS = 2
PLAYBACK_TIMEOUT = 45
TTS_MESSAGE_TIMEOUT = 240
PLAYBACK_START_TIMEOUT = 3
PUNCTUATION_BREAK_CHARS = ".!?…;:,"
VOICE_CLIENT_MAX_AGE = 18 * 60

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


def find_split_index(text: str, chunk_size: int) -> int:
    window = text[: chunk_size + 1]
    min_punctuation_index = max(20, chunk_size // 3)

    for index in range(min(len(window) - 1, chunk_size), min_punctuation_index - 1, -1):
        if window[index] in PUNCTUATION_BREAK_CHARS:
            return index + 1

    min_space_index = max(10, chunk_size // 3)
    space_index = window.rfind(" ", 0, chunk_size + 1)
    if space_index >= min_space_index:
        return space_index

    return chunk_size


def split_tts_text(text: str, chunk_size: int = MAX_TTS_CHUNK_LENGTH) -> list[str]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []
    if len(normalized_text) <= chunk_size:
        return [normalized_text]

    chunks = []
    remaining_text = normalized_text

    while len(remaining_text) > chunk_size:
        split_index = find_split_index(remaining_text, chunk_size)
        chunk = remaining_text[:split_index].strip()
        if chunk:
            chunks.append(chunk)
        remaining_text = remaining_text[split_index:].strip()

    if remaining_text:
        chunks.append(remaining_text)

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
        self.voice_connected_at_by_guild = {}
        self.voice_limit_lock = asyncio.Lock()

    def get_tts_voice_limit_config(self, guild_id: int) -> dict | None:
        server_data = self.get_server_data(guild_id)
        if not server_data:
            return None

        config = server_data.get(TTS_VOICE_LIMIT_CONFIG_KEY)
        return config if isinstance(config, dict) else None

    async def expand_voice_channel_for_tts(self, channel: discord.VoiceChannel | None):
        if channel is None:
            return

        if not isinstance(channel, discord.VoiceChannel):
            return

        async with self.voice_limit_lock:
            parsed_config = self.parse_tts_voice_limit_config(self.get_tts_voice_limit_config(channel.guild.id))
            if parsed_config is None:
                return

            configured_channel_id, configured_limit = parsed_config
            if channel.id != configured_channel_id:
                return

            human_member_count = sum(1 for member in channel.members if not member.bot)
            if channel.user_limit != configured_limit or human_member_count > configured_limit - 1:
                return

            try:
                await channel.edit(
                    user_limit=configured_limit + 1,
                    reason="R4Bot TTS temporary voice slot",
                )
            except Exception as exc:
                print(f"Failed to expand TTS voice channel limit: {exc}")

    def is_bot_in_channel(self, channel: discord.VoiceChannel) -> bool:
        bot_user = self.Bot.user
        return bot_user is not None and any(member.id == bot_user.id for member in channel.members)

    @staticmethod
    def parse_tts_voice_limit_config(config: dict | None) -> tuple[int, int] | None:
        if not config:
            return None

        try:
            channel_id = int(config.get("channel_id"))
            limit = int(config.get("limit"))
        except (TypeError, ValueError):
            return None

        if channel_id <= 0 or limit <= 0:
            return None

        return channel_id, limit

    async def restore_voice_channel_from_config(self, channel: discord.VoiceChannel | None, config: dict | None):
        if channel is None or not isinstance(channel, discord.VoiceChannel):
            return

        parsed_config = self.parse_tts_voice_limit_config(config)
        if parsed_config is None:
            return

        tracked_channel_id, original_limit = parsed_config
        if channel.id != tracked_channel_id:
            return

        if self.is_bot_in_channel(channel):
            return

        if channel.user_limit == original_limit:
            return

        try:
            await channel.edit(
                user_limit=original_limit,
                reason="R4Bot TTS temporary voice slot released",
            )
        except Exception as exc:
            print(f"Failed to restore TTS voice channel limit: {exc}")
            return

    async def restore_voice_channel_limit_if_needed(self, channel: discord.VoiceChannel | None):
        if channel is None or not isinstance(channel, discord.VoiceChannel):
            return

        async with self.voice_limit_lock:
            config = self.get_tts_voice_limit_config(channel.guild.id)
            await self.restore_voice_channel_from_config(channel, config)

    async def restore_tracked_voice_limits_without_bot(self):
        for guild in self.Bot.guilds:
            config = self.get_tts_voice_limit_config(guild.id)
            if not config:
                continue

            try:
                tracked_channel_id = int(config.get("channel_id"))
            except (TypeError, ValueError):
                continue

            for channel in guild.voice_channels:
                if channel.id == tracked_channel_id:
                    await self.restore_voice_channel_limit_if_needed(channel)
                    break

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
        voice_channel = voice_client.channel if voice_client is not None else None
        self.voice_connected_at_by_guild.pop(guild.id, None)
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
        finally:
            await self.restore_voice_channel_limit_if_needed(voice_channel)

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

        voice_channel = voice_client.channel
        await voice_client.disconnect(force=True)
        await self.restore_voice_channel_limit_if_needed(voice_channel)

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
        bot_user = self.Bot.user
        if bot_user is not None and member.id == bot_user.id:
            if before.channel != after.channel:
                await self.restore_voice_channel_limit_if_needed(before.channel)
            return

        if member.bot:
            return

        voice_client = member.guild.voice_client
        if voice_client is None:
            return

        await self.schedule_disconnect_check(member.guild)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.restore_tracked_voice_limits_without_bot()

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

    def is_voice_client_stale(self, guild_id: int) -> bool:
        connected_at = self.voice_connected_at_by_guild.get(guild_id)
        if connected_at is None:
            return False

        return monotonic() - connected_at >= VOICE_CLIENT_MAX_AGE

    async def ensure_voice_client(self, channel):
        voice_client = channel.guild.voice_client

        if voice_client and not voice_client.is_connected():
            voice_channel = voice_client.channel
            await voice_client.disconnect(force=True)
            await self.restore_voice_channel_limit_if_needed(voice_channel)
            voice_client = None
            self.voice_connected_at_by_guild.pop(channel.guild.id, None)

        if voice_client and self.is_voice_client_stale(channel.guild.id):
            print("TTS voice client is stale, reconnecting before playback.")
            await self.reset_voice_client(channel.guild)
            voice_client = None

        if voice_client is None:
            await self.expand_voice_channel_for_tts(channel)
            try:
                voice_client = await channel.connect(timeout=30.0, reconnect=True)
            except Exception:
                await self.restore_voice_channel_limit_if_needed(channel)
                raise
            self.voice_connected_at_by_guild[channel.guild.id] = monotonic()
        elif voice_client.channel != channel:
            previous_channel = voice_client.channel
            previous_limit_config = self.get_tts_voice_limit_config(channel.guild.id)
            await self.expand_voice_channel_for_tts(channel)
            try:
                await voice_client.move_to(channel)
            except Exception:
                await self.restore_voice_channel_limit_if_needed(channel)
                raise
            await self.restore_voice_channel_from_config(previous_channel, previous_limit_config)
            self.voice_connected_at_by_guild[channel.guild.id] = monotonic()

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
                await self.reset_voice_client(voice_channel.guild)
                print(f"TTS playback attempt {attempt + 1}/3 timed out.")
                await asyncio.sleep(1)
            except Exception as playback_error:
                last_error = playback_error
                await self.reset_voice_client(voice_channel.guild)
                print(f"TTS playback attempt {attempt + 1}/3 failed: {playback_error}")
                await asyncio.sleep(1)

        if not playback_started and last_error:
            raise last_error

    @staticmethod
    def save_tts_chunk(chunk: str, language: str, temp_file: Path):
        gTTS(chunk, lang=language).save(str(temp_file))

    async def generate_tts_file(self, chunk: str, language: str) -> Path | None:
        temp_file = None

        for attempt in range(GTTS_GENERATION_ATTEMPTS):
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                    temp_file = Path(temp_audio.name)

                timeout = GTTS_GENERATION_TIMEOUT + attempt * 10
                await asyncio.wait_for(
                    asyncio.to_thread(self.save_tts_chunk, chunk, language, temp_file),
                    timeout=timeout,
                )

                if temp_file.exists() and temp_file.stat().st_size > 0:
                    return temp_file

                print("TTS chunk generation produced an empty file.")
            except asyncio.TimeoutError:
                print(f"TTS chunk generation attempt {attempt + 1}/{GTTS_GENERATION_ATTEMPTS} timed out.")
            except Exception as exc:
                print(f"TTS chunk generation attempt {attempt + 1}/{GTTS_GENERATION_ATTEMPTS} failed: {exc}")

            await self.safe_unlink_temp_file(temp_file)
            temp_file = None
            await asyncio.sleep(0.5 * (attempt + 1))

        return None

    async def generate_tts_files_for_chunk(self, chunk: str, language: str, depth: int = 0) -> list[Path]:
        temp_file = await self.generate_tts_file(chunk, language)
        if temp_file is not None:
            return [temp_file]

        if depth >= 3 or len(chunk) <= MIN_TTS_RETRY_CHUNK_LENGTH:
            print("TTS chunk generation failed after retries, skipping smallest chunk.")
            return []

        fallback_size = max(MIN_TTS_RETRY_CHUNK_LENGTH, min(MAX_TTS_CHUNK_LENGTH, len(chunk) // 2))
        fallback_chunks = split_tts_text(chunk, chunk_size=fallback_size)
        if len(fallback_chunks) <= 1:
            print("TTS chunk generation failed and chunk cannot be split further.")
            return []

        print(f"TTS chunk generation failed, retrying as {len(fallback_chunks)} smaller chunks.")
        files = []
        for fallback_chunk in fallback_chunks:
            files.extend(await self.generate_tts_files_for_chunk(fallback_chunk, language, depth=depth + 1))
        return files

    async def process_speech_chunks(self, voice_channel, source_channel, speech: str, tts_id: int):
        chunks = split_tts_text(speech)
        if not chunks:
            return

        language = detect_tts_language(speech)

        typing_context = await self.safe_typing_context(source_channel)
        async with typing_context:
            for chunk in chunks:
                temp_files = []
                try:
                    if tts_id in self.skipped_tts_ids:
                        break

                    temp_files = await self.generate_tts_files_for_chunk(chunk, language)
                    if not temp_files:
                        continue

                    for temp_file in temp_files:
                        if tts_id in self.skipped_tts_ids:
                            break
                        await self.play_audio_file(voice_channel, temp_file, tts_id=tts_id)
                finally:
                    for temp_file in temp_files:
                        await self.safe_unlink_temp_file(temp_file)

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
