# Разработка модулей для R4Bot

Этот документ описывает публичный контракт для внешних модулей R4Bot.

## Что считается публичным API

Для внешних модулей поддерживается только следующий слой:
- `bot.r4_services`
- `r4bot_sdk`
- `module.json`
- `requirements.txt`
- `*.example.json` для конфигов и секретов

Прямые импорты внутренних файлов ядра не считаются стабильным API.

## Базовый подход

Рекомендуемая структура модуля:

```txt
module.json
cog.py
service.py
requirements.txt
README.md
resources/
<module>.example.json
<module>.secrets.example.json
```

Границы ответственности такие:
- `cog.py` — Discord-обвязка, команды, listeners, регистрация Cog, основное поведение модуля
- `service.py` — необязательный слой для интеграций и расширений

Важно:
- `service.py` не должен автоматически считаться местом для всей логики модуля
- обычные slash-команды и базовое поведение вполне нормально оставлять в `cog.py`
- `service.py` полезен там, где модуль подключается к другим модулям или отдаёт им расширения

## SDK

Для модуля можно использовать:

```python
from r4bot_sdk import R4BotModule
```

Чтобы импорт работал в IDE и при установке модуля, добавьте SDK в `requirements.txt` модуля:

```txt
r4bot-sdk @ git+https://github.com/Rarmash/R4Bot-SDK.git@master
```

Для модулей используйте только `r4bot_sdk`. Внутренний код ядра бота не считается публичным API.

`R4BotModule` даёт:
- `get_server_data(guild_id)`
- `get_module_config(guild_id)`
- `get_module_secrets()`
- `get_secret(key, default=None)`
- `get_resource_path(*parts)`
- `is_module_enabled(module_id)`
- `register_hook_provider(hook_name, provider)`
- `unregister_hook_provider(hook_name)`
- `list_hook_providers(hook_name)`
- `collect_hook_results(hook_name, **payload)`
- `subscribe_hook_events(hook_name, listener)`
- `unsubscribe_hook_events(hook_name, listener)`

Также в модуле доступны:
- `self.bot`
- `self.services`
- `self.context`

## Пример структуры кода

### `cog.py`

```python
import discord

from r4bot_sdk import R4BotModule


class Example(R4BotModule):
    module_id = "example"

    module = discord.SlashCommandGroup("example", "Example")

    @module.command(description="Проверка модуля")
    async def ping(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await ctx.respond("Сервер ещё не настроен.", ephemeral=True)
            return

        await ctx.respond("Модуль работает.")


def setup(bot):
    bot.add_cog(Example(bot))
```

### `service.py`

```python
class ExampleService:
    def __init__(self, module):
        self.module = module
        self.bot = module.bot
        self.services = module.services

    def register_hooks(self):
        # Здесь модуль может зарегистрировать свои расширения.
        # Например:
        # self.module.register_hook_provider("consumer.fields", self.build_profile_field)
        pass

    def unregister_hooks(self):
        # Здесь модуль снимает расширения при выгрузке.
        # Например:
        # self.module.unregister_hook_provider("consumer.fields")
        pass
```

## `module.json`

Минимальный пример:

```json
{
  "id": "example",
  "name": "Example",
  "version": "1.0.0",
  "entrypoint": "cog",
  "description": "Example module for R4Bot.",
  "author": "YourName",
  "min_core_version": "2.0",
  "required_services": [
    "config"
  ]
}
```

## Конфиги и секреты

Обычные настройки модуля лежат в:

```txt
config/modules/<module_id>.json
```

Шаблон для автосоздания при установке:

```txt
<module_id>.example.json
```

Секреты модуля лежат в:

```txt
config/secrets/<module_id>.json
```

Шаблон для автосоздания при установке:

```txt
<module_id>.secrets.example.json
```

## Ресурсы

Если модулю нужны изображения или другие ассеты, храните их в:

```txt
resources/
```

В коде путь можно получить так:

```python
path = self.get_resource_path("image.png")
```

## Optional-интеграции

Модули могут расширять друг друга через хуки. Полезно мыслить это так:
- один модуль является поставщиком расширения
- другой модуль является потребителем расширения

