# Разработка модулей для R4Bot

Этот документ описывает публичный контракт для внешних модулей R4Bot.

## Что считается публичным API

Для модулей поддерживается только этот слой:

- `r4bot_sdk`;
- `bot.r4_services`;
- `module.json`;
- `requirements.txt`;
- `<module_id>.example.json`;
- `<module_id>.secrets.example.json`;
- папка `resources/`.

Не импортируйте внутренние файлы ядра напрямую. Если модулю нужен новый тип интеграции, лучше оформить его через hook или добавить возможность в SDK.

## Репозиторий модуля

Рекомендуемая структура:

```text
module.json
cog.py
service.py
requirements.txt
README.md
resources/
<module_id>.example.json
<module_id>.secrets.example.json
```

Обязательные файлы:

- `module.json`;
- `cog.py`;
- `requirements.txt`.

Необязательные файлы:

- `service.py`;
- `README.md`;
- `resources/`;
- example-конфиги и example-секреты.

## `cog.py` и `service.py`

`cog.py` отвечает за Discord-часть:

- slash-команды;
- listeners;
- UI-компоненты;
- регистрацию Cog;
- основное поведение модуля.

`service.py` нужен не для всей логики модуля, а для интеграций и расширений.

Хорошие кандидаты для `service.py`:

- регистрация hook-провайдеров;
- сбор данных из hook-потребителей;
- optional-интеграции с другими модулями;
- подключаемые возможности, которые другой модуль может использовать.

Обычную логику команд можно спокойно оставлять в `cog.py`, если так модуль понятнее.

## SDK

Добавьте SDK в `requirements.txt` модуля:

```txt
r4bot-sdk @ git+https://github.com/Rarmash/R4Bot-SDK.git@master
```

Базовый импорт:

```python
from r4bot_sdk import R4BotModule
```

`R4BotModule` даёт:

- `self.bot`;
- `self.services`;
- `self.context`;
- `get_server_data(guild_id)`;
- `get_module_config(guild_id)`;
- `get_module_secrets()`;
- `get_secret(key, default=None)`;
- `get_resource_path(*parts)`;
- `is_module_enabled(module_id)`;
- `register_hook_provider(hook_name, provider)`;
- `unregister_hook_provider(hook_name)`;
- `list_hook_providers(hook_name)`;
- `collect_hook_results(hook_name, **payload)`;
- `subscribe_hook_events(hook_name, listener)`;
- `unsubscribe_hook_events(hook_name, listener)`.

## Runtime services

Модуль получает общие сервисы через:

```python
self.services
```

или:

```python
bot.r4_services
```

Доступные сервисы:

- `config`;
- `firebase`;
- `module_config`;
- `module_state`;
- `resources`;
- `secrets`.

Пример:

```python
server_data = self.get_server_data(ctx.guild.id)
module_config = self.get_module_config(ctx.guild.id)
api_key = self.get_secret("api_key")
image_path = self.get_resource_path("banner.png")
```

## Минимальный `cog.py`

```python
import discord

from r4bot_sdk import R4BotModule


class Example(R4BotModule):
    module_id = "example"

    module = discord.SlashCommandGroup("example", "Example")

    @module.command(description="Проверить модуль")
    async def ping(self, ctx):
        server_data = self.get_server_data(ctx.guild.id)
        if not server_data:
            await ctx.respond("Сервер ещё не настроен.", ephemeral=True)
            return

        await ctx.respond("Модуль работает.")


def setup(bot):
    bot.add_cog(Example(bot))
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

Поля:

- `id` — технический ID модуля, совпадает с папкой в `installed_modules`.
- `name` — человекочитаемое имя.
- `version` — версия модуля.
- `entrypoint` — Python-файл без `.py`, обычно `cog`.
- `description` — описание.
- `author` — автор.
- `min_core_version` — минимальная версия ядра.
- `required_services` — список сервисов, которые нужны модулю.

Версию нужно повышать при каждом изменении, которое должен получить пользователь через `manage_modules.py update`.

Если версия в источнике не выше установленной, update пропустит модуль.

## Конфиг модуля

Обычные настройки модуля хранятся в:

```text
config/modules/<module_id>.json
```

Чтобы установщик создал файл автоматически, добавьте в репозиторий:

```text
<module_id>.example.json
```

Пример:

```json
{
  "123456789012345678": {
    "channel_id": 0,
    "enabled": true
  }
}
```

Чтение из модуля:

```python
module_config = self.get_module_config(ctx.guild.id) or {}
channel_id = module_config.get("channel_id")
```

## Секреты модуля

Секреты хранятся в:

```text
config/secrets/<module_id>.json
```

Чтобы установщик создал файл автоматически, добавьте в репозиторий:

```text
<module_id>.secrets.example.json
```

Пример:

```json
{
  "api_key": ""
}
```

Чтение из модуля:

```python
api_key = self.get_secret("api_key")
```

Не храните реальные секреты в Git.

## Ресурсы

Если модулю нужны изображения или другие ассеты, положите их в:

```text
resources/
```

Получение пути:

```python
image_path = self.get_resource_path("image.png")
```

После установки ресурсы будут лежать в:

```text
installed_modules/<module_id>/resources/
```

## Зависимости

Все зависимости модуля должны быть в его собственном `requirements.txt`.

Пример:

```txt
py-cord>=2.6.0
r4bot-sdk @ git+https://github.com/Rarmash/R4Bot-SDK.git@master
requests>=2.32.0
```

Ядро не хранит зависимости внешних модулей в корневом `requirements.txt`.

При `install` зависимости ставятся автоматически.

При `update` зависимости ставятся только если версия модуля в источнике выше установленной версии.

## Hooks

Hooks позволяют модулям расширять друг друга без прямой зависимости.

Схема:

- модуль-потребитель задаёт имя hook-канала и формат данных;
- модуль-поставщик регистрирует provider в этот hook-канал;
- ядро не знает о конкретных типах расширений.

Важно:

- отсутствие модуля-потребителя не должно ломать модуль-поставщик;
- отсутствие provider-ов не должно ломать модуль-потребитель;
- provider может возвращать `dict`, `list` или `None`, если формат hook-канала это допускает.

### Пример поставщика расширения

Модуль `reputation` отдаёт дополнительное поле для карточки участника.

`cog.py`:

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


def setup(bot):
    bot.add_cog(Reputation(bot))
```

