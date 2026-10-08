# early-mind

## Локальный запуск

1. Установите [uv](https://docs.astral.sh/uv/getting-started/installation/) и откройте терминал в корне проекта.
2. Запустите API: `uv run --locked uvicorn app.main:create_app --factory --loop asyncio:SelectorEventLoop`.
3. Откройте [Swagger UI](http://127.0.0.1:8000/docs) или [проверку работоспособности](http://127.0.0.1:8000/health).

## Локальная PostgreSQL

1. Установите и запустите [Docker Desktop](https://docs.docker.com/desktop/).
2. Скопируйте `.env.example` в `.env` и задайте случайные `POSTGRES_PASSWORD`, `DB_PASSWORD` и `DB_MIGRATION_PASSWORD`.
3. Запустите БД: `docker compose up -d --wait db`.
4. Примените миграции: `uv run --locked alembic upgrade head`.

Роли и их пароли создаются только при первом запуске на пустом томе. Чтобы применить изменения в `scripts/db`, пересоздайте БД (все данные будут удалены): `docker compose down -v`.

## Тесты

- Все тесты: `uv run --locked pytest`. Интеграционные тесты создают отдельную БД `early_mind_test` в запущенной PostgreSQL и удаляют её после прогона; без БД они пропускаются.
- Только быстрые тесты без БД: `uv run --locked pytest -m "not integration"`.
- Отчёт [Allure](https://allurereport.org/) (нужен Node.js): `uv run --locked pytest --alluredir=allure-results --clean-alluredir`, затем `npx allure@3.20.1 generate allure-results` — отчёт появится в `allure-report/index.html`. В CI отчёт прикладывается к каждому прогону как артефакт `allure-report`.
