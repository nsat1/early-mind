# Руководство по запуску

Код бэкенда, контент и миграции лежат в папке `backend`, фронтенд — в `frontend`. Команды `uv` выполняются в папке `backend`, `docker compose` — в корне проекта.

## PostgreSQL, Redis и почта

1. Установите и запустите [Docker Desktop](https://docs.docker.com/desktop/).
2. Скопируйте `.env.example` в `.env` и задайте случайные `POSTGRES_PASSWORD`, `DB_PASSWORD`, `DB_MIGRATION_PASSWORD` и `REDIS_PASSWORD`.
3. Запустите PostgreSQL, Redis и почтовый ящик [Mailpit](https://mailpit.axllent.org/): `docker compose up -d --wait`. Письма, которые отправляет приложение, видны на http://localhost:8025.
4. В папке `backend` примените миграции: `uv run --locked alembic upgrade head`.
5. Загрузите контент: `uv run --locked python -m app.alphabet.sync`. Команда добавляет и обновляет буквы и слова из `backend/content/alphabets`, повторный запуск безопасен. Буквы, удалённые из файлов, остаются в БД: команда выводит о них предупреждение.

Роли и их пароли создаются только при первом запуске на пустом томе. Чтобы применить изменения в `backend/scripts/db`, пересоздайте БД (все данные будут удалены): `docker compose down -v`.

## Бэкенд

1. Установите [uv](https://docs.astral.sh/uv/getting-started/installation/), откройте терминал в папке `backend` и установите зависимости: `uv sync --locked`. В PyCharm выберите интерпретатор `backend/.venv` и укажите `backend` рабочей папкой конфигурации запуска.
2. Запустите API: `uv run --locked uvicorn app.main:create_app --factory --loop asyncio:SelectorEventLoop`.
3. Откройте [Swagger UI](http://127.0.0.1:8000/docs).

## Фронтенд

1. Установите [Node.js 24](https://nodejs.org/) и откройте терминал в папке `frontend`.
2. Установите зависимости: `npm ci`.
3. Запустите: `npm run dev` и откройте http://localhost:5173. Данные приходят с бэкенда: сервер разработки перенаправляет `/api` и `/media` на http://127.0.0.1:8000, поэтому сначала запустите БД и бэкенд.

Проверки: типы — `npm run typecheck`, тесты — `npm test`, стиль кода — `npm run lint` ([Biome](https://biomejs.dev/), исправить — `npm run format`), сборка — `npm run build`.

Типы API в `src/api/schema.ts` генерируются из `docs/api/openapi.json`, руками их не правьте. После изменения API обновите их: `npm run api:types` (при коммите это делает хук).

## Тесты

- Все тесты, в папке `backend`: `uv run --locked pytest`.
- Интеграционные тесты создают отдельную БД `early_mind_test` в запущенной PostgreSQL и используют отдельную БД Redis; без PostgreSQL и Redis они пропускаются.
- Только быстрые тесты без сервисов: `uv run --locked pytest -m "not integration"`.
- После изменения API обновите спецификацию `docs/api/openapi.json`: `uv run --locked python -m app.openapi`. Иначе упадёт тест её актуальности. Файл генерируется из кода, тексты правьте в коде.
- Документация API по ветке `main` публикуется на [GitHub Pages](https://nsat1.github.io/early-mind/api/) после каждого успешного прогона CI.

## Pre-commit

- Установите хуки один раз, в папке `backend`: `uv run --locked pre-commit install`. Для проверки фронтенда нужны его зависимости: `npm ci` в папке `frontend`.
- При `git commit` хуки запускают Ruff и Biome, проверяют файлы и обновляют `docs/api/openapi.json`. Если хук исправил файлы, коммит останавливается: добавьте исправления (`git add`) и повторите коммит.
- Проверить весь репозиторий вручную: `uv run --locked pre-commit run --all-files`.

## Отчёт [Allure](https://allurereport.org/) (нужен Node.js)

- Прогон, в папке `backend`: `uv run --locked pytest --alluredir=allure-results --clean-alluredir`.
- Собрать отчёт: `npx allure@3.20.1 generate allure-results`.
- Открыть отчёт: `start allure-report/index.html`.
- Отчёт по ветке `main` публикуется на [GitHub Pages](https://nsat1.github.io/early-mind/) после каждого успешного прогона CI.
