from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TranslateRequest(BaseModel):
    text: str
    webhook_url: Optional[str] = None

class TranslateResponse(BaseModel):
    task_id: str

class TranslationChunkSchema(BaseModel):
    id: str
    chunk_index: int
    status: str
    score: Optional[float] = None
    review_cycle: int
    created_at: datetime
    updated_at: datetime

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    chunks: List[TranslationChunkSchema]
    webhook_url: Optional[str] = None
    translated_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class TaskSummarySchema(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

class TaskListResponse(BaseModel):
    tasks: List[TaskSummarySchema]

class RerunResponse(BaseModel):
    status: str
    message: str

class ChunkDetailResponse(TranslationChunkSchema):
    task_id: str
    original_text: str
    translated_text: Optional[str] = None
    failure_reason: Optional[str] = None
