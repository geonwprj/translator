import logging
import re
import httpx
from sqlalchemy.orm import Session
from translator.configs.base import settings
from translator.clients.database import db_client
from translator.models.main import TranslationTask, TranslationChunk
from translator.clients.llm import translate_chunk, judge_chunk

logger = logging.getLogger("translator.workers.translation")

async def trigger_webhook(task_id: str, db: Session):
    task = db.query(TranslationTask).filter(TranslationTask.id == task_id).first()
    if not task or not task.webhook_url:
        return
    
    chunks = db.query(TranslationChunk).filter(TranslationChunk.task_id == task_id).order_by(TranslationChunk.chunk_index).all()
    combined_text = "\n\n".join([c.translated_text for c in chunks if c.translated_text])
    
    payload = {
        "task_id": task.id,
        "status": task.status,
        "translated_text": combined_text
    }
    
    logger.info(f"Triggering webhook for task {task_id} (status: {task.status}) to {task.webhook_url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(task.webhook_url, json=payload, timeout=30.0)
            response.raise_for_status()
            logger.info(f"Successfully sent webhook for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to send webhook for task {task_id}: {e}")

def split_text_into_chunks(text: str, max_chars: int) -> list[str]:
    delimiter = "\n\n"
    parts = text.split(delimiter)
    chunks = []
    current_chunk = []
    current_len = 0

    for part in parts:
        part_len = len(part) + (len(delimiter) if current_len > 0 else 0)
        if current_len + part_len > max_chars and current_chunk:
            chunks.append(delimiter.join(current_chunk))
            current_chunk = [part]
            current_len = len(part)
        else:
            current_chunk.append(part)
            current_len += part_len

    if current_chunk:
        chunks.append(delimiter.join(current_chunk))

    return chunks

def deduplicate_text(text: str) -> str:
    """Removes identical consecutive sentences/paragraphs."""
    if not text:
        return text
    lines = text.split("\n")
    new_lines = []
    prev_line = None
    for line in lines:
        stripped = line.strip()
        if stripped and stripped == prev_line:
            continue
        new_lines.append(line)
        if stripped:
            prev_line = stripped
    return "\n".join(new_lines)

def find_split_point(text: str) -> int:
    """Finds a natural split point in the text."""
    mid = len(text) // 2
    # 1. Try \n\n near mid
    nl_nl = text.find("\n\n", mid - 200, mid + 200)
    if nl_nl != -1:
        return nl_nl + 2
    
    # 2. Try sentence boundaries near mid
    pattern = r"[。！？]"
    search_start = max(0, mid - 200)
    search_end = min(len(text), mid + 200)
    matches = list(re.finditer(pattern, text[search_start:search_end]))
    if matches:
        best_match = min(matches, key=lambda m: abs(mid - (search_start + m.end())))
        return search_start + best_match.end()
    
    return mid

def handle_chunk_split(db: Session, chunk: TranslationChunk, reason: str = "Auto-split (too large or blocked)") -> bool:
    """Splits a chunk into two smaller chunks and re-indexes subsequent ones.
    
    Returns False if the chunk is at or below TRANSLATE_SMALLEST_CHUNK,
    preventing infinite splitting loops.
    """
    text = chunk.original_text
    smallest = settings.translate_smallest_chunk

    if len(text) <= smallest:
        logger.warning(
            f"Chunk {chunk.id} ({len(text)} chars) is at or below the smallest allowed size "
            f"({smallest} chars). Cannot split further."
        )
        return False

    split_at = find_split_point(text)
    part1 = text[:split_at].strip()
    part2 = text[split_at:].strip()

    if not part1 or not part2:
        logger.warning(f"Split resulted in empty part for chunk {chunk.id}. Aborting split.")
        return False

    logger.info(
        f"Splitting chunk {chunk.id} (index {chunk.chunk_index}, {len(text)} chars) "
        f"into two sub-chunks ({len(part1)} + {len(part2)} chars). Reason: {reason}"
    )
    
    # 1. Shift existing indices
    db.query(TranslationChunk).filter(
        TranslationChunk.task_id == chunk.task_id,
        TranslationChunk.chunk_index > chunk.chunk_index
    ).update({TranslationChunk.chunk_index: TranslationChunk.chunk_index + 1})

    # 2. Update current chunk to Part 1
    chunk.original_text = part1
    chunk.status = "pending"
    chunk.score = None
    chunk.review_cycle = 0
    chunk.translated_text = None
    chunk.failure_reason = reason

    # 3. Create new chunk for Part 2
    new_chunk = TranslationChunk(
        task_id=chunk.task_id,
        chunk_index=chunk.chunk_index + 1,
        original_text=part2,
        status="pending"
    )
    db.add(new_chunk)
    db.commit()
    return True

def get_effective_threshold(chunk_text_len: int) -> int:
    """Returns a relaxed score threshold for small chunks.
    
    Small chunks are penalized harder by the judge since a single
    mistake has proportionally more impact on the overall score.
    """
    if chunk_text_len <= settings.translate_small_chunk_size:
        return settings.translate_small_chunk_score
    return settings.translate_threshold_score

async def update_task_status(task_id: str, db: Session):
    """Consolidated logic to update task status based on its chunks and trigger webhook."""
    task = db.query(TranslationTask).filter(TranslationTask.id == task_id).first()
    if not task:
        return
    
    chunks = db.query(TranslationChunk).filter(TranslationChunk.task_id == task_id).all()
    if not chunks:
        return

    statuses = [c.status for c in chunks]
    any_failed = "failed" in statuses
    any_translating = "translating" in statuses
    any_reviewing = "reviewing" in statuses
    any_pending = "pending" in statuses
    all_completed = all(s == "completed" for s in statuses)
    
    old_status = task.status
    new_status = old_status

    if any_translating:
        new_status = "translating"
    elif any_reviewing:
        new_status = "reviewing"
    elif any_pending:
        new_status = "translating"
    elif any_failed:
        new_status = "failed"
    elif all_completed:
        new_status = "completed"
    else:
        new_status = "pending"
        
    if old_status != new_status:
        logger.info(f"Task {task_id} status changing: {old_status} -> {new_status}")
        task.status = new_status
        db.commit()
        
        # Trigger webhook when moving to a terminal state
        if new_status in ("completed", "failed") and old_status not in ("completed", "failed"):
            if task.webhook_url:
                await trigger_webhook(task.id, db)

async def process_translation_chunk(chunk_id: str, db: Session = None):
    """Process a single translation chunk independently in background."""
    logger.info(f"Starting processing for chunk {chunk_id}")
    
    # Use provided session or create a new one
    should_close = False
    if db is None:
        db = db_client.SessionLocal()
        should_close = True
        
    try:
        chunk = db.query(TranslationChunk).filter(TranslationChunk.id == chunk_id).first()
        if not chunk:
            return

        threshold = get_effective_threshold(len(chunk.original_text))
        if chunk.status == "completed" and chunk.score is not None and chunk.score >= threshold:
            logger.info(f"Chunk {chunk_id} already completed (score {chunk.score} >= threshold {threshold}). Skipping.")
            return

        chunk.status = "translating"
        db.commit()

        best_score = chunk.score or 0
        best_translation = chunk.translated_text
        failure_feedback = chunk.failure_reason

        while chunk.review_cycle < settings.translate_max_review_cycle:
            try:
                # 1. Translate (using previous best and feedback if available)
                new_translation = await translate_chunk(chunk.original_text, best_translation, failure_feedback)
                new_translation = deduplicate_text(new_translation)
                
                # 2. Judge
                chunk.status = "reviewing"
                db.commit()
                
                judge_result = await judge_chunk(chunk.original_text, new_translation, failure_feedback)
                new_score = judge_result.get("score", 0)
                new_feedback = judge_result.get("feedback", "")
                improved_translation = judge_result.get("improved_translation", "").strip()
                
                # 3. Handle auto-split on null content
                if new_feedback == "Judge LLM returned null content":
                    logger.warning(f"Null content detected for chunk {chunk.id}. Triggering auto-split.")
                    if handle_chunk_split(db, chunk, reason="Auto-split (null judge content)"):
                        return # Exit current worker; split chunks will be picked up by process_full_task

                # 4. Use improved translation if provided and current score is low
                if improved_translation and improved_translation != new_translation and new_score < threshold:
                    logger.info(f"Judge provided an improved version for chunk {chunk.id}. Swapping candidate.")
                    improved_translation = deduplicate_text(improved_translation)
                    # We'll re-judge it to be sure it's actually better
                    improved_judge = await judge_chunk(chunk.original_text, improved_translation, failure_feedback)
                    improved_score = improved_judge.get("score", 0)
                    if improved_score > new_score:
                        logger.info(f"Improved version score: {improved_score} > {new_score}. Accepting improvement.")
                        new_translation = improved_translation
                        new_score = improved_score
                        new_feedback = improved_judge.get("feedback", "")

                # 5. Evaluate and Rollback Logic
                if new_score > best_score:
                    logger.info(f"Chunk {chunk_id} achieved better score: {new_score} > {best_score}. Updating best version.")
                    best_score = new_score
                    best_translation = new_translation
                    
                    # Update DB with new best
                    chunk.translated_text = best_translation
                    chunk.score = best_score
                else:
                    logger.info(f"Chunk {chunk_id} new score {new_score} <= best score {best_score}. Rolling back to previous best version.")
                
                failure_feedback = new_feedback
                chunk.failure_reason = new_feedback
                chunk.review_cycle += 1
                db.commit()

                if best_score >= threshold:
                    chunk.status = "completed"
                    chunk.failure_reason = None
                    db.commit()
                    logger.info(f"Chunk {chunk_id} passed threshold ({best_score} >= {threshold}). Completed.")
                    break
            except Exception as e:
                logger.error(f"Error processing chunk {chunk.id}: {e}")
                chunk.review_cycle += 1
                chunk.failure_reason = str(e)
                db.commit()

        # --- Post-loop: handle max review cycles exhausted ---
        if chunk.status not in ("completed", "pending"):
            # Attempt to split the chunk into smaller pieces for re-processing
            chunk_len = len(chunk.original_text)
            reason = (
                f"Max review cycles ({settings.translate_max_review_cycle}) exhausted "
                f"with best score {best_score}/{threshold}"
            )

            if chunk_len > settings.translate_smallest_chunk:
                logger.info(
                    f"Chunk {chunk.id} ({chunk_len} chars) failed after max review cycles. "
                    f"Attempting to split for re-processing."
                )
                if handle_chunk_split(db, chunk, reason=reason):
                    return  # Split succeeded; sub-chunks are pending and will be picked up

            # Either chunk is too small to split, or split failed
            logger.error(
                f"Chunk {chunk.id} ({chunk_len} chars) permanently failed. "
                f"At or below smallest chunk size ({settings.translate_smallest_chunk} chars) "
                f"or split failed. Best score: {best_score}/{threshold}"
            )
            chunk.status = "failed"
            chunk.failure_reason = (
                f"{reason}. Chunk too small to split further "
                f"(size: {chunk_len}, min: {settings.translate_smallest_chunk})."
            )
            db.commit()

        # Update Task Status and trigger webhook if terminal
        await update_task_status(chunk.task_id, db)

    finally:
        if should_close:
            db.close()

async def process_full_task(task_id: str):
    """Processes all non-completed chunks in a task dynamically."""
    logger.info(f"Starting full task processing for {task_id}")
    db: Session = db_client.SessionLocal()
    try:
        task = db.query(TranslationTask).filter(TranslationTask.id == task_id).first()
        if not task:
            return

        task.status = "translating"
        db.commit()

        while True:
            # Query for the next chunk that needs processing
            chunk = db.query(TranslationChunk).filter(
                TranslationChunk.task_id == task_id,
                TranslationChunk.status.in_(["pending", "translating", "reviewing"])
            ).order_by(TranslationChunk.chunk_index.asc()).first()

            if not chunk:
                break

            await process_translation_chunk(chunk.id, db=db)

        # Final status check and potential webhook trigger
        await update_task_status(task_id, db)

    finally:
        db.close()
