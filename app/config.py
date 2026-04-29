from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dashboard.db"

    # Sessions
    secret_key: str = "change-me-in-production-use-a-long-random-string"
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days

    # Public site (used in email links and Open Graph tags)
    site_url: str = "http://localhost:8000"
    site_name: str = "Event Dashboard"

    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = "Event Dashboard <onboarding@resend.dev>"

    # LinkedIn (optional auto-posting)
    linkedin_access_token: str = ""
    linkedin_organization_urn: str = ""  # e.g. "urn:li:organization:12345"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
