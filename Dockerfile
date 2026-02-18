FROM python:3.14-rc-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* /app/
RUN uv sync --frozen --no-dev

COPY src /app/src

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "python", "-m", "app.main"]
