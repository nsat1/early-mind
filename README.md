# Early Mind

[![CI](https://github.com/nsat1/early-mind/actions/workflows/ci.yml/badge.svg)](https://github.com/nsat1/early-mind/actions/workflows/ci.yml)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org)
[![Allure Report](https://img.shields.io/badge/Allure-test%20report-blue)](https://nsat1.github.io/early-mind/)
[![API docs](https://img.shields.io/badge/API-docs-blue?logo=openapiinitiative&logoColor=white)](https://nsat1.github.io/early-mind/api/)

Веб-платформа раннего обучения для детей 3–6 лет: ребёнок изучает контент короткими сессиями, а родитель видит его прогресс.

- [x] API азбуки, PostgreSQL, миграции, роли БД с минимальными правами
- [x] CI: интеграционные тесты на PostgreSQL, отчёты Allure
- [x] Контент алфавита как код с автоматическими проверками
- [x] Контент в БД и фильтрация букв
- [x] Каркас фронтенда: главная страница и список букв
- [ ] Интерфейс азбуки: звуки, иллюстрации, задания
- [ ] Публичная демо-версия
- [ ] Аккаунт родителя: регистрация и вход
- [ ] Профили детей и прогресс на сервере (релиз 2)

## О проекте

- **Проблема.** Детский цифровой контент перенасыщен пассивными развлечениями, а интерес ребёнка к технике уходит в просмотр мультфильмов вместо обучения.
- **Решение.** Короткие обучающие сессии под контролем родителя: ребёнок изучает контент и закрепляет его в заданиях, родитель видит прогресс, сильные и слабые темы.
- **Отличия.** Методика вместо развлечений, родитель — участник процесса, никакой рекламы, работает в браузере без установки.

## Документация

| Документ | Содержание |
|---|---|
| [Модель данных](docs/architecture/data-model.md) | ER-диаграмма и словарь данных |
| [Спецификация API](docs/api/openapi.json) | Контракт REST API в формате OpenAPI 3.1, [документация на GitHub Pages](https://nsat1.github.io/early-mind/api/) |
| [Руководство по запуску](docs/development.md) | Локальный запуск, фронтенд, PostgreSQL, тесты, отчёт Allure |

Материалы анализа — концепция, сценарии, требования, аналитика, архитектура C4 и проектирование аккаунта — в папке [docs/analysis](docs/analysis).

## Структура репозитория

| Папка | Что внутри |
|---|---|
| `backend/` | API на FastAPI (`app/`), контент азбуки (`content/`), миграции, SQL ролей БД, тесты |
| `frontend/` | Веб-приложение на React и TypeScript |
| `docs/` | Модель данных, спецификация API, руководство по запуску; материалы анализа — в `docs/analysis/` |

## Технологии

- **Бэкенд:** Python 3.14, FastAPI, Pydantic.
- **Фронтенд:** TypeScript, React, Vite, React Router, Vitest, Biome.
- **Данные:** PostgreSQL 18, Redis 8, SQLAlchemy 2 (async), Alembic.
- **Тесты:** pytest, интеграционные тесты на PostgreSQL и Redis, Allure Report.
- **Инфраструктура:** Docker Compose, GitHub Actions, uv, Ruff, pre-commit.

## Ключевые решения

- **Минимальные права в БД.** Приложение и миграции работают под разными ролями: приложение может читать, добавлять, изменять и удалять строки, но не менять схему. Это проверяется тестами.
- **Контент как код.** Алфавит хранится в TOML-файле и проходит валидацию и автоматические проверки целостности: позиция буквы, её вид, слова на эту букву.
- **Тесты на настоящей PostgreSQL.** Интеграционные тесты создают отдельную тестовую БД, применяют миграции и проверяют ограничения, права ролей и соответствие миграций моделям.
- **Публичный отчёт о тестах.** Отчёт Allure прикладывается к каждому запуску GitHub Actions, а отчёт по ветке `main` [опубликован на GitHub Pages](https://nsat1.github.io/early-mind/).