Важно:
- если модуль-потребитель не установлен, это не должно считаться ошибкой
- provider можно зарегистрировать заранее
- потребитель просто использует его позже, если появится в рантайме

### Пример поставщика расширения

Допустим, есть модуль `reputation`, который хочет отдавать наружу дополнительное поле с репутацией участника.

```python
from r4bot_sdk import R4BotModule
from .service import ReputationService


class Reputation(R4BotModule):
    module_id = "reputation"

    def __init__(self, bot):
        super().__init__(bot)
        self.service = ReputationService(self)
        self.service.register_hooks()

    def cog_unload(self):
        self.service.unregister_hooks()
```

```python
class ReputationService:
    HOOK_NAME = "membercard.fields"

    def __init__(self, module):
        self.module = module

    def register_hooks(self):
        self.module.register_hook_provider(self.HOOK_NAME, self.build_reputation_field)

    def unregister_hooks(self):
        self.module.unregister_hook_provider(self.HOOK_NAME)

    async def build_reputation_field(self, ctx, member, user_data, server_data):
        return {
            "name": "Репутация",
            "value": str(user_data.get("reputation", 0)),
        }
```

### Пример потребителя расширения

Допустим, есть отдельный модуль `membercard`, который умеет собирать такие поля и показывать их в своей карточке.

```python
from r4bot_sdk import collect_hook_results
from discord.ext import commands
from .service import MemberCardService


class MemberCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.service = MemberCardService(bot)

    async def render_card(self, ctx, member, user_data, server_data):
        extra_fields = await self.service.collect_extra_fields(ctx, member, user_data, server_data)

        for field in extra_fields:
            print(field["name"], field["value"])
```

```python
class MemberCardService:
    HOOK_NAME = "membercard.fields"

    def __init__(self, bot):
        self.bot = bot

    async def collect_extra_fields(self, ctx, member, user_data, server_data):
        results = await collect_hook_results(
            self.bot,
            self.HOOK_NAME,
            ctx=ctx,
            member=member,
            user_data=user_data,
            server_data=server_data,
        )

        fields = []
        for _, result in results:
            if isinstance(result, dict):
                fields.append(result)
            elif isinstance(result, list):
                fields.extend(item for item in result if isinstance(item, dict))

        return fields
```

По такой же схеме можно строить и другие расширения:
- модуль-потребитель сам задаёт имя hook-канала и формат данных
- модуль-поставщик подключается к этому hook-каналу
- ядро при этом остаётся универсальным и не знает про конкретные типы расширений

## Зависимости

Зависимости модуля должны лежать в его собственном `requirements.txt`.

Ядро R4Bot не хранит модульные зависимости в корневом `requirements.txt`.
При установке и обновлении модуля его `requirements.txt` ставится автоматически через CLI.
Обновление выполняется только если `version` в `module.json` источника выше установленной версии.
Если код модуля изменился, но версия не поднята, `manage_modules.py update` пропустит этот модуль как актуальный.

## Создание каркаса

Новый модуль можно создать так:

```bash
python manage_modules.py create-module example --output C:\path\to\R4Bot-Module-Example
```

Генератор создаёт:
- `module.json`
- `cog.py`
- `service.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `<module>.example.json`
- `<module>.secrets.example.json`

## Проверка модуля

Перед установкой или публикацией можно прогнать валидацию:

```bash
python manage_modules.py validate path:C:\path\to\R4Bot-Module-Example
```

Или для GitHub-репозитория:

```bash
python manage_modules.py validate github:OWNER/REPO@master
```

## Локальная установка

```bash
python manage_modules.py install path:C:\path\to\R4Bot-Module-Example --enable
```

## Публикация

```bash
python manage_modules.py install github:OWNER/REPO@master --enable
```

## Практические рекомендации

- Не импортируйте внутренние файлы ядра напрямую.
- Не превращайте `service.py` в обязательную свалку всей логики.
- Держите в `service.py` то, что связано с расширениями, интеграциями и подключаемыми возможностями.
- Основное поведение slash-команд можно спокойно держать в `cog.py`, если так модуль понятнее.
- Держите обычные настройки и секреты в разных файлах.
- Все зависимости модуля храните внутри репозитория самого модуля.
