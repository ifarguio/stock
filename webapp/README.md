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

## Деплой на Render (через интернет)

> ⚠️ **Важно про бесплатный тариф Render:** бесплатный PostgreSQL **удаляется
> через 30 дней** после создания. Для реальной работы апгрейдните базу до
> Starter (~$6/мес) — она не удаляется. Web service можно оставить бесплатным
> (он «засыпает» через 15 мин неактивности, первый запрос после сна ~50 сек).

### Вариант A — через GitHub (рекомендуется)
1. Загрузите проект на GitHub.
2. На <https://render.com> → **New → Blueprint** → выберите репозиторий.
   Render сам прочитает `webapp/render.yaml` и создаст БД + web service.
3. После первого деплоя откройте **Shell** веб-сервиса и создайте пользователя:
   ```bash
   flask --app app.py create-user admin mypassword --display "Admin"
   ```
4. Откройте URL вида `https://inventory-orders-xxxx.onrender.com/login`.

### Вариант B — вручную
1. **New + → PostgreSQL** (free), запомните `DATABASE_URL`.
2. **New + → Web Service** → выберите репозиторий, **Root Directory** = `webapp`,
   **Build** = `pip install -r requirements.txt`,
   **Start** = `gunicorn app:app --workers 1 --threads 4 --timeout 60`.
3. В **Environment** добавьте: `DATABASE_URL` (из БД), `SECRET_KEY` (сгенерируйте),
   `FLASK_APP=app.py`.
4. После деплоя → **Shell** → `flask --app app.py create-user admin пароль`.

### Переменные окружения
| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | строка подключения PostgreSQL (на Render подставляется автоматически) |
| `SECRET_KEY` | ключ для подписи сессий (сгенерируйте случайный) |
| `FLASK_APP` | `app.py` |
| `PYTHON_VERSION` | `3.11.9` |

---

## Создание новых пользователей
Через Shell веб-сервиса (или локально):
```bash
flask --app app.py create-user ivan secretpass --display "Иван"
```

## Бэкап данных
На Render используйте функцию **Download dump** в разделе базы данных.
Локально — `pg_dump inventory > backup.sql`.

## Резюме для не-технического пользователя
Чтобы запустить в интернете, вам (или разработчику) нужно:
1. Положить код на GitHub.
2. На Render создать сервис из этого репозитория (БД создастся автоматически).
3. Создать логин/пароль командой.
4. Раздать команде URL + логин/пароль.
