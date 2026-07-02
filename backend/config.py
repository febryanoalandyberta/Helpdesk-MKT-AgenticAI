"""
Helpdesk MKT Agentic AI Automation
Configuration Module
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Helpdesk MKT Agentic AI"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    APP_SECRET_KEY: str = "dev-secret-key"
    DEBUG: bool = True

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "helpdesk_mkt"
    DB_USER: str = "mkt_user"
    DB_PASSWORD: str = "mkt_password"
    DATABASE_URL: str = "postgresql+asyncpg://mkt_user:mkt_password@localhost:5432/helpdesk_mkt"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Zammad
    ZAMMAD_URL: str = ""
    ZAMMAD_TOKEN: str = ""
    ZAMMAD_POLL_INTERVAL: int = 15

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_DEFAULT_GROUP_ID: str = ""

    # LLM — Multi-provider via LiteLLM (CrewAI)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini/gemini-2.0-flash"
    OLLAMA_MODEL: str = "ollama/llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # Primary LLM for agents (Gemini = cloud, Ollama = local)
    PRIMARY_LLM: str = "gemini"  # "gemini" or "ollama"
    OPENAI_API_KEY: str = ""  # kept for backward compat
    OPENAI_MODEL: str = "gpt-4o"  # kept for backward compat

    # JWT
    JWT_SECRET: str = "jwt-dev-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # Agent Settings
    TIER0_CONFIDENCE_THRESHOLD: int = 85
    TIER1_ESCALATION_TIMEOUT: int = 300
    MAX_CONCURRENT_AGENTS: int = 5

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
