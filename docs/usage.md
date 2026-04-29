# Использование R4Bot

Этот документ описывает установку, запуск, конфигурацию и администрирование R4Bot.

## Требования

- Python 3.11 или новее.
- Git.
- Discord Bot Token.
- Discord Application ID.
- Firebase Admin SDK config, если установленные модули используют Firebase.
- `ffmpeg`, если вы используете голосовые или TTS-модули.

## Установка ядра

```bash
git clone https://github.com/Rarmash/R4Bot.git
cd R4Bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

На Linux/macOS активация окружения обычно выглядит так:

```bash
source .venv/bin/activate
```

## Базовые файлы

### `.env`

Создайте `.env` по шаблону `.env_template`:

```env
TOKEN=
APPLICATIONID=
DEBUGMODE=OFF
```

Поля:

- `TOKEN` — токен Discord-бота.
- `APPLICATIONID` — ID приложения Discord.
- `DEBUGMODE` — `ON` или `OFF`.

### `servers.json`

`servers.json` хранит настройки конкретных Discord-серверов. Встроенные модули ядра из `core/builtin_modules` загружаются автоматически, поэтому перечислять их в конфиге не нужно.

После запуска и приглашения бота на сервер выполните:

```text
/service initserver
```

Команда создаст `servers.json`, если файла ещё нет, и добавит блок настроек для текущего сервера:

```json
{
  "123456789012345678": {
    "accent_color": "0x209af8",
    "admin_id": 123456789012345678,
    "mod_role_id": 0,
    "insider_id": 0,
    "admin_role_id": 0
  }
}
```

### `firebaseConfig.json`

Если модулям нужен Firebase, положите в корень проекта `firebaseConfig.json`.

Файл можно получить в Firebase Console:

```text
Project Settings -> Service accounts -> Firebase Admin SDK -> Python
```

Если Firebase не нужен, файл можно не создавать.

## Запуск

```bash
python main.py
```

При старте бот:

- создаёт runtime services;
- подключает Firebase, если есть `firebaseConfig.json`;
- загружает built-in модули из `core/builtin_modules`;
- загружает включённые внешние модули из `data/module_state.json`;
- синхронизирует slash-команды.

## Управление модулями через CLI

CLI запускается через:

```bash
python manage_modules.py <command>
```

Поддерживаемые источники:

- `github:OWNER/REPO@master`
- `github:OWNER/REPO@tag`
- `path:C:\path\to\module`

### Установка

```bash
python manage_modules.py install github:Rarmash/R4Bot-Module-Logger@master --enable
```

Что делает установка:

- скачивает или копирует модуль;
- проверяет `module.json`;
- кладёт модуль в `installed_modules/<module_id>`;
- устанавливает зависимости из `requirements.txt` модуля;
- создаёт `config/modules/<module_id>.json`, если в модуле есть example-конфиг;
- создаёт `config/secrets/<module_id>.json`, если в модуле есть example-секреты;
- записывает состояние в `data/module_state.json`;
- включает модуль, если указан `--enable`.

### Обновление одного модуля

```bash
python manage_modules.py update logger
```

Обновление выполняется только если `version` в `module.json` источника выше установленной версии.

Если версия такая же или ниже, CLI покажет, что модуль уже актуален.

### Обновление всех модулей

```bash
python manage_modules.py update --all
```

CLI отдельно покажет:

- обновлённые модули;
- модули, которые уже актуальны;
- ошибки обновления.

### Включение и отключение

```bash
python manage_modules.py enable logger
python manage_modules.py disable logger
```

Эти команды меняют состояние в `data/module_state.json`.

Если бот уже запущен, после CLI-команды обычно нужен рестарт, чтобы runtime точно соответствовал состоянию на диске.

### Удаление

```bash
python manage_modules.py remove logger
```

Команда удаляет папку модуля из `installed_modules` и запись из `data/module_state.json`.

Конфиги и секреты модуля не удаляются автоматически.

### Список установленных модулей

```bash
python manage_modules.py list-installed
```

### Проверка модуля

```bash
python manage_modules.py validate path:C:\path\to\R4Bot-Module-Example
python manage_modules.py validate github:OWNER/REPO@master
```

### Создание каркаса модуля

```bash
python manage_modules.py create-module example --output C:\path\to\R4Bot-Module-Example
```

Подробности: [Разработка модулей](module-development.md).

## Управление из Discord

Built-in команды находятся в группе `/service`.

Основные команды:

- `/service initserver` — создать минимальный конфиг для текущего сервера.
- `/service secrets` — отправить владельцу/админу конфиги и секреты в личные сообщения.
- `/service shutdown` — остановить процесс бота.
- `/service modules` — показать установленные модули.
- `/service moduleinfo` — показать информацию о конкретном модуле.
- `/service doctor` — проверить состояние ядра, модулей и их зависимостей.
- `/service moduleerrors` — показать последние ошибки загрузки модулей.
- `/service enablemodule` — включить установленный модуль в runtime.
- `/service disablemodule` — выключить установленный модуль в runtime.
- `/service reloadmodule` — перезагрузить включённый модуль.

Команды управления модулями в Discord работают с уже установленными модулями. Установка, обновление и удаление выполняются через CLI.

## Конфиги модулей

Обычные настройки модулей лежат здесь:

```text
config/modules/<module_id>.json
```

Примеры обычных настроек:

- ID каналов;
- ID ролей;
- лимиты;
- флаги включения отдельных возможностей;
- настройки поведения модуля.

При установке модуль может создать этот файл автоматически из шаблона:

```text
<module_id>.example.json
```

## Секреты модулей

Секреты модулей лежат здесь:

```text
config/secrets/<module_id>.json
```

Примеры секретов:

- API-ключи;
- токены интеграций;
- приватные параметры внешних сервисов.

При установке модуль может создать этот файл автоматически из шаблона:

```text
<module_id>.secrets.example.json
```

Реальные секреты не должны попадать в Git.

## Ресурсы модулей

Модуль может поставлять ассеты в собственной папке:

```text
resources/
```

После установки они доступны из:

```text
installed_modules/<module_id>/resources/
```

Модули получают путь к ресурсам через runtime services или `R4BotModule.get_resource_path(...)`.

## Обновление ядра

Ядро не обновляет себя автоматически во время работы.

Рекомендуемый процесс:

```bash
git pull
pip install -r requirements.txt
python manage_modules.py update --all
python main.py
```

Если обновились зависимости модулей, выполняйте `update --all` при остановленном боте.

## Docker

Базовый запуск:

```bash
docker compose up --build -d
```

Контейнер использует те же файлы:

- `.env`;
- `firebaseConfig.json`;
- `servers.json`;
- `config/modules/*.json`;
- `config/secrets/*.json`;
- `data/module_state.json`.

## Частые проблемы

### Slash-команда пишет “Приложение не отвечает”

Частые причины:

- сервер не инициализирован через `/service initserver`;
- модуль не загрузился при старте;
- в консоли есть ошибка загрузки модуля;
- команда выполняет долгую операцию без `defer`.

### Команда модуля не появилась

Проверьте:

- модуль установлен;
- модуль включён;
- бот был перезапущен или модуль был загружен через `/service enablemodule`;
- slash-команды синхронизировались после загрузки.

### `update` не подтягивает изменения

Поднимите `version` в `module.json` модуля. Обновление выполняется только при более новой версии источника.

### Модуль не загружается из-за зависимости

Проверьте `required_dependencies` в `module.json` модуля. Все обязательные зависимости должны быть установлены и включены.

Для диагностики используйте:

```text
/service doctor
/service moduleerrors
```
