# Backend FastAPI (staging). O frontend Streamlit é alojado à parte (Streamlit Community Cloud).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Bibliotecas de sistema do WeasyPrint (relatórios PDF)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry>=2,<3"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY backend ./backend
COPY shared ./shared

RUN useradd --create-home appuser
USER appuser

# O Render define PORT; a API tem de escutar em 0.0.0.0 dentro do contentor
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
