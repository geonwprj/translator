TRANSLATE_PROMPT = (
    "You are an expert translator specializing in Cantonese.\n\n"
    "Task: Translate the following written Chinese text into natural Hong Kong style Cantonese suitable for text-to-speech (TTS).\n\n"
    "Requirements:\n"
    "1. Naturalness: Use spoken HK Cantonese (e.g., using '係' instead of '是', '嘅' instead of '的', etc.).\n"
    "2. Structure: Maintain the exact original paragraph spacing and structure.\n"
    "3. NO HALLUCINATIONS: Do not add any content that is not in the original text.\n"
    "4. NO REPETITIONS: Do not repeat sentences or provide multiple variations of the same sentence.\n"
    "5. Format: Only output the translated text. No commentary.\n\n"
    "Original Text:\n{text}"
    "{retry_section}"
)
