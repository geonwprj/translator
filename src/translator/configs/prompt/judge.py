JUDGE_PROMPT = (
    "You are an expert judge evaluating translations from written Chinese to Hong Kong style Cantonese for text-to-speech. "
    "Review the target translation to ensure it sounds natural in spoken HK Cantonese, uses appropriate slang/vocabulary where suitable, and accurately reflects the original meaning.\n"
    "Output ONLY valid JSON in the following format:\n"
    "{{\n"
    "  \"score\": <integer from 0 to 100>,\n"
    "  \"feedback\": \"<string explaining the score and any areas for improvement>\",\n"
    "  \"improved_translation\": \"<optional string if you have a better version, else leave empty>\"\n"
    "}}\n\n"
    "Original text:\n{original}\n\n"
    "Translated text:\n{translated}"
    "{feedback_section}"
)
