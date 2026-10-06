# early-mind

## Локальный запуск

1. Установите [uv](https://docs.astral.sh/uv/getting-started/installation/) и откройте терминал в корне проекта.
2. Запустите API: `uv run --locked uvicorn app.main:create_app --factory --loop asyncio:SelectorEventLoop`.
3. Откройте [Swagger UI](http://127.0.0.1:8000/docs) или [проверку работоспособности](http://127.0.0.1:8000/health).

## Локальная PostgreSQL

1. Установите и запустите [Docker Desktop](https://docs.docker.com/desktop/).
2. Скопируйте `.env.example` в `.env` и задайте случайный `POSTGRES_PASSWORD`.
3. Запустите БД: `docker compose up -d --wait db`.
