# Foodgram

**Foodgram** — сервис публикации и управления рецептами. Пользователи могут публиковать рецепты, добавлять их в избранное, корзину покупок, подписываться на авторов и скачивать список покупок. Проект разворачивается с помощью Docker.

---

## Состав проекта

* **Backend** — Django + DRF + PostgreSQL
* **Frontend** — React SPA
* **Nginx** — прокси-сервер
* **PostgreSQL** — СУБД

---

## Как запустить проект через Docker

### 1. Клонируйте репозиторий:

```bash
git clone <your_repo_url>
cd <repo_dir>
```

### 2. Создайте файл `.env` в корне проекта:

```ini
# .env
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=foodgram_db
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
DB_HOST=db
DB_PORT=5432

CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
```

### 3. Соберите и запустите контейнеры:

```bash
docker-compose up -d --build
```

### 4. Проверьте контейнеры:

```bash
docker ps
```

### 5. Примените миграции и загрузите данные:

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser  
docker-compose exec backend python manage.py load_ing
```

---

## очки доступа

| URL                                                                              | Описание                         |
| -------------------------------------------------------------------------------- | -------------------------------- |
| [http://localhost/admin/](http://localhost/admin/)                               | Админка Django                   |
| [http://localhost/api/](http://localhost/api/)                                   | API приложения                   |
| [http://localhost/api/auth/token/login/](http://localhost/api/auth/token/login/) | Получение токена                 |
| [http://localhost/api/users/me/](http://localhost/api/users/me/)                 | Профиль текущего юзера           |
| [http://localhost/api/docs/](http://localhost/api/docs/)                         | Документация API (swagger/redoc) |

---

## Структура проекта

```
foodgram-st-main/
├── backend/
│   ├── api/
│   ├── foodgram/            # Настройки Django
│   ├── formulas/            # Приложение рецептов
│   ├── users/               # Пользователи
│   └── manage.py            
├── frontend/
│   ├── Dockerfile
│   └── build/               # Статичные файлы
├── data/
│   └── ingredients.json     # Файл ингредиентов
├── infra/
│   └── nginx.conf
├── docker-compose.yml
├── .env
```

---

## Полезные команды

```bash
docker-compose exec backend python manage.py collectstatic 

docker-compose logs backend 

docker-compose down -v 
```

---

## Автор

**Савчук Антон** создан для учебных и демонстрационных целей.

