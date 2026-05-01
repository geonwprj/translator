import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from translator.configs.base import settings

class DatabaseClient:
    def __init__(self):
        # Ensure the database directory exists
        db_path = os.path.abspath(settings.db_path)
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)

        self.database_url = f"sqlite:///{db_path}"
        self.engine = create_engine(
            self.database_url, 
            connect_args={"check_same_thread": False},
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        self.Base = declarative_base()

    def init_db(self):
        """Initialize the database by creating all tables."""
        from translator.models.main import TranslationTask, TranslationChunk # Ensure models are registered
        self.Base.metadata.create_all(bind=self.engine)

    def get_db(self):
        """Dependency for FastAPI routes to get a database session."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

# Export a singleton instance
db_client = DatabaseClient()
