from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_USERNAME: str = "elastic"
    ES_PASSWORD: str = ""
    ES_VERIFY_CERTS: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    WINDOW_MINUTES: int = 5
    MODEL_DIR: str = "backend/models/saved"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
