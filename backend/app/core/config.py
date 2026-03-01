from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = "sql-ai-editor"
    log_level: str = "INFO"
    lsp_command: str = "sqlfluff"
    lsp_args: str = "lsp"
    lsp_startup_timeout_seconds: int = 10
    lsp_max_concurrent_sessions: int = 8
    database_url: str = "mysql+pymysql://sqlai:sqlai@mysql:3306/sqlai"

    model_config = SettingsConfigDict(env_prefix="SQLAI_", case_sensitive=False)


settings = AppSettings()
