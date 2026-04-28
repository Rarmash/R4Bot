from __future__ import annotations

import json
import re
from pathlib import Path

from core.version import VERSION


class ModuleGeneratorError(Exception):
    """Raised when a new module scaffold cannot be generated."""


class ModuleGenerator:
    def generate(
        self,
        module_id: str,
        output_dir: Path,
        *,
        name: str | None = None,
        author: str = "",
        description: str = "",
        overwrite: bool = False,
        include_config_template: bool = True,
        include_secrets_template: bool = True,
    ) -> Path:
        normalized_module_id = self._normalize_module_id(module_id)
        module_name = name or self._module_name_from_id(normalized_module_id)
        class_name = self._class_name_from_id(normalized_module_id)
        target_dir = output_dir.resolve()

        if target_dir.exists() and any(target_dir.iterdir()) and not overwrite:
            raise ModuleGeneratorError(
                f"Target directory is not empty: {target_dir}. Use --overwrite to scaffold into it."
            )

        target_dir.mkdir(parents=True, exist_ok=True)

        self._write_json(
            target_dir / "module.json",
            {
                "id": normalized_module_id,
                "name": module_name,
                "version": "1.0.0",
                "entrypoint": "cog",
                "description": description or f"{module_name} module for R4Bot.",
                "author": author,
                "min_core_version": VERSION,
                "required_services": ["config"],
            },
        )
        self._write_text(target_dir / "requirements.txt", "py-cord>=2.6.0\n")
        self._write_text(target_dir / ".gitignore", "__pycache__/\n*.pyc\n.venv/\n")
        self._write_text(
            target_dir / "README.md",
            self._build_readme(
                module_id=normalized_module_id,
                module_name=module_name,
            ),
        )
        self._write_text(
            target_dir / "cog.py",
            self._build_cog(
                module_id=normalized_module_id,
                class_name=class_name,
                module_name=module_name,
            ),
        )
        self._write_text(target_dir / "service.py", self._build_service(class_name=class_name))

        if include_config_template:
            self._write_json(target_dir / f"{normalized_module_id}.example.json", {})

        if include_secrets_template:
            self._write_json(target_dir / f"{normalized_module_id}.secrets.example.json", {})

        return target_dir

    @staticmethod
    def _normalize_module_id(module_id: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", module_id.strip()).strip("-_").lower()
        if not normalized:
            raise ModuleGeneratorError("Module id cannot be empty.")
        return normalized

    @staticmethod
    def _module_name_from_id(module_id: str) -> str:
        parts = [part for part in re.split(r"[-_]+", module_id) if part]
        return " ".join(part.capitalize() for part in parts) or module_id

    @staticmethod
    def _class_name_from_id(module_id: str) -> str:
        parts = [part for part in re.split(r"[^a-zA-Z0-9]+", module_id) if part]
        return "".join(part.capitalize() for part in parts) or "Module"

    @staticmethod
    def _write_text(path: Path, content: str):
        path.write_text(content, encoding="utf8")

    @staticmethod
    def _write_json(path: Path, payload: dict):
        with path.open("w", encoding="utf8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")

    @staticmethod
    def _build_readme(module_id: str, module_name: str) -> str:
        return f"""# {module_name}

Модуль `{module_id}` для R4Bot.

## Структура

- `module.json`
- `cog.py`
- `service.py`
- `requirements.txt`
- `{module_id}.example.json`
- `{module_id}.secrets.example.json`

`cog.py` отвечает за Discord-обвязку, команды и основное поведение модуля.
`service.py` — это необязательный слой для интеграций и расширений, если модуль
должен подключаться к другим модулям или расширять их функциональность.

## Локальная установка

```bash
python manage_modules.py install path:. --enable
```

## Публикация

После пуша в GitHub модуль можно ставить так:

```bash
python manage_modules.py install github:OWNER/REPO@master --enable
```
"""

    @staticmethod
    def _build_cog(module_id: str, class_name: str, module_name: str) -> str:
        return f"""import discord

from core.sdk import R4BotModule


class {class_name}(R4BotModule):
    module_id = "{module_id}"

    module = discord.SlashCommandGroup("{module_id}", "{module_name}")

    @module.command(description="Проверка модуля")
    async def ping(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await ctx.respond("Сервер ещё не настроен.", ephemeral=True)
            return

        await ctx.respond("Модуль работает.")


def setup(bot):
    bot.add_cog({class_name}(bot))
"""

    @staticmethod
    def _build_service(class_name: str) -> str:
        return f"""class {class_name}Service:
    def __init__(self, module):
        self.module = module
        self.bot = module.bot
        self.services = module.services

    def register_hooks(self):
        # Здесь модуль может зарегистрировать optional-интеграции
        # и подключаемые возможности.
        pass

    def unregister_hooks(self):
        # Здесь модуль снимает свои hook-и при выгрузке.
        pass
"""
