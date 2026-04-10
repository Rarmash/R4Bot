# R4Bot ![Version](https://img.shields.io/badge/Latest-1.4/master-blue.svg)

Discord-бот для модерации серверов и дополнительных сервисных задач. Бот использует slash-команды, работает с несколькими серверами через `servers.json`, поддерживает Firebase и включает игровые и служебные модули.

## Установка
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/Rarmash/R4Bot.git
   ```
2. Перейдите в директорию проекта:
   ```bash
   cd R4Bot
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Установите [FFmpeg](https://ffmpeg.org/). Он нужен для TTS и голосового воспроизведения.
5. Настройте бота через файлы `servers.json` и `.env` (шаблон — [.env_template](https://github.com/Rarmash/R4Bot/blob/master/.env_template)).
6. Сгенерируйте ключ доступа к своему приложению [Firebase](https://console.firebase.google.com) (`Project Settings` -> `Service accounts` -> `Firebase Admin SDK` -> `Python`) и поместите полученный файл в корень проекта как `firebaseConfig.json`.
7. Запустите бота:
   ```bash
   python main.py
   ```

## Docker
Для запуска через Docker:

```bash
docker compose up --build -d
```

Контейнер использует:
- `.env`
- `firebaseConfig.json`
- `servers.json`

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
