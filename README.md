# R4Bot ![Version](https://img.shields.io/github/v/release/Rarmash/R4Bot?label=Latest)

R4Bot — Discord-бот для модерации, профилей, TTS и игровых интеграций. Сейчас проект работает как гибрид: часть функциональности остаётся встроенной в основной репозиторий, а часть уже вынесена во внешние модули, которые ставятся из GitHub.

## Что есть сейчас

- built-in ядро и базовые коги:
  - `mod`
  - `module_manager`
  - `profile`
  - `service`
  - `steam`
  - `tts`
- внешние GitHub-модули:
  - `logger`
  - `suggestions`
  - `starboard`
  - `messages`
  - `rolesback`
  - `leaderboards`
  - `voice`
  - `timeouts`
  - `xbox`
  - `fortnite`

## Структура конфигов

В проекте теперь используются три уровня конфигурации.

### `servers.json`

Хранит только серверный core-конфиг и список встроенных `cogs`.

Пример:

```json
{
  "cogs": [
    "mod",
    "module_manager",
    "profile",
    "service",
    "steam",
    "tts"
  ],
  "server_id": {
    "accent_color": "0x209af8",
    "admin_id": 0,
    "admin_role_id": 0,
    "mod_role_id": 0,
    "insider_id": 0
  }
}
```

Если сервер ещё не настроен, владелец может инициализировать минимальный конфиг командой `/service initserver`.

### `config/modules/*.json`

Хранит обычные настройки отдельных модулей, которые не являются секретами.

Сейчас в проекте уже используются:

- [config/modules/logger.json](c:/Users/Rarmash/PycharmProjects/R4Bot/config/modules/logger.json)
- [config/modules/messages.json](c:/Users/Rarmash/PycharmProjects/R4Bot/config/modules/messages.json)
- [config/modules/starboard.json](c:/Users/Rarmash/PycharmProjects/R4Bot/config/modules/starboard.json)

Шаблоны лежат рядом в виде `*.example.json`.

### `config/secrets/*.json`

Хранит секреты модулей: API-ключи и другие чувствительные данные.

Сейчас в проекте уже используются:

- [config/secrets/xbox.json](c:/Users/Rarmash/PycharmProjects/R4Bot/config/secrets/xbox.json)
- [config/secrets/fortnite.json](c:/Users/Rarmash/PycharmProjects/R4Bot/config/secrets/fortnite.json)

Шаблоны лежат в виде `*.example.json`, а реальные файлы игнорируются git.

## `.env`

`.env` теперь нужен только для базовых переменных самого бота и старых built-in интеграций.

Актуальный набор:

```env
TOKEN=
APPLICATIONID=
STEAMAPI=
DEBUGMODE=OFF
```

Примечание:

- `XBOXAPI` и `FORTNITEAPI` больше не предполагаются в `.env`
- для внешних модулей `xbox` и `fortnite` используются `config/secrets/xbox.json` и `config/secrets/fortnite.json`

Шаблон: [.env_template](c:/Users/Rarmash/PycharmProjects/R4Bot/.env_template)

## Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/Rarmash/R4Bot.git
cd R4Bot
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Установите [FFmpeg](https://ffmpeg.org/).

Он нужен для TTS и голосового воспроизведения.

4. Подготовьте файлы:

- `.env`
- `firebaseConfig.json`
- `servers.json`

`firebaseConfig.json` нужно получить в Firebase Console:
`Project Settings -> Service accounts -> Firebase Admin SDK -> Python`

5. При необходимости заполните модульные конфиги и секреты:

- `config/modules/*.json`
- `config/secrets/*.json`

6. Запустите бота:

```bash
python main.py
```

## Управление модулями через CLI

Для установки и обновления модулей используется:

- [manage_modules.py](c:/Users/Rarmash/PycharmProjects/R4Bot/manage_modules.py)

Поддерживаются источники:

- `github:OWNER/REPO@master`
- `path:локальный_путь`

### Установка модуля

```bash
python manage_modules.py install github:Rarmash/R4Bot-Module-Logger@master --enable
```

### Обновление модуля

```bash
python manage_modules.py update logger
```

### Выключение модуля

```bash
python manage_modules.py disable logger
```

### Включение модуля

```bash
python manage_modules.py enable logger
```

### Удаление модуля

```bash
python manage_modules.py remove logger
```

## Управление модулями из Discord

В built-in входит [module_manager.py](c:/Users/Rarmash/PycharmProjects/R4Bot/cogs/module_manager.py), который даёт slash-команды:

- `/module list`
- `/module info`
- `/module enable`
- `/module disable`
- `/module reload`

Установка и удаление модулей по-прежнему делаются через CLI, а не из Discord.

## Docker

Базовый запуск:

```bash
docker compose up --build -d
```

Контейнер использует:

- `.env`
- `firebaseConfig.json`
- `servers.json`

Файл:

- [docker-compose.yml](c:/Users/Rarmash/PycharmProjects/R4Bot/docker-compose.yml)

### Docker через sing-box

Если Discord недоступен напрямую, можно пустить трафик контейнера через sing-box.

1. Создайте локальный override:

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
```

2. Создайте локальный конфиг sing-box:

```bash
cp sing-box.json.example sing-box.json
```

3. Заполните `sing-box.json` своими параметрами.

4. Запустите контейнеры:

```bash
docker compose up --build -d
```

Файлы `docker-compose.override.yml` и `sing-box.json` предназначены только для локального использования на сервере и не должны коммититься.

## Текущее направление проекта

R4Bot постепенно переводится на модульную архитектуру:

- runtime-сервисы доступны через `bot.r4_services`
- внешние модули ставятся из GitHub
- обычные настройки модулей хранятся в `config/modules`
- секреты модулей хранятся в `config/secrets`

То есть основной репозиторий всё больше становится ядром, а функциональность выносится в отдельные module-repos.
