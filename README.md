# R4Bot ![Version](https://img.shields.io/github/v/release/Rarmash/R4Bot?label=Latest)

R4Bot — Discord-бот для модерации серверов и дополнительных сервисных задач. Бот использует slash-команды, работает с несколькими серверами через `servers.json`, поддерживает Firebase и включает игровые и служебные модули.

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
3. Установите [FFmpeg](https://ffmpeg.org/). Он нужен для TTS и голосового воспроизведения.
4. Настройте бота через `servers.json` и `.env`:
   - шаблон переменных: [.env_template](https://github.com/Rarmash/R4Bot/blob/master/.env_template)
   - `firebaseConfig.json` нужно получить в [Firebase Console](https://console.firebase.google.com) через `Project Settings` -> `Service accounts` -> `Firebase Admin SDK` -> `Python`
5. Запустите бота:
   ```bash
   python main.py
   ```

## Docker
Базовый запуск:

```bash
docker compose up --build -d
```

Контейнер использует:
- `.env`
- `firebaseConfig.json`
- `servers.json`

### Docker через Sing-box
Если бот запускается на сервере, где Discord недоступен напрямую (например, из-за блокировок), можно пустить весь трафик контейнера через VPN с помощью sing-box.

1. Создайте локальный override:
   ```bash
   cp docker-compose.override.example.yml docker-compose.override.yml
   ```
2. Создайте локальный конфиг XRay:
   ```bash
   cp sing-box.json.example sing-box.json
   ```
3. Заполните `sing-box.json` своими данными.

   Укажите свои параметры:

   - `server` — IP вашей XRay-ноды
   - `server_port` — порт inbound (например, 2040)
   - `uuid` — ID пользователя
   - `flow` — обязательно xtls-rprx-vision, если используется Reality
   - `server_name` — SNI (домен из Reality конфигурации)
   - `public_key` — Reality public key
   - `short_id` — Reality short ID
4. Запустите контейнеры:
   ```bash
   docker compose up --build -d
   ```

Файлы `docker-compose.override.yml` и `sing-box.json` предназначены для локального использования на сервере и не должны коммититься в репозиторий. Используйте IP (`172.x.x.x` / реальный IP), а не `host.docker.internal`.

## О `servers.json`
Бот поддерживает работу на нескольких серверах. Для этого нужно добавить отдельный блок настроек для каждого сервера.

```json
{
    "cogs": [
        "events"
    ],
    "server_id": {
        "accent_color": "0xFFFFFF",
        "log_channel": 0,
        "admin_channel": 0,
        "ticket_category": 0,
        "suggestions_channel": 0,
        "media_channel": 0,
        "media_pins": 1,
        "admin_id": 0,
        "mod_role_id": 0,
        "insider_id": 0,
        "admin_role_id": 0,
        "trash_channels": [],
        "bannedChannels": [],
        "bannedUsers": [],
        "bannedCategories": [],
        "bannedTTSChannels": [],
        "banned_TTS_role": 0
    }
}
```

Описание полей:
- `cogs` — список подключаемых модулей
- `accent_color` — акцентный цвет сообщений бота в формате HEX
- `log_channel` — канал для логирования удалённых и изменённых сообщений
- `admin_channel` — административный канал
- `ticket_category` — категория для тикетов
- `suggestions_channel` — канал для предложений
- `media_channel` — канал для медиа-контента
- `media_pins` — количество реакций, нужное для закрепления сообщения
- `admin_id` — Discord ID администратора бота
- `mod_role_id` — ID роли модератора
- `insider_id` — ID роли инсайдера
- `admin_role_id` — ID роли администрации
- `trash_channels` — каналы, где не считается статистика сообщений
- `bannedChannels` — каналы, исключённые из логирования
- `bannedUsers` — пользователи, исключённые из логирования
- `bannedCategories` — категории, исключённые из логирования
- `bannedTTSChannels` — каналы, где отключён TTS
- `banned_TTS_role` — роль, которой запрещено использовать TTS

## О `.env`
```env
TOKEN=           # Токен бота Discord
APPLICATIONID=   # Application ID приложения из Discord Developer Portal
FORTNITEAPI=     # Ключ API для Fortnite
XBOXAPI=         # Ключ API для Xbox
STEAMAPI=        # Ключ официального Steam Web API
DEBUGMODE=OFF    # Значение debug-режима
```
