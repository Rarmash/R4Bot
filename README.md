# R4Bot ![Version](https://img.shields.io/github/v/release/Rarmash/R4Bot?label=Latest)

R4Bot — это модульное ядро Discord-бота. Этот репозиторий отвечает за runtime, загрузку модулей, общие сервисы, конфиги, секреты и встроенный административный слой. Основной пользовательский функционал подключается как внешние GitHub-модули.

## Что входит в R4Bot

### Встроенные модули ядра
- `events`
- `service`

### Поддерживаемые внешние модули
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
- `steam`
- `mod`
- `profile`
- `tts`
- `tickets`

## Как устроен runtime

Модули получают доступ к общим сервисам через:

```python
bot.r4_services
```

Сейчас там доступны:
- `config`
- `firebase`
- `module_config`
- `resources`
- `module_state`
- `profile_extensions`
- `secrets`

За счёт этого внешние модули могут жить в отдельных репозиториях и не импортировать код ядра напрямую.

## Конфигурация

### `servers.json`

`servers.json` хранит:
- список встроенных модулей ядра
- базовые настройки серверов

Пример:

```json
{
  "cogs": [
    "events",
    "service"
  ],
  "123456789012345678": {
    "accent_color": "0x209af8",
    "admin_id": 0,
    "admin_role_id": 0,
    "mod_role_id": 0,
    "insider_id": 0
  }
}
```

Если сервер ещё не инициализирован, владелец может выполнить:

```text
/service initserver
```

### `config/modules/*.json`

Эти файлы хранят обычные настройки модулей:
- каналы
- категории
- роли
- лимиты
- флаги

Примеры:
- `config/modules/logger.json`
- `config/modules/messages.json`
- `config/modules/starboard.json`
- `config/modules/tts.json`
- `config/modules/tickets.json`

### `config/secrets/*.json`

Эти файлы хранят секреты модулей:
- API-ключи
- приватные токены интеграций

Примеры:
- `config/secrets/xbox.json`
- `config/secrets/fortnite.json`
- `config/secrets/steam.json`

Реальные `config/secrets/*.json` игнорируются git. В репозитории должны лежать только шаблоны `*.example.json`.

### `.env`

`.env` используется только для базовых переменных самого ядра.

Минимальный пример:

```env
TOKEN=
APPLICATIONID=
DEBUGMODE=OFF
```

Шаблон:
- `.env_template`

## Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/Rarmash/R4Bot.git
cd R4Bot
```

2. Установите зависимости ядра:

```bash
pip install -r requirements.txt
```

3. Установите `ffmpeg`.

Он нужен внешнему TTS-модулю.

4. Подготовьте файлы:
- `.env`
- `firebaseConfig.json`
- `servers.json`

`firebaseConfig.json` можно получить в Firebase Console:
`Project Settings -> Service accounts -> Firebase Admin SDK -> Python`

5. При необходимости заполните:
- `config/modules/*.json`
- `config/secrets/*.json`

6. Запустите бота:

```bash
python main.py
```

## Управление модулями через CLI

Используется:
- `manage_modules.py`

Поддерживаемые источники:
- `github:OWNER/REPO@master`
- `path:локальная_папка_модуля`

Зависимости модулей не хранятся в корневом `requirements.txt`.
Если у модуля есть свой `requirements.txt`, они устанавливаются автоматически при:
- `install`
- `update`

### Установка модуля

```bash
python manage_modules.py install github:Rarmash/R4Bot-Module-Logger@master --enable
```

### Обновление одного модуля

```bash
python manage_modules.py update logger
```

### Обновление всех модулей

```bash
python manage_modules.py update --all
```

### Включение модуля

```bash
python manage_modules.py enable logger
```

### Выключение модуля

```bash
python manage_modules.py disable logger
```

### Удаление модуля

```bash
python manage_modules.py remove logger
```

### Важное замечание

Установка и обновление модулей меняют и файлы, и Python-зависимости.
Безопаснее выполнять эти команды на остановленном боте, а после завершения делать рестарт.

## Управление из Discord

Встроенные административные команды доступны через `/service`:
- `/service initserver`
- `/service secrets`
- `/service shutdown`
- `/service modules`
- `/service moduleinfo`
- `/service enablemodule`
- `/service disablemodule`
- `/service reloadmodule`

## Ресурсы модулей

Если модуль поставляет изображения или другие ассеты, они лежат внутри самого репозитория модуля в папке `resources/`.

Из кода они доступны через:

```python
bot.r4_services.resources.get_resource_path(module_id, ...)
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

Compose-файл:
- `docker-compose.yml`

## Структура проекта

Этот репозиторий — ядро бота. Он отвечает за:
- запуск runtime
- встроенные административные модули
- общие сервисы
- работу с конфигами и секретами
- установку и загрузку внешних модулей

Функциональные модули живут в отдельных GitHub-репозиториях и устанавливаются в `installed_modules/`.
