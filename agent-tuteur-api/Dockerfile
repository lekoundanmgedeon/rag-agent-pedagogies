# Image unique servant l'API FastAPI et le worker ARQ (mêmes dépendances,
# entrée différente selon la commande passée par docker-compose).
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
COPY corpus ./corpus
COPY scripts ./scripts

RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "agent_tuteur.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
