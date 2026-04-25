# R4Bot ![Version](https://img.shields.io/github/v/release/Rarmash/R4Bot?label=Latest)

R4Bot — Discord-бот с модульной архитектурой. Основной репозиторий теперь выступает как ядро: он поднимает runtime, конфиги, сервисы, загрузчик модулей и несколько built-in команд, а почти весь пользовательский функционал вынесен во внешние GitHub-модули.

## Текущее состояние

### Built-in ядро
- `events`
- `service`

### Внешние GitHub-модули
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

## Архитектура

Основной рантайм даёт модулям доступ к сервисам через:

```python
bot.r4_services
```

Сейчас там используются, в том числе:
- `config`
- `firebase`
- `module_config`
- `resources`
- `module_state`
- `profile_extensions`
- `secrets`

Это позволяет внешним модулям не импортировать код ядра напрямую и жить как отдельные репозитории.

## Структура конфигов

### `servers.json`

Хранит:
- список built-in модулей ядра
- core-настройки серверов
- только общие поля, которые действительно нужны ядру и нескольким модулям

Пример:

```json
{
  "cogs": [
    "events",
    "service"
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

Если сервер ещё не инициализирован, владелец может выполнить `/service initserver`.

Что больше не должно жить в `servers.json`:
- лог-каналы
- suggestion-каналы
- ticket-категории
- starboard/media-настройки
- TTS-ограничения
- прочие настройки отдельных модулей

Для этого теперь используются `config/modules/*.json`.

### `config/modules/*.json`

Хранит обычные настройки модулей:
- каналы
- категории
- роли
- лимиты
- флаги

Например сейчас используются:
- `config/modules/logger.json`
- `config/modules/messages.json`
- `config/modules/starboard.json`
- `config/modules/tts.json`
- `config/modules/tickets.json`

Именно сюда теперь вынесены поля, которые раньше исторически лежали в `servers.json`.

### `config/secrets/*.json`

Хранит секреты модулей:
- API-ключи
- приватные токены интеграций

Например сейчас используются:
- `config/secrets/xbox.json`
- `config/secrets/fortnite.json`
- `config/secrets/steam.json`

Реальные `config/secrets/*.json` игнорируются git, а шаблоны коммитятся как `*.example.json`.

## `.env`

`.env` теперь нужен только для базовых переменных самого ядра.

Актуальный минимальный набор:

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

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Установите `ffmpeg`.

Он нужен внешнему TTS-модулю.

4. Подготовьте файлы:
- `.env`
- `firebaseConfig.json`
- `servers.json`

`firebaseConfig.json` берётся из Firebase Console:
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

Поддерживаются источники:
- `github:OWNER/REPO@master`
- `path:локальный_путь`

### Установка

```bash
python manage_modules.py install github:Rarmash/R4Bot-Module-Logger@master --enable
```

### Обновление

```bash
python manage_modules.py update logger
```

### Обновление всех модулей

```bash
python manage_modules.py update --all
```

### Включение

```bash
python manage_modules.py enable logger
```

### Выключение

```bash
python manage_modules.py disable logger
```

### Удаление

```bash
python manage_modules.py remove logger
```

## Управление из Discord

Теперь административные built-in команды собраны под `/service`.

### Доступно в ядре
- `/service initserver`
- `/service secrets`
- `/service shutdown`
- `/service modules`
- `/service moduleinfo`
- `/service enablemodule`
- `/service disablemodule`
- `/service reloadmodule`

### Профильный модуль
- `/profile`
- `/server`

## Ресурсы модулей

Если модуль хранит свои изображения или другие файлы, они лежат внутри самого module-repo в папке `resources/`.

Из кода они доступны через:

```python
bot.r4_services.resources.get_resource_path(module_id, ...)
```

## Docker

Базовый запуск:

```bash
docker compose up --build -d
```

Используются:
- `.env`
- `firebaseConfig.json`
- `servers.json`

Файл:
- `docker-compose.yml`

## Направление проекта

R4Bot уже почти полностью работает как ядро + внешние модули:
- built-in часть отвечает за runtime и административную основу
- предметная логика живёт в отдельных GitHub-репозиториях
- модули получают сервисы через `bot.r4_services`
- конфиги и секреты разделены по уровням ответственности

То есть основной репозиторий теперь не монолитный бот, а база для модульной экосистемы.
