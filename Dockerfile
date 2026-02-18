FROM python:3.14-rc-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# uv
RUN pip install --no-cache-dir uv

# зависимости
COPY pyproject.toml uv.lock* /app/
RUN uv sync --frozen --no-dev

# код
COPY src /app/src

# чтобы импорты были "from app..."
ENV PYTHONPATH=/app/src

CMD ["uv", "run", "python", "-m", "app.main"]
