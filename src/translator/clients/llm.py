import json
import logging
import asyncio
import time
from litellm import acompletion
from litellm.exceptions import RateLimitError
from translator.configs.llm import llm_settings
from translator.configs.prompt.translate import TRANSLATE_PROMPT
from translator.configs.prompt.judge import JUDGE_PROMPT

logger = logging.getLogger(__name__)

# Global state for cooldown
_cooldown_until: float = 0
_cooldown_lock = asyncio.Lock()

async def _handle_cooldown():
    """Checks if cooldown is active and waits if necessary."""
    global _cooldown_until
    async with _cooldown_lock:
        now = time.time()
        if now < _cooldown_until:
            wait_time = _cooldown_until - now
            logger.warning(f"LLM Cooldown active. Waiting for {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)

def _set_cooldown():
    """Sets the cooldown period."""
    global _cooldown_until
    _cooldown_until = time.time() + llm_settings.cooldown
    logger.error(f"LLM Rate Limit (429) hit. Cooldown set for {llm_settings.cooldown} seconds.")

async def translate_chunk(text: str, previous_translation: str = None, feedback: str = None) -> str:
    """Uses translator LLM to translate written Chinese to HK Cantonese."""
    await _handle_cooldown()
    
    api_base = f"http://{llm_settings.host}:{llm_settings.port}"
    if llm_settings.secure:
        api_base = f"https://{llm_settings.host}:{llm_settings.port}"

    retry_section = ""
    if previous_translation and feedback:
        retry_section = f"\n\nPrevious Version:\n{previous_translation}\n\nCritique/Feedback:\n{feedback}\nPlease provide an improved version addressing the above feedback."

    prompt = TRANSLATE_PROMPT.format(text=text, retry_section=retry_section)

    try:
        response = await acompletion(
            model=llm_settings.translate_model if "/" in llm_settings.translate_model else f"openai/{llm_settings.translate_model}",
            messages=[{"role": "user", "content": prompt}],
            api_base=api_base,
            api_key=llm_settings.api_key,
        )
        content = response.choices[0].message.content
        logger.info(f"Translation result (first 100 chars): {content[:100] if content else 'NONE'}")
        return content.strip() if content else ""
    except RateLimitError:
        _set_cooldown()
        raise
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise

# State for judge fallback cooldowns
_judge_primary_cooldown_until: float = 0
_judge_fallback_cooldown_until: float = 0

async def judge_chunk(original: str, translated: str, failure_feedback: str = None) -> dict:
    """Uses judge LLM to review the translation and output JSON."""
    global _judge_primary_cooldown_until, _judge_fallback_cooldown_until
    await _handle_cooldown()
    
    api_base = f"http://{llm_settings.host}:{llm_settings.port}"
    if llm_settings.secure:
        api_base = f"https://{llm_settings.host}:{llm_settings.port}"

    feedback_section = ""
    if failure_feedback:
        feedback_section = f"\n\nPrevious Failure Feedback:\n{failure_feedback}\nPlease ensure the new translation addresses these issues."

    prompt = JUDGE_PROMPT.format(
        original=original,
        translated=translated,
        feedback_section=feedback_section
    )

    logger.info(f"Judging translation (first 100 chars): {translated[:100] if translated else 'EMPTY'}")
    
    now = time.time()
    models_to_try = []
    
    # 1. Primary Model
    if now > _judge_primary_cooldown_until:
        models_to_try.append(llm_settings.judge_model)
    else:
        logger.info("Primary judge model is on cooldown. Skipping.")

    # 2. Fallback Model
    if llm_settings.judge_model_fallback:
        if now > _judge_fallback_cooldown_until:
            if llm_settings.judge_model_fallback not in models_to_try:
                models_to_try.append(llm_settings.judge_model_fallback)
        else:
            logger.info("Fallback judge model is on cooldown. Skipping.")

    # 3. Local Model (Tertiary)
    if llm_settings.judge_model_local:
        if llm_settings.judge_model_local not in models_to_try:
            models_to_try.append(llm_settings.judge_model_local)

    last_exception = None
    for i, model_name in enumerate(models_to_try):
        try:
            model_full_name = model_name if "/" in model_name else f"openai/{model_name}"
            # Log if we are not using the primary model
            if model_name != llm_settings.judge_model:
                logger.warning(f"Using alternate model: {model_name}")

            response = await acompletion(
                model=model_full_name,
                messages=[{"role": "user", "content": prompt}],
                api_base=api_base,
                api_key=llm_settings.api_key,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            logger.info(f"Judge raw content: {content}")
            if content is None:
                return {"score": 0, "feedback": "Judge LLM returned null content"}
                
            content = content.strip()
            
            # In case the model returns markdown JSON blocks
            if content.startswith("```json"):
                content = content.replace("```json", "", 1)
                if content.endswith("```"):
                    content = content[:-3]
            
            return json.loads(content)

        except RateLimitError as e:
            last_exception = e
            if model_name == llm_settings.judge_model:
                _judge_primary_cooldown_until = time.time() + llm_settings.cooldown
                logger.warning(f"Primary judge model hit rate limit. Cooldown set for {llm_settings.cooldown}s.")
            elif model_name == llm_settings.judge_model_fallback:
                _judge_fallback_cooldown_until = time.time() + llm_settings.cooldown
                logger.warning(f"Fallback judge model hit rate limit. Cooldown set for {llm_settings.cooldown}s.")
            
            # If this is the last model we can try, set global cooldown
            if i == len(models_to_try) - 1:
                _set_cooldown()
                raise
            # Otherwise, loop will continue to next model
            continue
        except Exception as e:
            logger.error(f"Judge failed on model {model_name}: {e}")
            # Default failing score if json decode errors or API fails
            return {"score": 0, "feedback": f"API or JSON Parse Error: {str(e)}"}
    
    if last_exception:
        raise last_exception
    return {"score": 0, "feedback": "Judge failed: No models available"}
