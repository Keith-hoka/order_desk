# Multi-stage build for the order_desk extraction service.
FROM python:3.12-slim AS builder

# uv for fast, reproducible dependency install
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached unless the lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Then install the project itself
COPY src ./src
COPY README.md ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

WORKDIR /app
# Copy the resolved virtualenv and the source from the builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"

# Non-root user for the service
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "order_desk.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
