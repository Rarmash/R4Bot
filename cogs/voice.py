from datetime import datetime

from discord.ext import commands, tasks

from modules.firebase import create_record, get_from_record, update_record


def is_voice_activity_counted(voice_state) -> bool:
    if voice_state is None or voice_state.channel is None:
        return False

    return not (
        voice_state.self_mute
        or voice_state.self_deaf
        or voice_state.mute
        or voice_state.deaf
    )


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}
        self.flush_voice_time.start()

    def cog_unload(self):
        self.flush_voice_time.cancel()

    def _get_session_key(self, guild_id: int, user_id: int):
        return f"{guild_id}:{user_id}"

    def _iter_session_parts(self):
        for session_key, started_at in self.active_sessions.items():
            guild_id, user_id = session_key.split(":", 1)
            yield int(guild_id), int(user_id), started_at

    def _start_session(self, guild_id: int, user_id: int):
        self.active_sessions[self._get_session_key(guild_id, user_id)] = datetime.utcnow()

    def _pop_session_start(self, guild_id: int, user_id: int):
        return self.active_sessions.pop(self._get_session_key(guild_id, user_id), None)

    def _add_voice_time(self, guild_id: int, user_id: int, seconds: int):
        if seconds <= 0:
            return

        guild_key = str(guild_id)
        user_key = str(user_id)
        user_record = get_from_record(guild_key, "Users", user_key)
        if user_record is None:
            create_record(guild_key, "Users", user_key, {"messages": 0, "timeouts": 0, "voice": seconds})
            return

        update_record(guild_key, "Users", user_key, {"voice": user_record.get("voice", 0) + seconds})

    def _flush_session(self, guild_id: int, user_id: int, started_at: datetime):
        elapsed_seconds = int((datetime.utcnow() - started_at).total_seconds())
        self._add_voice_time(guild_id, user_id, elapsed_seconds)
        self._start_session(guild_id, user_id)

    @tasks.loop(seconds=30)
    async def flush_voice_time(self):
        sessions = list(self._iter_session_parts())
        for guild_id, user_id, started_at in sessions:
            self._flush_session(guild_id, user_id, started_at)

    @flush_voice_time.before_loop
    async def before_flush_voice_time(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        self.active_sessions.clear()
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                for member in voice_channel.members:
                    if member.bot or not is_voice_activity_counted(member.voice):
                        continue
                    self._start_session(guild.id, member.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        guild_id = member.guild.id
        user_id = member.id
        was_counted = is_voice_activity_counted(before)
        is_counted = is_voice_activity_counted(after)

        if was_counted:
            started_at = self._pop_session_start(guild_id, user_id)
            if started_at is not None:
                elapsed_seconds = int((datetime.utcnow() - started_at).total_seconds())
                self._add_voice_time(guild_id, user_id, elapsed_seconds)

        if is_counted:
            self._start_session(guild_id, user_id)


def setup(bot):
    bot.add_cog(Voice(bot))
