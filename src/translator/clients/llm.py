import json
import logging
from litellm import acompletion
from translator.configs.base import settings
from translator.configs.prompt.translate import TRANSLATE_PROMPT
from translator.configs.prompt.judge import JUDGE_PROMPT

logger = logging.getLogger(__name__)

async def translate_chunk(text: str, previous_translation: str = None, feedback: str = None) -> str:
    """Uses translator LLM to translate written Chinese to HK Cantonese."""
    api_base = f"http://{settings.llm_host}:{settings.llm_port}"
    if settings.llm_secure:
        api_base = f"https://{settings.llm_host}:{settings.llm_port}"

    retry_section = ""
    if previous_translation and feedback:
        retry_section = f"\n\nPrevious Version:\n{previous_translation}\n\nCritique/Feedback:\n{feedback}\nPlease provide an improved version addressing the above feedback."

    prompt = TRANSLATE_PROMPT.format(text=text, retry_section=retry_section)

    try:
        response = await acompletion(
            model=settings.llm_translate_model if "/" in settings.llm_translate_model else f"openai/{settings.llm_translate_model}",
            messages=[{"role": "user", "content": prompt}],
            api_base=api_base,
            api_key=settings.llm_api_key,
        )
        content = response.choices[0].message.content
        logger.info(f"Translation result (first 100 chars): {content[:100] if content else 'NONE'}")
        return content.strip() if content else ""
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise

async def judge_chunk(original: str, translated: str, failure_feedback: str = None) -> dict:
    """Uses judge LLM to review the translation and output JSON."""
    api_base = f"http://{settings.llm_host}:{settings.llm_port}"
    if settings.llm_secure:
        api_base = f"https://{settings.llm_host}:{settings.llm_port}"

    feedback_section = ""
    if failure_feedback:
        feedback_section = f"\n\nPrevious Failure Feedback:\n{failure_feedback}\nPlease ensure the new translation addresses these issues."

    prompt = JUDGE_PROMPT.format(
        original=original,
        translated=translated,
        feedback_section=feedback_section
    )

    logger.info(f"Judging translation (first 100 chars): {translated[:100] if translated else 'EMPTY'}")
    try:
        response = await acompletion(
            model=settings.llm_judge_model if "/" in settings.llm_judge_model else f"openai/{settings.llm_judge_model}",
            messages=[{"role": "user", "content": prompt}],
            api_base=api_base,
            api_key=settings.llm_api_key,
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
    except Exception as e:
        logger.error(f"Judge failed: {e}")
        # Default failing score if json decode errors or API fails
        return {"score": 0, "feedback": f"API or JSON Parse Error: {str(e)}"}
