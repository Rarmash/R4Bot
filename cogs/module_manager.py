import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from core.module_manifest import ModuleManifest
from core.module_state import ModuleStateStore
from modules.server_config import respond_missing_server_config
from options import servers_data
from services.config_service import ConfigService


class ModuleManager(commands.Cog):
    module = SlashCommandGroup("module", "Управление установленными модулями")

    def __init__(self, bot, servers_data):
        self.bot = bot
        self.servers_data = servers_data
        self.config = ConfigService()
        self.state_store = ModuleStateStore(self.config.paths.module_state_file)

    def get_server_data(self, guild_id: int):
        return self.servers_data.get(str(guild_id))

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

    @module.command(description="Посмотреть список установленных модулей")
    @discord.guild_only()
    async def list(self, ctx):
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

    @module.command(description="Посмотреть информацию об установленном модуле")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def info(self, ctx, module_id):
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

    @module.command(description="Включить установленный модуль")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def enable(self, ctx, module_id):
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

    @module.command(description="Выключить установленный модуль")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def disable(self, ctx, module_id):
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

    @module.command(description="Перезагрузить установленный модуль")
    @discord.option("module_id", str, description="ID модуля")
    @discord.guild_only()
    async def reload(self, ctx, module_id):
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
    bot.add_cog(ModuleManager(bot, servers_data))
