# ndbx-lab

`ndbx-lab` — это FastAPI-приложение для выполнения лабораторных работ по курсу NoSQL.

Проект запускается в Docker, использует Redis как внешнее хранилище и развивается по мере выполнения лабораторных работ. В текущем состоянии в проекте уже реализованы базовый health-check и работа с анонимными пользовательскими сессиями.

## Что есть в проекте

- FastAPI-приложение со `src`-структурой
- запуск через Docker Compose
- конфигурация через `.env.local`
- Redis как инфраструктурная зависимость
- Swagger UI для ручной проверки API
- Postman-коллекция для тестирования запросов

## Технологии

- Python
- FastAPI
- Redis
- Docker Compose

## Запуск

Перед запуском проверьте настройки в `.env.local`.

Запуск в фоне:

```bash
make run
```

Запуск с логами в текущем терминале:

```bash
make rund
```

Проверка статуса контейнеров:

```bash
make services
```

Остановка:

```bash
make stop
```

После запуска приложение доступно по адресу [http://localhost:8080](http://localhost:8080), Swagger UI — [http://localhost:8080/docs](http://localhost:8080/docs).

## Конфигурация

Проект использует `.env.local` как основной источник конфигурации.

Основные переменные окружения:

- `APP_HOST` — хост приложения
- `APP_PORT` — порт приложения
- `APP_USER_SESSION_TTL` — TTL пользовательской сессии
- `APP_USER_SESSION_CREATE_MAX_ATTEMPTS` — число попыток создания новой сессии
- `APP_USER_SESSION_STORE_RETRY_ATTEMPTS` — число повторов Redis-операций при конфликте записи
- `REDIS_HOST` — хост Redis
- `REDIS_PORT` — порт Redis
- `REDIS_PASSWORD` — пароль Redis
- `REDIS_DB` — номер Redis database

Если `REDIS_PASSWORD` задан, он используется и приложением, и контейнером Redis.

## Текущая функциональность

### `GET /health`

Проверка работоспособности сервиса.

Ответ:

```json
{"status":"ok"}
```

### `POST /session`

Endpoint для создания и обновления анонимной пользовательской сессии.

Сессии:

- хранятся в Redis
- используют cookie `X-Session-Id`
- имеют TTL
- сохраняются по ключу `sid:{session_id}`

## Архитектура

Приложение построено послойно, чтобы HTTP-часть, бизнес-логика и работа с Redis были разделены.

- `src/app/main.py` и `src/app/service.py` отвечают за создание FastAPI-приложения, загрузку конфигурации и инициализацию зависимостей в lifecycle
- `src/app/routers.py` и `src/app/api/` содержат HTTP-роуты и обработчики запросов
- `src/app/session/service.py` содержит бизнес-логику сессий: создать новую сессию или обновить существующую
- `src/app/session/store.py` изолирует работу с Redis: хранение, обновление TTL и запись метаданных сессии
- `src/app/session/bootstrap.py` собирает session-модуль и связывает service со store
- `src/app/user_session.py` содержит утилиты для cookie, sid и Redis key format

Поток запроса выглядит так:

1. HTTP-запрос приходит в handler.
2. Handler достает данные из cookie и обращается к session service.
3. Session service решает, нужно обновить существующую сессию или создать новую.
4. Session store выполняет операции в Redis.
5. Handler формирует HTTP-ответ и устанавливает cookie.

## Проверка API

### Swagger

Swagger UI доступен по адресу [http://localhost:8080/docs](http://localhost:8080/docs).

### curl

Пример запроса на создание сессии:

```bash
curl -i -c /tmp/ndbx.cookies -X POST http://localhost:8080/session
```

Пример повторного запроса с той же cookie:

```bash
curl -i -b /tmp/ndbx.cookies -X POST http://localhost:8080/session
```

Проверка health-check:

```bash
curl -i http://localhost:8080/health
```

### Postman

В проекте есть Postman-коллекция:

[api_tests_collection.json](src/tools/api_tests_collection.json)

Ее можно использовать для проверки:

- `POST /session`
- повторного `POST /session` с cookie
- `GET /health`

## Структура проекта

- `src/app/` — приложение и основная бизнес-логика
- `src/app/api/` — HTTP handlers
- `src/app/session/` — логика сессий и работа с Redis
- `src/tools/` — вспомогательные артефакты, включая Postman-коллекцию
- `docker-compose.yml` — запуск приложения и Redis
- `.env.local` — конфигурация окружения
- `Makefile` — команды для запуска и остановки проекта

## Назначение репозитория

Этот репозиторий используется как рабочий проект для лабораторных работ по NoSQL. По мере выполнения следующих лабораторных работ функциональность приложения может расширяться, а README и документация будут обновляться вместе с проектом.
