import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from translator.clients.database import db_client
from translator.routes import translation
from translator.configs.base import settings

# Configure global logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

logger = logging.getLogger("translator")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application-scoped resources."""
    # Ensure db tables are created
    db_client.init_db()
    yield

app = FastAPI(
    title="translator",
    description="Novel translation service from written Chinese to HK Cantonese for TTS.",
    version="0.1.5",
    root_path=settings.root_path,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(translation.router, prefix="/api/v1")

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "translator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
