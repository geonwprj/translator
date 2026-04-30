from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    server_host: str = "0.0.0.0"
    api_port: int = 8000
    webui_port: int = 3000
    cors_origins: str = "*"
    server_mode: str = "development"
    log_level: str = "INFO"
    temp_path: str = "./tmp"
    db_path: str = "./data/translator.db"
    root_path: str = ""
    
    llm_host: str = "localhost"
    llm_port: int = 80
    llm_secure: bool = False
    llm_api_key: str = ""
    llm_translate_model: str = "translategemma-speed"
    llm_judge_model: str = "gemma-4-31b"
    
    translate_chunk_max_chars: int = 1000
    translate_smallest_chunk: int = 400
    translate_max_review_cycle: int = 3
    translate_threshold_score: int = 80
    translate_small_chunk_score: int = 60
    translate_small_chunk_size: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
