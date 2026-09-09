"""Configuración centralizada de la aplicación."""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    ollama_host: str = Field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    ollama_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1"))
    gmail_credentials_path: Path = Field(
        default_factory=lambda: Path(os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"))
    )
    gmail_token_path: Path = Field(
        default_factory=lambda: Path(os.getenv("GMAIL_TOKEN_PATH", "token.json"))
    )
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/organizador.db")
    )
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


settings = Settings()