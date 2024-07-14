# R4Bot ![Version](https://img.shields.io/badge/Latest-1.2/master-blue.svg)
Discord-бот, созданный для облегчения модерации серверов, и не только. Используются слэш-команды.

## 🛠️ Установка
1. Клонируйте репозиторий:
    ```BASH
    git clone https://github.com/Rarmash/R4bot.git
    ```
2. Смените директорию:
    ```BASH
    cd R4bot
    ```
3. Установите зависимости:
    ```BASH
    pip install -r requirements.txt
    ```
4. Загрузите и установите [FFMPEG](https://ffmpeg.org/) (как вариант - в корень проекта).

5. Запустите файл Python:
    ```BASH
    python main.py
    ```

6. Настройте бота через файлы servers.json и .env (шаблон - [.env_template](https://github.com/Rarmash/R4Bot/blob/master/.env_template)).

7. Сгенерируйте ключ доступа к своему приложению [Firebase](https://console.firebase.google.com) (в панели управления: `Project Settings` -> `Service accounts` -> `Firebase Admin SDK` -> `Python`) и поместите полученный файл в корень проекта.

## 🛠️ О servers.json:
Бот поддерживает нахождение на нескольких серверах. Просто продублируйте блок с настройками сервера и заполните его.
```JSON
{
    "gears": [                            // список подключаемых модулей
        "events"
    ],
    "server_id": {                        // ID сервера
        "accent_color": "0xFFFFFF",       // акцентный цвет для сообщений бота (в виде HEX-кода)
        "log_channel": 0,                 // ID канала для логирования удалённых/отредактированных сообщений
        "admin_channel": 0,               // ID канала Администрации
        "ticket_category": 0,             // ID категории для тикетов
        "suggestions_channel": 0,         // ID канала для предложений
        "media_channel": 0,               // ID канала для медиаконтента
        "media_pins": 1,                  // количество реакций, необходимых для закрепления сообщения
        "admin_id": 0,                    // ID администратора бота
        "elder_mod_role_id": 0,           // ID роли старшего модератора
        "junior_mod_role_id": 0,          // ID роли младшего модератора
        "insider_id": 0,                  // ID роли инсайдера
        "admin_role_id": 0,               // ID роли Администрации
        "trash_channels": [],             // ID каналов, в которых не будет подсчитываться количество отправленных сообщений
        "bannedChannels": [],             // ID каналов, в которых не будут учитываться сообщения для логирования
        "bannedUsers": [],                // ID пользователей, чьи сообщения не будут учитываться для логирования
        "bannedCategories": [],           // ID категорий, в каналах которых не будут учитываться сообщения для логирования
        "bannedTTSChannels": []           // ID каналов, в которых не будет использоваться Text-to-Speech
    }
}
```

## 🛠️ О .env:
```ENV
TOKEN=           // Токен бота Discord
APPLICATIONID=   // Application ID приложения бота с Discord Developer Portal
FORTNITEAPI=     // Ключ API для получения данных с https://fortnite-api.com/
XBOXAPI=         // Ключ API для получения данных с https://xbl.io/
DEBUGMODE=OFF    // Значение DEBUG-режима
```
