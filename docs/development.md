# Руководство по запуску

## PostgreSQL, Redis и почта

1. Установите и запустите [Docker Desktop](https://docs.docker.com/desktop/).
2. Скопируйте `.env.example` в `.env` и задайте `POSTGRES_PASSWORD`, `DB_PASSWORD`, `DB_MIGRATION_PASSWORD`, `REDIS_PASSWORD` и `AUTH_SECRET` — не короче 32 символов: `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Запуск: `docker compose up -d --wait`. Письма, которые отправляет приложение, видны на http://localhost:8025.
4. В папке `backend` примените миграции: `uv run --locked alembic upgrade head`.
5. Контент: `uv run --locked python -m app.alphabet.sync`.

## Бэкенд

1. Установите [uv](https://docs.astral.sh/uv/getting-started/installation/), в папке `backend` `uv sync --locked`. В PyCharm выберите интерпретатор `backend/.venv` и укажите `backend` рабочей папкой конфигурации запуска.
2. Запуск API: `uv run --locked uvicorn app.main:create_app --factory --loop asyncio:SelectorEventLoop`.
3. Откройте [Swagger UI](http://127.0.0.1:8000/docs).

## Фронтенд

1. Установите [Node.js 24](https://nodejs.org/) и откройте терминал в папке `frontend`.
2. Установите зависимости: `npm ci`.
3. Запуск: `npm run dev` и откройте http://localhost:5173.

## Pre-commit

- Установите хуки один раз, в папке `backend`: `uv run --locked pre-commit install`.
- При `git commit` хуки запускают Ruff и Biome, проверяют файлы и обновляют `docs/api/openapi.json`.
- Проверить весь репозиторий вручную: `uv run --locked pre-commit run --all-files`.

## Отчёт [Allure](https://allurereport.org/) (нужен Node.js)

- Прогон, в папке `backend`: `uv run --locked pytest --alluredir=allure-results --clean-alluredir`.
- Собрать отчёт: `npx allure@3.20.1 generate allure-results`.
- Открыть отчёт: `start allure-report/index.html`.
- Отчёт по ветке `main` публикуется на [GitHub Pages](https://nsat1.github.io/early-mind/) после каждого успешного прогона CI.
