import datetime
import json
import os
import time
from math import ceil
from pathlib import Path

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from core.module_manifest import ModuleManifest
from core.module_state import ModuleStateStore


CONFIG_NOT_INITIALIZED_MESSAGE = "Сервер ещё не настроен. Владелец сервера может выполнить `/service initserver`."
DEFAULT_ACCENT_COLOR = "0x209af8"
DEFAULT_SERVER_CONFIG = {
    "accent_color": DEFAULT_ACCENT_COLOR,
    "admin_id": 0,
    "mod_role_id": 0,
    "insider_id": 0,
    "admin_role_id": 0,
}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf8") as file:
        return json.load(file)


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8") as file:
        json.dump(payload, file, indent=4, ensure_ascii=False)


def build_server_config(admin_id: int) -> dict:
    payload = dict(DEFAULT_SERVER_CONFIG)
    payload["admin_id"] = admin_id
    return payload


def initialize_server_config(path: Path, guild_id: int, admin_id: int, overwrite: bool = False) -> tuple[dict, bool]:
    payload = read_json(path) or {"cogs": []}
    guild_key = str(guild_id)
    already_exists = guild_key in payload

    if already_exists and not overwrite:
        return payload[guild_key], False

    payload[guild_key] = build_server_config(admin_id)
    write_json(path, payload)
    return payload[guild_key], True


async def respond_missing_server_config(target):
    if hasattr(target, "respond"):
        await target.respond(CONFIG_NOT_INITIALIZED_MESSAGE, ephemeral=True)
        return

    response = getattr(target, "response", None)
    if response is not None and not response.is_done():
        await response.send_message(CONFIG_NOT_INITIALIZED_MESSAGE, ephemeral=True)
        return

    followup = getattr(target, "followup", None)
    if followup is not None:
        await followup.send(CONFIG_NOT_INITIALIZED_MESSAGE, ephemeral=True)


