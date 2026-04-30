import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from translator.clients.database import db_client

class TranslationTask(db_client.Base):
    __tablename__ = "translation_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, default="pending")  # pending, processing, completed, failed
    original_text = Column(Text, nullable=False)
    webhook_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("TranslationChunk", back_populates="task", cascade="all, delete-orphan")


class TranslationChunk(db_client.Base):
    __tablename__ = "translation_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("translation_tasks.id"))
    chunk_index = Column(Integer, nullable=False)
    
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=True)
    
    score = Column(Float, nullable=True)
    review_cycle = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, translating, reviewing, completed, failed
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship("TranslationTask", back_populates="chunks")
