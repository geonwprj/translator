FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONPATH=/app/src

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY .env.docker ./.env

# Install dependencies
RUN uv sync --frozen --no-dev

# Ensure data and log directories exist
RUN mkdir -p /app/data /app/log /app/tmp

# Expose port
EXPOSE 8000

# Set entrypoint
CMD ["uv", "run", "uvicorn", "translator.main:app", "--host", "0.0.0.0", "--port", "8000"]
