from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
from translator.clients.database import db_client
from translator.models.main import TranslationTask, TranslationChunk
from translator.models.schemas import (
    TranslateRequest, 
    TranslateResponse, 
    TaskStatusResponse, 
    TranslationChunkSchema,
    TaskListResponse,
    TaskSummarySchema,
    ChunkDetailResponse,
    RerunResponse
)
from translator.workers.translation import split_text_into_chunks, process_full_task, process_translation_chunk
from translator.configs.base import settings

router = APIRouter()

@router.post("/translate", response_model=TranslateResponse)
async def submit_translation(
    request: TranslateRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_client.get_db)
):
    text_chunks = split_text_into_chunks(request.text, settings.translate_chunk_max_chars)
    
    task = TranslationTask(
        original_text=request.text, 
        status="pending",
        webhook_url=request.webhook_url
    )
    db.add(task)
    db.flush() # flush to get task.id

    for i, chunk_text in enumerate(text_chunks):
        chunk = TranslationChunk(
            task_id=task.id,
            chunk_index=i,
            original_text=chunk_text,
            status="pending"
        )
        db.add(chunk)
    
    db.commit()

    background_tasks.add_task(process_full_task, task.id)
    return TranslateResponse(task_id=task.id)


@router.get("/translate", response_model=TaskListResponse)
def list_tasks(db: Session = Depends(db_client.get_db)):
    tasks = db.query(TranslationTask).order_by(TranslationTask.created_at.desc()).all()
    return TaskListResponse(
        tasks=[
            TaskSummarySchema(
                id=t.id,
                status=t.status,
                created_at=t.created_at,
                updated_at=t.updated_at
            ) for t in tasks
        ]
    )


@router.get("/translate/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str, db: Session = Depends(db_client.get_db)):
    task = db.query(TranslationTask).filter(TranslationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    chunks = db.query(TranslationChunk).filter(TranslationChunk.task_id == task.id).order_by(TranslationChunk.chunk_index).all()
    
    chunk_schemas = [
        TranslationChunkSchema(
            id=c.id,
            chunk_index=c.chunk_index,
            status=c.status,
            score=c.score,
            review_cycle=c.review_cycle,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in chunks
    ]

    combined_text = None
    if task.status == "completed":
        combined_text = "\n\n".join([c.translated_text for c in chunks if c.translated_text])

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        webhook_url=task.webhook_url,
        chunks=chunk_schemas,
        translated_text=combined_text,
        created_at=task.created_at,
        updated_at=task.updated_at
    )

@router.get("/translate/{task_id}/chunks/{chunk_id}", response_model=ChunkDetailResponse)
def get_chunk_detail(task_id: str, chunk_id: str, db: Session = Depends(db_client.get_db)):
    chunk = db.query(TranslationChunk).filter(TranslationChunk.id == chunk_id, TranslationChunk.task_id == task_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    return ChunkDetailResponse(
        id=chunk.id,
        task_id=chunk.task_id,
        chunk_index=chunk.chunk_index,
        status=chunk.status,
        score=chunk.score,
        review_cycle=chunk.review_cycle,
        original_text=chunk.original_text,
        translated_text=chunk.translated_text,
        failure_reason=chunk.failure_reason,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at
    )


@router.post("/translate/{task_id}/rerun", response_model=RerunResponse)
async def rerun_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_client.get_db)
):
    task = db.query(TranslationTask).filter(TranslationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    chunks = db.query(TranslationChunk).filter(TranslationChunk.task_id == task.id).all()
    failed_chunks = [c for c in chunks if c.status == "failed" or (c.status == "completed" and c.score is not None and c.score < settings.translate_threshold_score)]
    
    if not failed_chunks:
        return RerunResponse(status="skipped", message="All chunks are completed successfully. Nothing to rerun.")
    
    for c in failed_chunks:
        c.status = "pending"
        c.review_cycle = 0
        c.score = None
        c.failure_reason = None
    
    task.status = "translating"
    db.commit()
    
    background_tasks.add_task(process_full_task, task.id)
    
    return RerunResponse(status="queued", message=f"Queued task {task_id} for rerun of failed chunks.")

@router.post("/translate/{task_id}/chunks/{chunk_id}/rerun", response_model=RerunResponse)
async def rerun_chunk(
    task_id: str,
    chunk_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_client.get_db)
):
    chunk = db.query(TranslationChunk).filter(TranslationChunk.id == chunk_id, TranslationChunk.task_id == task_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    if chunk.status == "completed" and chunk.score is not None and chunk.score >= settings.translate_threshold_score:
        return RerunResponse(status="skipped", message="Chunk already completed successfully. To force, modify status directly (not available via API).")

    chunk.status = "pending"
    chunk.review_cycle = 0
    chunk.score = None
    chunk.failure_reason = None
    
    task = db.query(TranslationTask).filter(TranslationTask.id == task_id).first()
    if task:
        task.status = "translating"
    
    db.commit()
    
    background_tasks.add_task(process_translation_chunk, chunk.id)
    
    return RerunResponse(status="queued", message=f"Queued chunk {chunk_id} for rerun.")
