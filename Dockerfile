FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

WORKDIR /app

# Dependencies first, in their own layer, so a code-only change doesn't reinstall them.
# --no-dev keeps mypy, pytest and ruff out of the production image.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# Then the application.
COPY . /app
RUN uv sync --frozen --no-dev --no-cache

# Don't run as root.
RUN useradd --system --no-create-home kuryana
USER kuryana

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0"]
