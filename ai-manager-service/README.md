# AI-Manager Service

Сервис ИИ-администратора для клиник на FastAPI и SQLite. Генерирует промпты для GoHighLevel, ведёт диалог с клиентами через ключ OpenRouter и собирает лиды (имя, телефон, жалоба).

## Стек

- Python 3.10+
- FastAPI
- SQLAlchemy 2.0
- SQLite
- Pydantic v2
- Jinja2
- httpx
- python-dotenv

## Установка

Откройте PowerShell и выполните команды из корневой папки проекта:

```bash
cd ai-manager-service
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Если PowerShell запрещает активацию окружения, выполните эту команду только для
текущего окна терминала и повторите активацию:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Настройка

Скопируйте `.env.example` в `.env` и укажите ключ OpenRouter:

```bash
Copy-Item .env.example .env       # PowerShell
# cp .env.example .env            # Linux/macOS
```

Отредактируйте `.env`:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1/chat/completions
# Необязательно: путь к CA-bundle, если в сети используется собственный сертификат
OPENROUTER_CA_BUNDLE=
DATABASE_URL=sqlite:///./ai_manager.db
```

На Windows приложение использует системное хранилище сертификатов. Если в вашей сети
есть корпоративный прокси с собственным CA, установите его корневой сертификат в Windows
или укажите путь к CA-bundle в `OPENROUTER_CA_BUNDLE`.

## Первый запуск демо

Первый запуск выполняется из папки `ai-manager-service` в активированном
виртуальном окружении:

```bash
python run.py
```

После старта терминал выведет точный адрес:

```text
Демо-версия: http://localhost:8000
```

Откройте в браузере именно [http://localhost:8000](http://localhost:8000).
Отдельный frontend-сервер не нужен: HTML-интерфейс обслуживает FastAPI.

При первом старте автоматически создаются SQLite-база `ai_manager.db`, тестовый
бизнес «Дента-Плюс» и его демо-данные. В интерфейсе нажмите «Сгенерировать
промпт», затем отправьте сообщение в чат.

Для ответа чат должен подключиться к OpenRouter, поэтому в `.env` должен быть
действующий `OPENROUTER_API_KEY`. Без ключа страница откроется, но ответы модели
не будут работать.

## Вторичный запуск демо

После первой установки каждый следующий запуск выглядит так:

```powershell
cd D:\_Work\AI-manager\ai-manager-service
.\.venv\Scripts\Activate.ps1
python run.py
```

После этого снова откройте [http://localhost:8000](http://localhost:8000).
База и бизнес сохраняются между запусками. При изменении шаблона обязательно
нажмите «Сгенерировать промпт» заново, потому что в чат передаётся последний
сохранённый вариант промпта.

Для остановки сервиса нажмите `Ctrl+C` в терминале. Если порт 8000 занят,
остановите уже работающий экземпляр, а не запускайте второй поверх него.

Полезные адреса:

- Демо: [http://localhost:8000](http://localhost:8000)
- Документация API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Список бизнесов: [http://localhost:8000/api/businesses](http://localhost:8000/api/businesses)

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/businesses` | Список бизнесов |
| POST | `/api/businesses` | Создание бизнеса |
| POST | `/api/businesses/{id}/generate-prompt` | Генерация промпта из шаблона |
| GET | `/api/businesses/{id}/prompt` | Последний промпт бизнеса |
| POST | `/api/chat/demo` | Демо-чат с ботом |
| GET | `/api/businesses/{id}/patients` | Список собранных лидов |

## Где находятся инструкции ИИ-менеджера

Основной шаблон инструкций находится в
`backend/templates/prompt_template.md`. После изменения файла перезапустите
сервис и нажмите «Сгенерировать промпт» в демо. Данные демо-клиники, включая
адрес, цены и врачей, находятся в `backend/app/main.py`.

## Telegram

Telegram-режим запускается отдельным процессом после запуска основного API.
Подробная настройка описана в разделе [Запуск Telegram-бота](#запуск-telegram-бота).

### Запуск Telegram-бота

1. В Telegram откройте `@BotFather`, выполните `/newbot` и сохраните выданный токен.
2. Напишите своему боту любое сообщение и узнайте свой Telegram ID через
	`@userinfobot` или аналогичный проверенный сервис.
3. Добавьте в `.env`:

```env
TELEGRAM_BOT_TOKEN=токен-от-BotFather
TELEGRAM_ADMIN_CHAT_ID=ваш-telegram-id
```

4. В отдельном окне PowerShell запустите API, если он ещё не запущен:

```powershell
cd D:\_Work\AI-manager\ai-manager-service
.\.venv\Scripts\Activate.ps1
python run.py
```

5. Во втором окне запустите Telegram-бота:

```powershell
cd D:\_Work\AI-manager\ai-manager-service
.\.venv\Scripts\Activate.ps1
python telegram_bot.py
```

Клиент пишет боту в Telegram, бот отвечает через ту же модель и сохраняет
сессию, историю и лид в `ai_manager.db`. При активном боте администратор получает
уведомление о новом диалоге. Кнопка `Взять диалог` переводит сессию в режим
`HUMAN_TAKEN`; после этого модель клиенту не отвечает. Администратор может
отправлять ответы через кнопку/команды, а кнопка `Вернуть боту` снова включает
автоматические ответы.

В текущей версии ответ оператор отправляет из своего Telegram-чата с ботом:

```text
/reply CHAT_ID текст ответа
```

`CHAT_ID` указан в уведомлении о сессии, например `telegram:123456789`;
для команды нужно использовать только числовую часть `123456789`. Это не
создаёт общий групповой чат с клиентом, но для пользователя выглядит как один
диалог с ботом, а оператор получает контроль над той же перепиской. Все
сообщения, режим сессии и лид остаются в базе.

Telegram-бот и API должны работать одновременно в двух окнах терминала. Токен
нельзя публиковать или помещать в Git.

## Структура

```
ai-manager-service/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── agent_engine.py
│   │   ├── prompt_generator.py
│   │   ├── ghl_converter.py
│   │   └── routers/
│   │       ├── businesses.py
│   │       ├── agents.py
│   │       └── chat.py
│   ├── templates/
│   │   └── prompt_template.md
│   └── static/
│       ├── demo.html
│       └── style.css
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── run.py
└── telegram_bot.py