`service.py`:

```python
class ReputationService:
    HOOK_NAME = "membercard.fields"

    def __init__(self, module):
        self.module = module

    def register_hooks(self):
        self.module.register_hook_provider(self.HOOK_NAME, self.build_field)

    def unregister_hooks(self):
        self.module.unregister_hook_provider(self.HOOK_NAME)

    async def build_field(self, ctx, member, user_data, server_data):
        return {
            "name": "Репутация",
            "value": str(user_data.get("reputation", 0)),
        }
```

### Пример потребителя расширения

Модуль `membercard` собирает поля от других модулей.

`cog.py`:

```python
from r4bot_sdk import R4BotModule

from .service import MemberCardService


class MemberCard(R4BotModule):
    module_id = "membercard"

    def __init__(self, bot):
        super().__init__(bot)
        self.service = MemberCardService(self)

    async def render_card(self, ctx, member, user_data, server_data):
        fields = await self.service.collect_fields(ctx, member, user_data, server_data)
        for field in fields:
            print(field["name"], field["value"])
```

`service.py`:

```python
class MemberCardService:
    HOOK_NAME = "membercard.fields"

    def __init__(self, module):
        self.module = module

    async def collect_fields(self, ctx, member, user_data, server_data):
        results = await self.module.collect_hook_results(
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

## Создание каркаса

```bash
python manage_modules.py create-module example --output C:\path\to\R4Bot-Module-Example
```

Параметры:

- `--name` — человекочитаемое имя.
- `--author` — автор.
- `--description` — описание.
- `--overwrite` — разрешить запись в непустую папку.
- `--no-config-template` — не создавать `<module_id>.example.json`.
- `--no-secrets-template` — не создавать `<module_id>.secrets.example.json`.

## Локальная установка

```bash
python manage_modules.py install path:C:\path\to\R4Bot-Module-Example --enable
```

## Проверка

```bash
python manage_modules.py validate path:C:\path\to\R4Bot-Module-Example
```

или:

```bash
python manage_modules.py validate github:OWNER/REPO@master
```

## Публикация

1. Создайте GitHub-репозиторий.
2. Убедитесь, что `module.json` содержит корректный `id` и `version`.
3. Закоммитьте модуль.
4. Запушьте ветку `master`.
5. Установите модуль:

```bash
python manage_modules.py install github:OWNER/REPO@master --enable
```

## Правила версий

- Начальная версия модуля: `1.0.0`.
- Любое изменение, которое должен получить пользователь через `update`, требует повышения `version`.
- `update` не переустанавливает модуль с такой же или более старой версией.
- Для маленьких фиксов используйте patch-версию: `1.0.1`.
- Для новых возможностей используйте minor-версию: `1.1.0`.
- Для несовместимых изменений используйте major-версию: `2.0.0`.

## Практические рекомендации

- Не импортируйте внутренние файлы ядра.
- Не превращайте `service.py` в свалку всей логики.
- Храните интеграции и hook wiring в `service.py`.
- Храните команды и Discord listeners в `cog.py`.
- Храните обычные настройки и секреты в разных файлах.
- Не коммитьте реальные секреты.
- Поднимайте `version` перед публикацией изменений.
- Проверяйте модуль через `validate` перед установкой или пушем.
