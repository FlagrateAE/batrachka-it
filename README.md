# BatrachkaIT

REST API для пошуку роботи в IT: рекрутери публікують стандартизовані вакансії, кандидати
знаходять їх за точними фільтрами (домен, зарплатна вилка, досвід, формат роботи, тип компанії,
рівень англійської) і подають заявки. Контакти сторін розкриваються лише після схвалення заявки,
а найм кандидата атомарно закриває вакансію.

Проєкт виконано в межах лабораторних робіт №4 (базова структура коду) та №5 (інтеграція
компонентів і управління залежностями). Вимоги, архітектура та беклог описані в ЛР1–ЛР3.

**Команда:** ІМ-43 Балалаєв М. Ю., ІМ-44 Лебедєва С. А., ІМ-44 Криницький Я. В.

## Зміст

1. [Стек технологій](#1-стек-технологій)
2. [Архітектура та структура проєкту](#2-архітектура-та-структура-проєкту)
3. [Швидкий старт у Docker](#3-швидкий-старт-у-docker)
4. [Локальна розробка (WSL Debian + uv)](#4-локальна-розробка-wsl-debian--uv)
5. [Змінні середовища](#5-змінні-середовища)
6. [API](#6-api)
7. [Тестування](#7-тестування)
8. [Виконання функціональних вимог](#8-виконання-функціональних-вимог)
9. [Виконання нефункціональних вимог](#9-виконання-нефункціональних-вимог)
10. [Команда та внесок](#10-команда-та-внесок)
11. [Спрощення та обмеження](#11-спрощення-та-обмеження)

## 1. Стек технологій

| Шар | Технологія | Версія (uv.lock) |
|---|---|---|
| Мова | Python | 3.14 (`requires-python >= 3.12`) |
| Пакетний менеджер | uv | 0.13.6 |
| Веб-фреймворк | FastAPI / Starlette / Uvicorn | 0.165.0 / 1.10.0 / 0.54.0 |
| Валідація | Pydantic / pydantic-settings | 2.14.4 / 2.16.3 |
| ORM і драйвер | SQLAlchemy (async) / asyncpg | 2.0.58 / 0.32.0 |
| Міграції | Alembic | 1.20.1 |
| Безпека | PyJWT / pwdlib + argon2-cffi | 2.15.1 / 0.4.2 + 25.1.0 |
| СУБД | PostgreSQL | 17 (образ `postgres:17-alpine`) |
| Тести | pytest / pytest-asyncio / pytest-cov / httpx | 9.2.0 / 1.5.0 / 7.1.0 / 0.28.1 |
| Лінтер і форматер | Ruff | 0.17.6 |
| Контейнеризація | Docker, Docker Compose | сервіси `api` і `db` |
| CI | GitHub Actions | `.github/workflows/ci.yml` |

Залежності описані в `pyproject.toml` (діапазони версій) і зафіксовані в `uv.lock` (точні версії
з хешами для всього дерева). Група `dev` містить інструменти тестування і не потрапляє в
Docker-образ.

## 2. Архітектура та структура проєкту

Модульний моноліт із шаруватою архітектурою (ЛР2). Кожен предметний модуль має однакові шари:

```
router (HTTP, Pydantic-схеми)  →  service (бізнес-правила)  →  repository (SQLAlchemy)  →  PostgreSQL
```

Шари зв'язуються через `Depends` у файлах `dependencies.py` кожного модуля. Збирання застосунку
(composition root) відбувається у `create_app()`: там створюються рушій БД, фабрика сесій,
`PasswordHasher` і `TokenService`.

```
batrachkait/
├── src/app/
│   ├── main.py                 # create_app(): збирання застосунку, OpenAPI, lifespan
│   ├── api.py                  # агрегує роутери модулів під /api/v1
│   ├── health.py               # GET /health
│   ├── models.py               # реєстр усіх ORM-моделей (для Alembic і mapper-ів)
│   ├── core/
│   │   ├── config.py           # Settings / DatabaseSettings (pydantic-settings, .env)
│   │   ├── database.py         # рушій, фабрика сесій, протокол UnitOfWork
│   │   ├── security.py         # PasswordHasher (Argon2), TokenService (JWT access/refresh)
│   │   ├── dependencies.py     # SessionDep, TokenServiceDep, PasswordHasherDep
│   │   ├── exceptions.py       # доменні винятки без залежності від HTTP
│   │   └── error_handlers.py   # відображення доменних винятків на HTTP-коди
│   ├── common/
│   │   ├── enums.py            # перелічувані типи з ERD
│   │   ├── db.py               # Base, naming convention, TimestampMixin, ENUM-типи PostgreSQL
│   │   └── schemas.py          # пагінація Page/PageParams, PatchModel
│   ├── auth/                   # реєстрація, вхід, refresh; get_current_user, require_role
│   ├── users/                  # моделі User/Candidate/Recruiter (ISA), профіль /users/me
│   ├── vacancies/              # публікація, редагування, закриття, пошук
│   └── applications/           # заявки, статуси, розкриття контактів, транзакція найму
├── migrations/                 # Alembic (async env.py), початкова міграція 0001
├── tests/
│   ├── unit/                   # безпека, Pydantic-схеми
│   └── integration/            # ендпоінти, фільтри, найм, конкурентність, міграції
├── scripts/
│   ├── seed.py                 # демо-дані: акаунти + N вакансій
│   └── load_test.py            # навантажувальний тест пошуку (NFR-1.1)
├── docs/
│   ├── MANUAL_TESTING.md       # інструкція ручного тестування (46 тест-кейсів)
│   ├── COMMIT_PLAN.md          # план комітів і розподіл між учасниками
│   └── diagrams/erd.plantuml   # ERD з ЛР2
├── docker/postgres/init/       # створення тестової БД при першому запуску контейнера
├── Dockerfile, compose.yaml, .dockerignore
├── pyproject.toml, uv.lock, .python-version, alembic.ini
└── .env.example, .gitignore, .github/workflows/ci.yml
```

### Принципи SOLID у коді

| Принцип | Де видно |
|---|---|
| S — єдина відповідальність | Роутер лише перетворює HTTP ↔ схеми, сервіс тримає правила, репозиторій формує SQL. `error_handlers.py` окремо від `exceptions.py`, тому сервіси не знають про HTTP. |
| O — відкритість/закритість | Новий модуль підключається одним рядком в `api.py`. Новий тип доменної помилки додається в `exceptions.py` і словник кодів, без зміни обробника. |
| L — підстановка Лісков | Будь-яка реалізація протоколів `UserRepository`, `VacancyRepository`, `ApplicationRepository`, `UnitOfWork` підходить сервісу, наприклад фейкова в тестах. `AsyncSession` структурно задовольняє `UnitOfWork`. |
| I — розділення інтерфейсів | `VacancyService` залежить лише від вузького протоколу `ActiveApplicationsRejecter` (один метод), а не від усього репозиторію заявок. |
| D — інверсія залежностей | Сервіси приймають протоколи в конструкторі, конкретні класи підставляються в `dependencies.py` через `Depends`. |

### Відповідність діаграмам ЛР2

* **ERD** → `users/models.py`, `vacancies/models.py`, `applications/models.py`, міграція `0001`.
  Назви таблиць, стовпців і ENUM-значень збігаються з `docs/diagrams/erd.plantuml`.
* **Use Case** → ендпоінти (розділ 6), правила ролей у `auth/dependencies.py` (`require_role`).
* **Sequence «Найм кандидата»** → `ApplicationService.change_status`: блокування вакансії
  (`SELECT … FOR UPDATE`), гілка `alt [Open]` змінює статуси в одній транзакції, гілка
  `alt [Closed]` повертає `409 Vacancy is closed`.

## 3. Швидкий старт у Docker

Потрібні Docker і Docker Compose (Docker Desktop з увімкненою інтеграцією WSL).

```bash
git clone <url-репозиторію> batrachkait && cd batrachkait
cp .env.example .env
sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$(openssl rand -hex 32)/" .env
docker compose up --build -d
docker compose ps                      # обидва сервіси мають бути healthy/running
curl http://localhost:8000/health      # {"status":"ok","database":"ok"}
```

Swagger UI: <http://localhost:8000/docs>. Контейнер `api` при старті сам застосовує міграції
(`alembic upgrade head`) і запускає Uvicorn з `UVICORN_WORKERS` процесами.

Корисні команди:

```bash
docker compose logs -f api                                   # логи застосунку
docker compose exec db psql -U batrachka -d batrachkait      # консоль PostgreSQL
docker compose exec api python scripts/seed.py --vacancies 10000   # демо-дані
docker compose down          # зупинити (дані зберігаються в томі pgdata)
docker compose down -v       # зупинити і видалити дані
```

## 4. Локальна розробка (WSL Debian + uv)

Встановлення uv і Python (один раз):

```bash
sudo apt update && sudo apt install -y curl ca-certificates git
curl --proto '=https' --tlsv1.2 -LsSf https://releases.astral.sh/github/uv/releases/download/0.13.6/uv-installer.sh | sh
source $HOME/.local/bin/env
uv python install 3.14
```

Запуск проєкту (PostgreSQL береться з compose):

```bash
cp .env.example .env                    # і задайте JWT_SECRET_KEY, як у розділі 3
uv sync                                 # створює .venv з основними та dev-залежностями
docker compose up -d db                 # лише база даних
uv run alembic upgrade head             # схема БД
uv run uvicorn app.main:create_app --factory --reload
```

Якщо після клонування ваша версія uv переписує `uv.lock` (`uv sync` показує зміни у файлі),
закомітьте оновлений lock-файл: Docker-збірка використовує `uv sync --locked` і вимагає
актуального lock-файлу.

Якість коду:

```bash
uv run ruff check .          # лінтер
uv run ruff format .         # форматування
```

Нова міграція після зміни моделей:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run alembic check         # має вивести "No new upgrade operations detected"
```

## 5. Змінні середовища

| Змінна | За замовчуванням | Призначення |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://batrachka:batrachka@localhost:5432/batrachkait` | Підключення застосунку і Alembic. У compose підміняється на хост `db`. |
| `TEST_DATABASE_URL` | `…/batrachkait_test` | Окрема БД для pytest (таблиці перестворюються). |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 10 / 10 | Пул з'єднань на один процес Uvicorn. |
| `JWT_SECRET_KEY` | — (обов'язкова, ≥ 32 символи) | Ключ підпису JWT. |
| `JWT_ALGORITHM` | `HS256` | Алгоритм підпису. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Час життя access-токена. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Час життя refresh-токена. |
| `UVICORN_WORKERS` | 2 | Кількість процесів у контейнері. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `batrachka` / `batrachka` / `batrachkait` | Ініціалізація контейнера PostgreSQL. |

Обмеження: `UVICORN_WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)` має бути меншим за
`max_connections` PostgreSQL (100 за замовчуванням).

## 6. API

Усі бізнес-ендпоінти мають префікс `/api/v1`. Запити, що змінюють стан, вимагають заголовка
`Authorization: Bearer <access_token>`. Помилки повертаються у форматі `{"detail": "..."}`.

| Метод | Шлях | Доступ | Призначення |
|---|---|---|---|
| GET | `/health` | усі | Стан сервісу і БД |
| POST | `/auth/register` | гість | Реєстрація кандидата або рекрутера (поле `role`) |
| POST | `/auth/login` | гість | OAuth2 password flow, `username` = email → access + refresh |
| POST | `/auth/refresh` | гість з refresh | Нова пара токенів |
| GET | `/users/me` | авторизований | Власний профіль із контактами |
| PATCH | `/users/me` | авторизований | Часткове оновлення профілю (`candidate` / `recruiter` блоки) |
| GET | `/vacancies` | усі | Пошук відкритих вакансій за фільтрами, сортування, пагінація |
| GET | `/vacancies/{id}` | усі | Деталі вакансії (без контактів) |
| POST | `/vacancies` | рекрутер | Публікація вакансії (`OPEN`) |
| GET | `/vacancies/my` | рекрутер | Власні вакансії з кількістю заявок |
| PATCH | `/vacancies/{id}` | автор | Редагування відкритої вакансії |
| POST | `/vacancies/{id}/close` | автор | Ручне закриття, активні заявки → `REJECTED` |
| DELETE | `/vacancies/{id}` | автор | Видалення разом із заявками (каскад) |
| POST | `/vacancies/{id}/apply` | кандидат | Заявка з необов'язковим супровідним листом (`PENDING`) |
| GET | `/vacancies/{id}/applications` | автор | Заявки на вакансію, фільтр `status` |
| GET | `/applications/my` | кандидат | Власні заявки, фільтр `status` |
| GET | `/applications/{id}` | учасники заявки | Деталі; для сторонніх `404` |
| PATCH | `/applications/{id}/status` | автор вакансії | `ACCEPTED` / `REJECTED` / `HIRED` |

Параметри пошуку `GET /vacancies`:

| Параметр | Семантика |
|---|---|
| `domain`, `company_type`, `work_format` | точний збіг |
| `english_level` | ваш рівень: повертаються вакансії, що вимагають такого самого або нижчого (порядок ENUM у PostgreSQL) |
| `experience_years` | ваш досвід: вакансії, що вимагають стільки ж років або менше |
| `salary_from` / `salary_to` | перетин вилок: `salary_max ≥ salary_from`, `salary_min ≤ salary_to` |
| `sort_by` | `created_at` (за замовчуванням) або `salary_max` |
| `order` | `desc` (за замовчуванням) або `asc` |
| `limit` / `offset` | 20 / 0 за замовчуванням, `limit` ≤ 100 |

Дозволені переходи статусу заявки: `PENDING → ACCEPTED | REJECTED | HIRED`,
`ACCEPTED → REJECTED | HIRED`. `REJECTED` і `HIRED` кінцеві. Будь-які зміни на закритій вакансії
повертають `409`.

## 7. Тестування

### Автоматичні тести

```bash
docker compose up -d db
uv run pytest                                   # 113 тестів
uv run pytest --cov --cov-report=term-missing   # з покриттям, поріг 70% (fail_under)
uv run pytest tests/integration/test_concurrency.py -v   # лише конкурентність
```

| Набір | Тестів | Що перевіряє |
|---|---|---|
| `unit/test_security.py` | 9 | Argon2, сіль, JWT: тип токена, термін дії, підпис, обов'язкові claims |
| `unit/test_user_schemas.py` | 12 | Реєстрація за роллю, нормалізація email, PATCH без `null` для обов'язкових полів |
| `unit/test_vacancy_schemas.py` | 14 | Вилка зарплати, ліміти пагінації, політика розкриття контактів |
| `integration/test_auth.py` | 11 | Реєстрація, дубль email, вхід, refresh, хеш у БД |
| `integration/test_users.py` | 9 | Профіль, оновлення, ролі, 401 без токена |
| `integration/test_vacancies.py` | 26 | CRUD, права автора, усі фільтри, сортування, пагінація, каскад, статистика |
| `integration/test_applications.py` | 22 | Подача, дублі, приховування/розкриття контактів, переходи, найм |
| `integration/test_concurrency.py` | 5 | Блокування вакансії, одночасний найм, одночасні дублікати заявок |
| `integration/test_migrations.py` | 1 | Міграції = моделі (обмеження, індекси, ENUM), чистий downgrade |
| `integration/test_system.py` | 4 | `/health`, OpenAPI, Swagger UI |

Фактичний результат: **113 passed, покриття 97,4%**. Інтеграційні тести працюють зі справжнім
PostgreSQL (не SQLite), бо перевіряють ENUM, блокування рядків і обмеження цілісності.

### Ручне тестування

Покрокова інструкція з командами `curl` та очікуваними відповідями: [`docs/MANUAL_TESTING.md`](docs/MANUAL_TESTING.md).

### Навантажувальний тест

```bash
docker compose exec api python scripts/seed.py --vacancies 10000
uv run python scripts/load_test.py --concurrency 100 --requests-per-client 20
```

Скрипт виводить пропускну здатність і перцентилі затримки та повертає код `1`, якщо p95 > 250 мс.

### CI

`.github/workflows/ci.yml` на кожен push і pull request: `ruff check`, `ruff format --check`,
`alembic upgrade head`, `alembic check`, `alembic downgrade base`, `pytest --cov` на сервісі
PostgreSQL 17.

## 8. Виконання функціональних вимог

| Вимога | Реалізація | Автотести | Ручні кейси |
|---|---|---|---|
| FR-1.1 Реєстрація з роллю і профілем | `POST /auth/register`, дискримінатор `role` | `test_auth.py`, `test_user_schemas.py` | TC-04…TC-07 |
| FR-1.2 OAuth2 / JWT access + refresh | `POST /auth/login`, `POST /auth/refresh`, `TokenService` | `test_auth.py`, `test_security.py` | TC-09…TC-11 |
| FR-1.3 Оновлення профілю | `PATCH /users/me` | `test_users.py` | TC-12…TC-14 |
| FR-2.1 Публікація вакансії | `POST /vacancies` (лише рекрутер) | `test_vacancies.py` | TC-15, TC-16 |
| FR-2.2 Фіксований набір характеристик | `VacancyCreate`, ENUM + CHECK у БД | `test_vacancy_schemas.py`, `test_vacancies.py` | TC-15, TC-17 |
| FR-2.3 `OPEN` → `CLOSED` (найм або вручну) | `change_status`, `POST /vacancies/{id}/close` | `test_applications.py`, `test_vacancies.py` | TC-36, TC-38 |
| FR-3.1 Комбіновані фільтри відкритих вакансій | `GET /vacancies`, `_build_conditions` | `test_vacancies.py` (9 тестів фільтрів) | TC-20…TC-25 |
| FR-3.2 Без повнотекстового пошуку, сортування | лише реляційні умови; `sort_by` | `test_vacancies.py` | TC-26 |
| FR-4.1 Заявка `PENDING` з листом | `POST /vacancies/{id}/apply` | `test_applications.py` | TC-29, TC-30 |
| FR-4.2 `ACCEPTED` / `REJECTED` / `HIRED` | `PATCH /applications/{id}/status`, `ALLOWED_TRANSITIONS` | `test_applications.py` | TC-31…TC-34 |
| FR-4.3 Найм закриває вакансію і відхиляє інших | одна транзакція в `ApplicationService.change_status` | `test_applications.py`, `test_concurrency.py` | TC-36, TC-37 |
| FR-4.4 Контакти після `ACCEPTED` / `HIRED` | `to_recruiter_view`, `to_candidate_view` | `test_applications.py` | TC-31, TC-32, TC-36 |
| Could Have: «Мої відгуки», «Відгуки на мої вакансії» | `GET /applications/my`, `GET /vacancies/{id}/applications` з `status` | `test_applications.py` | TC-35 |
| Could Have: статистика відгуків | `applications_count` у `GET /vacancies/my` | `test_vacancies.py` | TC-35 |

## 9. Виконання нефункціональних вимог

| Вимога | Як забезпечено | Доказ |
|---|---|---|
| NFR-1.1 Пошук ≤ 250 мс при 100 з'єднаннях | B-Tree індекси (`status, domain`), (`status, created_at`), (`status, salary_max`), `salary_min`, `experience_years_required`; сторінка й `total` одним запитом (`count(*) OVER()`); asyncpg; кілька процесів Uvicorn | `EXPLAIN ANALYZE` і навантаження (TC-45), виміри нижче, `scripts/load_test.py` |
| NFR-1.2 Пагінація, 20 за замовчуванням | `PageParams(limit=20, offset=0)`, `limit ≤ 100` | `test_default_page_size_is_20`, TC-27 |
| NFR-2.1 Argon2 із сіллю | `pwdlib` `PasswordHash.recommended()` → `$argon2id$` | `test_password_is_stored_as_argon2_hash`, TC-08 |
| NFR-2.2 Контакти приховані | `contact_info` відсутній у схемах вакансії, `null` у заявках до `ACCEPTED` | `test_contacts_are_hidden_while_pending`, TC-18, TC-31 |
| NFR-2.3 Bearer JWT для змінних запитів | `OAuth2PasswordBearer` + `require_role` на кожному POST/PATCH/DELETE, крім `/auth/*` | тести `401` / `403`, TC-16, TC-43 |
| NFR-3.1 Транзакційний найм без race condition | `SELECT … FOR UPDATE` на вакансії, `FOR UPDATE` на заявці, повторна перевірка статусу після блокування, `FOR SHARE` під час подачі заявки | `test_concurrency.py` (див. нижче), TC-39, TC-40 |
| NFR-3.2 `ON DELETE CASCADE` + `UNIQUE(vacancy_id, candidate_id)` | FK у моделях і міграції | `test_delete_cascades_to_applications`, `test_migrations.py`, TC-41, TC-42 |
| NFR-4.1 OpenAPI на `/docs` | автоматична специфікація FastAPI, теги й описи | `test_system.py`, TC-02 |
| NFR-4.2 Покриття ≥ 70% | `fail_under = 70` у `pyproject.toml`, перевірка в CI | 97,4% |

### NFR-3.1: як перевірено, що блокування справді працює

Тест одночасного найму (`asyncio.gather` п'яти запитів `HIRED`) проходив навіть після того, як
блокування тимчасово прибрали: вікно гонки надто коротке, щоб його стабільно влучити. Тому
додано два детерміновані тести. Тест сам утримує `SELECT … FOR UPDATE` на вакансії в окремому
з'єднанні, надсилає запит через API, перевіряє, що запит **чекає**, потім закриває вакансію і
відпускає блокування. Запит має повернути `409 Vacancy is closed`. Контрольний експеримент:
без `with_for_update` у `VacancyRepository.get_locked` ці тести падають.

### NFR-1.1: виміри

Умови: 2 vCPU, PostgreSQL 16 на тому самому хості, 10 000 вакансій, `UVICORN_WORKERS=2`,
генератор навантаження ApacheBench з keep-alive, запит
`/vacancies?domain=PYTHON&salary_from=3000&experience_years=4`, клієнти без пауз між запитами.

| Одночасних з'єднань | Запитів/с | p50, мс | p95, мс | p99, мс | Помилок |
|---|---|---|---|---|---|
| 1 | 192 | 5 | 7 | 8 | 0 |
| 10 | 400 | 23 | 43 | 55 | 0 |
| 50 | 423 | 112 | 149 | 319 | 0 |
| 100 | 436 | 223 | **321** | 605 | 0 |

Висновок: у цьому середовищі вимога виконується до ~50 одночасних з'єднань. При 100 медіана
(223 мс) вкладається в ліміт, а p95 (321 мс) ні. Власна обробка запиту займає 5–8 мс, решта
часу — це черга. Стеля близько 435 запитів/с на 2 ядра, які сервер ділить із PostgreSQL. За
законом Літтла 100 клієнтів без пауз дають середнє очікування не менше 100 / 435 ≈ 230 мс.
Вимогу при 100 з'єднаннях потрібно перевірити на машині з ≥ 4 ядрами та `UVICORN_WORKERS=4`,
запустивши генератор навантаження окремо від сервера, і внести результат у таблицю:

| Середовище | Workers | p50, мс | p95, мс | Дата, хто виміряв |
|---|---|---|---|---|
| _заповнити_ | | | | |

## 10. Команда та внесок

| Учасник | Роль | Зона відповідальності в ЛР4–ЛР5 |
|---|---|---|
| Балалаєв Максим | Lead Backend Engineer / System Architect | Ініціалізація проєкту, ENUM і модель даних, `database.py`, модулі `vacancies` і `applications`, транзакція найму, тести бізнес-логіки й конкурентності |
| Криницький Ярослав | Backend Engineer (Infrastructure & Security) | Конфігурація, Alembic, Docker / Compose, CI, `security.py`, модулі `auth` і `users`, DI-залежності, тест міграцій, seed-скрипт |
| Лебедєва Софія | System Analyst & QA Engineer | Інфраструктура pytest, модульні тести схем, тести auth / users, фільтрів і пагінації, OpenAPI, навантажувальний тест, `MANUAL_TESTING.md`, README |

Робота ведеться в окремих гілках з pull request і рев'ю іншим учасником перед злиттям у `main`.
Повний перелік комітів, гілок і рецензентів: [`docs/COMMIT_PLAN.md`](docs/COMMIT_PLAN.md).

## 11. Спрощення та обмеження

* **Refresh-токени без відкликання.** Токени stateless: немає чорного списку, logout і ротації з
  інвалідацією старого refresh. Скомпрометований refresh-токен діє до закінчення терміну (7 днів).
* **Немає завантаження файлів.** `avatar_url` — посилання, резюме — текст (`resume_text`), як у
  специфікації.
* **Немає видалення облікового запису і модерації.** Каскадні FK у схемі є, але ендпоінта видалення
  користувача немає.
* **Offset-пагінація.** На глибоких сторінках повільніша за cursor-based; для обсягів проєкту
  достатньо.
* **Без rate limiting і CORS.** Окремого фронтенду немає (Won't Have), API використовується через
  Swagger UI / Postman.
* **SQLAlchemy 2.0.x, а не 2.1.** Так у специфікації (`>=2.0.58,<2.1`), хоча 2.1 уже доступна.
* **NFR-1.1 при 100 з'єднаннях не підтверджено** на тестовому стенді (розділ 9).
* **Docker-образ не зібраний у середовищі розробки цього README.** Реєстри образів були недоступні.
  `compose.yaml` перевірено командою `docker compose config`, а кроки Dockerfile (чисте оточення без
  dev-залежностей, `--no-editable`, міграції, 2 воркери, healthcheck, seed) відтворено вручну. Перший
  `docker compose up --build` на вашій машині — це і є остаточна перевірка (TC-01).
