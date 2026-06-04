# Multiagent Sales Assistant

Саморазвивающийся интеллектуальный помощник для отдела продаж услуг ремонта квартир.

## Описание

Многоагентная система на базе LLM (LangChain / CrewAI) с PostgreSQL, автоматизирующая:
- обработку обращений клиентов;
- формирование персонализированных рекомендаций менеджеру;
- подготовку коммерческих предложений;
- прогнозирование вероятности заключения сделки;
- самообучение на основе накопленного опыта.

## Стек технологий

| Слой | Технология |
|------|-----------|
| Язык | Python 3.11+ |
| API | FastAPI |
| Агенты | LangChain + CrewAI |
| LLM | OpenAI API / локальные модели (Hugging Face) |
| БД | PostgreSQL 15 + SQLAlchemy (async) + asyncpg |
| Контейнеризация | Docker + docker-compose |

## Структура проекта

```
multiagent-sales-assistant_bloc/
├── src/
│   ├── agents/          # Интеллектуальные агенты
│   │   ├── appeal_agent.py        # Агент обработки обращений
│   │   ├── recommendation_agent.py # Агент рекомендаций
│   │   ├── offer_agent.py         # Агент КП
│   │   ├── prediction_agent.py    # Агент прогнозирования
│   │   └── self_learning_agent.py # Агент самообучения
│   ├── orchestrator/    # Оркестратор (LangChain / CrewAI)
│   ├── database/        # ORM-модели и сессия БД
│   ├── llm/             # LLM-клиент и построитель промптов
│   └── api/             # FastAPI-приложение
├── migrations/          # SQL-миграции
├── tests/               # Тесты
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/IlyaAgoshkov/multiagent-sales-assistant_bloc.git
cd multiagent-sales-assistant_bloc
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
# Отредактировать .env: вставить OPENAI_API_KEY и параметры PostgreSQL
```

### 3. Запустить через Docker Compose

```bash
docker-compose up --build
```

### 4. Применить миграции

```bash
docker-compose exec app python -m src.database.init_db
```

API будет доступно по адресу: `http://localhost:8000`  
Документация (Swagger): `http://localhost:8000/docs`

## Запуск без Docker

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt

# Запустить PostgreSQL и создать БД вручную:
psql -U postgres -c "CREATE DATABASE sales_assistant;"
psql -U postgres -d sales_assistant -f migrations/init.sql

uvicorn src.api.main:app --reload
```

## Переменные окружения

| Переменная | Описание |
|-----------|---------|
| `DATABASE_URL` | URL подключения к PostgreSQL |
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `LLM_MODEL` | Название LLM-модели (default: `gpt-4o-mini`) |
| `SECRET_KEY` | Секрет для JWT-токенов |

## Автор

Агошков И.А., группа ПМ-51  
КубГУ, 2026
