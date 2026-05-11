from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str = "sqlite:///./dashboard.db"

    secret_key: str = "change-me-in-production-use-a-long-random-string"
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days

    site_name: str = "Event Dashboard"

    # Comma-separated allowlist of admin emails permitted to request magic links.
    # Empty by default — set ADMIN_EMAILS in .env. v2 replaces this with an
    # org_membership query (decisions.md Q5 / Q6; PRD §7 route-group pattern).
    admin_emails_csv: str = Field(default="", alias="ADMIN_EMAILS")

    magic_link_ttl_minutes: int = 15

    @property
    def admin_emails(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails_csv.split(",") if e.strip()]


settings = Settings()
