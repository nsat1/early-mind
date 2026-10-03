# early-mind

## Локальный запуск

1. Установите [uv](https://docs.astral.sh/uv/getting-started/installation/) и откройте терминал в корне проекта.
2. Запустите API: `uv run --locked uvicorn app.main:create_app --factory`.
3. Откройте [Swagger UI](http://127.0.0.1:8000/docs) или [проверку работоспособности](http://127.0.0.1:8000/health).
