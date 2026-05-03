from pydantic_settings import BaseSettings, SettingsConfigDict

class LLMSettings(BaseSettings):
    host: str = "localhost"
    port: int = 80
    secure: bool = False
    api_key: str = ""
    translate_model: str = "translategemma-speed"
    judge_model: str = "gemma-4-31b"
    judge_model_fallback: str = ""
    judge_model_local: str = ""
    cooldown: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        extra="ignore",
    )

llm_settings = LLMSettings()
