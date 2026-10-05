# early-mind

## Локальный запуск

1. Установите [uv](https://docs.astral.sh/uv/getting-started/installation/) и откройте терминал в корне проекта.
2. Запустите API: `uv run --locked uvicorn app.main:create_app --factory`.
3. Откройте [Swagger UI](http://127.0.0.1:8000/docs) или [проверку работоспособности](http://127.0.0.1:8000/health).

## Локальная PostgreSQL

1. Установите и запустите [Docker Desktop](https://docs.docker.com/desktop/).
2. Скопируйте `.env.example` в `.env` и задайте случайный `POSTGRES_PASSWORD`.
3. Запустите БД: `docker compose up -d --wait db`.

## Настройки приложения

Параметры `EARLY_MIND_DB_*` задаются в `.env` в корне проекта; переменные окружения имеют приоритет над файлом.
`EARLY_MIND_DB_PASSWORD` обязателен при получении настроек, без значения по умолчанию; `POSTGRES_PASSWORD` используется только для инициализации PostgreSQL в Compose.
`EARLY_MIND_DB_USER=early_mind_app` — отдельный пользователь приложения. Создание роли и её прав, а также подключение API к БД относятся к следующей итерации.
Сейчас API запускается независимо от этих настроек. Настройки читаются при первом вызове `get_settings()` и кэшируются на процесс; после изменения окружения перезапустите использующий их процесс.
