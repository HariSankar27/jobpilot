from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    llm_provider: str = "google_genai"
    llm_model: str = "gemini-2.5-flash"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    db_connect_timeout_s: int = 10
    monthly_budget_usd: float = 20.0


settings = Settings()