def read_env_lines(env_path: Path):
    if not env_path.exists():
        return []

    lines = []
    for raw_line in env_path.read_text(encoding="utf8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        lines.append((key.strip(), value.strip()))
    return lines


class Service(commands.Cog):
    service = SlashCommandGroup("service", "Сервисные команды")

    def __init__(self, bot):
        self.bot = bot
        self.services = bot.r4_services
        self.config = self.services.config
        self.state_store = ModuleStateStore(self.config.paths.module_state_file)

    def get_server_data(self, guild_id: int):
        return self.config.get_servers_data().get(str(guild_id))

    async def get_server_data_or_notify(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if server_data:
            return server_data

        await respond_missing_server_config(ctx)
        return None

    async def deny_if_not_admin(self, ctx, server_data) -> bool:
        if ctx.author.id == ctx.guild.owner_id:
            return False
        if ctx.author.id == server_data.get("admin_id"):
            return False

        await ctx.respond("Недостаточно прав для выполнения данной команды.", ephemeral=True)
        return True

    def get_manifest_path(self, module_id: str):
        return self.config.paths.installed_modules_dir / module_id / "module.json"

    def get_module_manifest(self, module_id: str):
        manifest_path = self.get_manifest_path(module_id)
        if not manifest_path.exists():
            return None
        return ModuleManifest.from_file(manifest_path)

    def get_extension_path(self, module_id: str):
        manifest = self.get_module_manifest(module_id)
        if manifest is None:
            return None
        return manifest.to_import_path()

    def get_installed_module(self, module_id: str):
        return self.state_store.list_installed().get(module_id)

    @staticmethod
    def build_source_label(module_data: dict) -> str:
        source = module_data.get("source", "unknown")
        if source == "github" and module_data.get("repo"):
            repo = module_data["repo"]
            ref = module_data.get("ref", "main")
            return f"[{repo}@{ref}](https://github.com/{repo})"
        if source == "path" and module_data.get("path"):
            return f"`path` `{module_data['path']}`"
        return f"`{source}`"

    @service.command(description="Создать минимальный конфиг для сервера")
    @discord.option("overwrite", description="Перезаписать уже существующий конфиг", default=False, required=False)
    @discord.guild_only()
    async def initserver(self, ctx, overwrite: bool = False):
        existing_server_data = self.get_server_data(ctx.guild.id)
        has_access = ctx.author.id == ctx.guild.owner_id
        if existing_server_data and ctx.author.id == existing_server_data.get("admin_id"):
            has_access = True

        if not has_access:
            await ctx.respond(
                "Инициализировать конфиг сервера может только владелец сервера или админ бота для этого сервера.",
                ephemeral=True,
            )
            return

        if existing_server_data and not overwrite:
            await ctx.respond(
                "Для этого сервера конфиг уже существует. Если нужно пересоздать его, укажи `overwrite: true`.",
                ephemeral=True,
            )
            return

        config, created = initialize_server_config(
            path=self.services.config.paths.servers_config,
            guild_id=ctx.guild.id,
            admin_id=ctx.guild.owner_id,
            overwrite=overwrite,
        )
        self.services.config.servers_data[str(ctx.guild.id)] = config

        status = "создан" if created else "обновлён"
        await ctx.respond(
            f"Минимальный конфиг сервера {status}. Теперь можно донастроить `servers.json` под каналы, роли и ID.",
            ephemeral=True,
        )

    @service.command(description="Отправить конфиги и секреты")
    async def secrets(self, ctx):
        server_data = await self.get_server_data_or_notify(ctx)
        if not server_data:
            return

        if await self.deny_if_not_admin(ctx, server_data):
            return

        env_lines = read_env_lines(self.services.config.paths.env_file)
        files_to_send = []

        candidates = [self.services.config.paths.servers_config]
        candidates.extend(sorted(self.services.config.paths.module_configs_dir.glob("*.json")))
        candidates.extend(sorted(self.services.config.paths.secrets_dir.glob("*.json")))

        for path in candidates:
            if path.exists():
                files_to_send.append(discord.File(path))

        if not env_lines and not files_to_send:
            await ctx.respond("Файлы конфигов и секретов не найдены.", ephemeral=True)
            return

        await ctx.respond("Скинул конфиги и секреты в ЛС.")

        if env_lines:
            secret_text = "\n".join(f"{key}={value}" for key, value in env_lines)
            await ctx.author.send(f"```env\n{secret_text}\n```")

        chunk = []
        for file in files_to_send:
            chunk.append(file)
            if len(chunk) == 10:
                await ctx.author.send(files=chunk)
                chunk = []

        if chunk:
            await ctx.author.send(files=chunk)

    @service.command(description="Выключить бота")
    async def shutdown(self, ctx):
        server_data = await self.get_server_data_or_notify(ctx)
        if not server_data:
            return

        if await self.deny_if_not_admin(ctx, server_data):
            return

        await ctx.respond("Завершение работы... :wave:")
        os.abort()

    @service.command(description="Посмотреть список установленных модулей")
    @discord.guild_only()
    async def modules(self, ctx):
        server_data = await self.get_server_data_or_notify(ctx)
        if not server_data:
            return

        installed = self.state_store.list_installed()
        if not installed:
            await ctx.respond("Установленных модулей пока нет.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Установленные модули",
            color=int(server_data.get("accent_color"), 16),
        )

        for module_id, data in sorted(installed.items()):
            status = "включён" if data.get("enabled") else "выключен"
            version = data.get("version", "?")
            embed.add_field(
                name=f"{data.get('name', module_id)} ({module_id})",
                value=(
                    f"Версия: `{version}`\n"
                    f"Статус: `{status}`\n"
                    f"Источник: {self.build_source_label(data)}"
                ),
                inline=False,
            )

        await ctx.respond(embed=embed, ephemeral=True)

    @service.command(description="Посмотреть информацию об установленном модуле")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def moduleinfo(self, ctx, module_id):
        server_data = await self.get_server_data_or_notify(ctx)
        if not server_data:
            return

        module_data = self.get_installed_module(module_id)
        if module_data is None:
            await ctx.respond(f"Модуль `{module_id}` не установлен.", ephemeral=True)
            return

        manifest = self.get_module_manifest(module_id)
        embed = discord.Embed(
            title=f"Информация о модуле {module_data.get('name', module_id)}",
            color=int(server_data.get("accent_color"), 16),
        )
        embed.add_field(name="ID", value=f"`{module_id}`")
        embed.add_field(name="Версия", value=f"`{module_data.get('version', '?')}`")
        embed.add_field(name="Статус", value="Включён" if module_data.get("enabled") else "Выключен")
        embed.add_field(name="Источник", value=self.build_source_label(module_data), inline=False)

        if manifest is not None:
            embed.add_field(name="Entrypoint", value=f"`{manifest.entrypoint}`", inline=False)
            embed.add_field(name="Автор", value=manifest.author or "Не указан")
            embed.add_field(name="Min core", value=manifest.min_core_version or "Не указана")
            embed.add_field(name="Описание", value=manifest.description or "Отсутствует", inline=False)

        if module_data.get("path"):
            embed.add_field(name="Путь", value=f"`{module_data['path']}`", inline=False)

        await ctx.respond(embed=embed, ephemeral=True)

    @service.command(description="Включить установленный модуль")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def enablemodule(self, ctx, module_id):
        server_data = await self.get_server_data_or_notify(ctx)
        if not server_data:
            return
        if await self.deny_if_not_admin(ctx, server_data):
            return

        module_data = self.get_installed_module(module_id)
        if module_data is None:
            await ctx.respond(f"Модуль `{module_id}` не установлен.", ephemeral=True)
            return
        if module_data.get("enabled"):
            await ctx.respond(f"Модуль `{module_id}` уже включён.", ephemeral=True)
            return

        extension_path = self.get_extension_path(module_id)
        if extension_path is None:
            await ctx.respond(f"У модуля `{module_id}` отсутствует `module.json`.", ephemeral=True)
            return

        self.state_store.set_enabled(module_id, True)
        try:
            self.bot.load_extension(extension_path)
        except Exception as exc:
            self.state_store.set_enabled(module_id, False)
            await ctx.respond(f"Не удалось включить модуль `{module_id}`: {exc}", ephemeral=True)
            return

        await ctx.respond(f"Модуль `{module_id}` включён.", ephemeral=True)

    @service.command(description="Выключить установленный модуль")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def disablemodule(self, ctx, module_id):
        server_data = await self.get_server_data_or_notify(ctx)
        if not server_data:
            return
        if await self.deny_if_not_admin(ctx, server_data):
            return

        module_data = self.get_installed_module(module_id)
        if module_data is None:
            await ctx.respond(f"Модуль `{module_id}` не установлен.", ephemeral=True)
            return
        if not module_data.get("enabled"):
            await ctx.respond(f"Модуль `{module_id}` уже выключен.", ephemeral=True)
            return

        extension_path = self.get_extension_path(module_id)
        if extension_path and extension_path in self.bot.extensions:
            try:
                self.bot.unload_extension(extension_path)
            except Exception as exc:
                await ctx.respond(f"Не удалось выгрузить модуль `{module_id}`: {exc}", ephemeral=True)
                return

        self.state_store.set_enabled(module_id, False)
        await ctx.respond(f"Модуль `{module_id}` выключен.", ephemeral=True)

    @service.command(description="Перезагрузить установленный модуль")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def reloadmodule(self, ctx, module_id):
        server_data = await self.get_server_data_or_notify(ctx)
        if not server_data:
            return
        if await self.deny_if_not_admin(ctx, server_data):
            return

        module_data = self.get_installed_module(module_id)
        if module_data is None:
            await ctx.respond(f"Модуль `{module_id}` не установлен.", ephemeral=True)
            return
        if not module_data.get("enabled"):
            await ctx.respond(f"Модуль `{module_id}` выключен. Сначала включи его.", ephemeral=True)
            return

        extension_path = self.get_extension_path(module_id)
        if extension_path is None:
            await ctx.respond(f"У модуля `{module_id}` отсутствует `module.json`.", ephemeral=True)
            return

        try:
            if extension_path in self.bot.extensions:
                self.bot.unload_extension(extension_path)
            self.bot.load_extension(extension_path)
        except Exception as exc:
            await ctx.respond(f"Не удалось перезагрузить модуль `{module_id}`: {exc}", ephemeral=True)
            return

        await ctx.respond(f"Модуль `{module_id}` перезагружен.", ephemeral=True)


def setup(bot):
    bot.add_cog(Service(bot))
