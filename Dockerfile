FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}"]
