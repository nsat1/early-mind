1. Запустите БД: `docker compose up -d --wait db`.

БД `early_mind`, пользователь `early_mind_admin`, адрес `127.0.0.1:5432`.
Данные сохраняются в volume `postgres_data`; остановка без удаления данных: `docker compose stop db`.
Переменные `POSTGRES_*` применяются при первой инициализации пустого volume; изменение `.env` не меняет пароль существующей БД.
