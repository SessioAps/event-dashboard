from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dashboard.db"

    # Sessions
    secret_key: str = "change-me-in-production-use-a-long-random-string"
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days

    site_name: str = "Event Dashboard"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
