# Inventory & Order Management — Web App

Веб-версия системы учёта товаров и заказов (Flask + PostgreSQL). Доступ через
браузер у нескольких пользователей одновременно, авторизация по логину/паролю,
интерфейс на английском и китайском.

Это полностью отдельный проект от десктоп-версии (`../app/`).

---

## Возможности
- **Inventory**: товары с фото, варианты (цвет/размер), поиск и фильтры,
  приход/расход, история движения.
- **Orders**: заказы клиентов, позиции заказа, отметка об отправке
  (списание склада), возврат к статусу «New» (возврат склада).
- **Statistics**: выручка/заказы/единицы, график во времени (Chart.js),
  фильтр по товару, топ-товары.
- **Авторизация**: вход по логину/паролю (несколько аккаунтов).
- **Язык**: переключение EN / 中文.

Склад всегда вычисляется: `stock = SUM(stock_in) − SUM(stock_out)`.
Списание происходит **только при отметке заказа отправленным**.

---

## Структура
```
webapp/
├── app.py              # Flask-приложение и все маршруты
├── db.py               # подключение к PostgreSQL (из DATABASE_URL)
├── repository.py       # бизнес-логика (порт десктопной версии)
├── auth.py             # логин/логаут, хеш паролей
├── schema.sql          # схема PostgreSQL (6 таблиц + users)
├── translations.py     # i18n EN/ZH + фильтр tr()
├── config.py           # конфиг из переменных окружения
├── templates/          # Jinja2-шаблоны
├── static/style.css    # стили поверх Bootstrap 5
├── requirements.txt
├── Procfile            # для Render/Heroku
└── render.yaml         # Blueprint для деплоя на Render
```

---

## Локальный запуск (для разработки)

### 1. Установить Python и PostgreSQL
- **Python 3.11+**: <https://www.python.org/downloads/>
- **PostgreSQL**: проще всего через Docker:
  ```bash
  docker run --name inv-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=inventory -p 5432:5432 -d postgres:16
  ```

### 2. Установить зависимости
```bash
cd webapp
pip install -r requirements.txt
```

### 3. Задать переменные окружения
```bash
# Windows (cmd):
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/inventory
set SECRET_KEY=any-random-string

# Linux/macOS:
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/inventory
export SECRET_KEY=any-random-string
```

### 4. Создать таблицы и первого пользователя
```bash
flask --app app.py init-db
flask --app app.py create-user admin mypassword --display "Admin"
```

### 5. Запустить
```bash
python app.py
```
Открыть <http://localhost:5000>, войти как `admin` / `mypassword`.

---

## Деплой в интернет (бесплатно: Supabase + Render)

Архитектура: **база данных на Supabase** (бесплатно навсегда, не удаляется) +
**приложение на Render** (бесплатный web service). Общая стоимость: **$0**.

> ⚠️ Почему не Render для БД: бесплатный PostgreSQL на Render **удаляется
> через 30 дней**. Supabase даёт постоянный free tier (500 МБ — для учёта
> товаров хватит надолго, не удаляется). Приложение на Render бесплатное,
> но «засыпает» через 15 мин неактивности (первый запрос после сна ~50 сек).

### Шаг 1. Создать базу данных на Supabase
1. Зарегистрируйтесь на <https://supabase.com> (через GitHub или email).
2. **New Project** → имя (например `stock`), сгенерируйте пароль БД, регион
   `Frankfurt` (или ближайший).
3. Дождитесь создания (~2 мин).
4. Откройте **Project Settings → Database → Connection string**. Вам нужна
   строка **Connection pooling** (через пулер, порт `6543`) — она выглядит так:
   ```
   postgresql://postgres.[проект]:[пароль]@aws-0-[регион].pooler.supabase.com:6543/postgres
   ```
   Скопируйте её и **подставьте свой реальный пароль** вместо `[пароль]`.

### Шаг 2. Создать таблицы в БД (один раз)
**Вариант A — через веб-интерфейс Supabase (проще):**
1. Откройте **SQL Editor** в проекте Supabase.
2. Скопируйте всё содержимое файла `webapp/schema.sql`, вставьте и нажмите **Run**.

**Вариант B — локально:**
```bash
set DATABASE_URL=<ваша строка из Supabase>   # подставьте свою
flask --app app.py init-db
```

### Шаг 3. Задеплоить приложение на Render
**Вариант A — через Blueprint (проще):**
1. На <https://render.com> → **New → Blueprint** → выберите репозиторий `stock`.
2. Render прочитает `webapp/render.yaml` и создаст web service.
3. В **Dashboard → ваш сервис → Environment** добавьте переменную:
   - `DATABASE_URL` = ваша строка подключения из Supabase (порт 6543)
   (SECRET_KEY Render сгенерирует сам.)
4. Render задеплоит автоматически. URL: `https://stock-xxxx.onrender.com`.

**Вариант B — вручную (Web Service):**
1. **New + → Web Service** → репозиторий `stock`, **Root Directory** = `webapp`,
   **Build** = `pip install -r requirements.txt`,
   **Start** = `gunicorn app:app --workers 1 --threads 4 --timeout 60`.
2. В **Environment** добавьте:
   - `DATABASE_URL` = строка из Supabase (порт 6543)
   - `SECRET_KEY` = случайная строка (например, `python -c "import secrets;print(secrets.token_hex(32))"`)
   - `FLASK_APP` = `app.py`
   - `PYTHON_VERSION` = `3.11.9`

### Шаг 4. Создать первого пользователя
После деплоя откройте **Shell** веб-сервиса на Render и выполните:
```bash
flask --app app.py create-user admin вашпароль --display "Admin"
```
Теперь можно войти на `https://stock-xxxx.onrender.com` как `admin`.

### Переменные окружения
| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | строка подключения **Supabase** (вставляете вручную) |
| `SECRET_KEY` | случайная строка (Render может сгенерировать) |
| `FLASK_APP` | `app.py` |
| `PYTHON_VERSION` | `3.11.9` |

### Если «засыпание» Render мешает
Бесплатный web service Render засыпает через 15 мин неактивности — первый
запрос после сна идёт ~50 сек. Если это мешает, апгрейдните web service до
Starter ($7/мес, не засыпает). БД на Supabase остаётся бесплатной.

---

## Создание новых пользователей
Через Shell веб-сервиса на Render (или локально):
```bash
flask --app app.py create-user ivan secretpass --display "Иван"
```

## Бэкап данных
- **Supabase:** Dashboard → ваш проект → **Database → Backups** (на free tier
  есть point-in-time за последние 7 дней). Также можно выгрузить через SQL Editor.
- Локально: `pg_dump "<DATABASE_URL>" > backup.sql`.

## Резюме для не-технического пользователя
Чтобы запустить в интернете бесплатно:
1. Создайте БД на Supabase (бесплатно) — скопируйте connection string (порт 6543).
2. Положите код на GitHub (уже сделано).
3. На Render создайте web service из репозитория, вставьте строку Supabase как
   `DATABASE_URL`.
4. Создайте логин/пароль командой через Shell.
5. Раздайте команде URL + логин/пароль.
