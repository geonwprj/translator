TRANSLATE_PROMPT = (
    "You are an expert translator. "
    "Translate the following written Chinese text into Hong Kong style Cantonese suitable for text-to-speech (TTS) audio book generation. "
    "Maintain the exact original paragraph spacing and structure. "
    "Only output the translated text, no additional comments.\n\n"
    "Original Text:\n{text}"
    "{retry_section}"
)
