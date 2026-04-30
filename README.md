# Translator Service

A robust translation service with multi-stage review and chunking support, powered by LiteLLM.

## Features

- **Asynchronous Translation**: Handles long-running translation tasks in the background.
- **Smart Chunking**: Automatically splits large texts into manageable chunks for better translation quality.
- **Multi-Stage Review**: Each translated chunk is reviewed by a "Judge" model to ensure accuracy and consistency.
- **Webhook Support**: Notifies external services upon task completion.
- **SQLite Persistence**: Stores task states and results reliably.

## Getting Started

### Prerequisites

- Python 3.10+
- `uv` for dependency management
- Access to an LLM provider (via LiteLLM)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/OWNER/translator.git
   cd translator
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp .env.sample .env
   # Edit .env with your settings
   ```

### Running the Service

```bash
uv run python -m translator.main
```

## Configuration

The service is configured via environment variables. See `.env.sample` for a complete list.

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_HOST` | Host to bind the API server | `0.0.0.0` |
| `API_PORT` | Port for the API server | `8000` |
| `DB_PATH` | Path to the SQLite database | `./data/translator.db` |

### LLM Settings (LiteLLM)

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_HOST` | LiteLLM proxy host | `llm.example.com` |
| `LLM_API_KEY` | API key for LiteLLM | `sk-...` |
| `LLM_TRANSLATE_MODEL` | Model used for translation | `gpt-4` |
| `LLM_JUDGE_MODEL` | Model used for reviewing | `gpt-4` |

### Translation Logic

- `TRANSLATE_CHUNK_MAX_CHARS`: Maximum characters per chunk (default: 1000).
- `TRANSLATE_SMALLEST_CHUNK`: Smallest chunk size when retrying failures (default: 300).
- `TRANSLATE_THRESHOLD_SCORE`: Minimum score required from the Judge model (default: 80).

## Deployment

A `Dockerfile` and `docker-compose.yaml` are provided for containerized deployment.

```bash
docker compose up -d
```

## License

MIT
