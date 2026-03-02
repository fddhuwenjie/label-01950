"""
Application configuration module.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    # Application
    APP_NAME: str = "SQLFluff LSP Server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100
    
    # SQLFluff
    DEFAULT_DIALECT: str = "ansi"
    SUPPORTED_DIALECTS: List[str] = ["ansi", "sparksql", "hive"]
    LINT_TIMEOUT: float = 5.0
    
    # Performance
    DEBOUNCE_DELAY_MS: int = 300
    MAX_DOCUMENT_SIZE: int = 1024 * 1024  # 1MB


settings = Settings()
