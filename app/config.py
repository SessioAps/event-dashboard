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

    # Backend platform service wiring (Phase E — sessio-align-grill decisions.md).
    # Base URL of the sessio-backend instance the api-client targets.
    # Required in any environment that exchanges/exercises the api-client.
    sessio_backend_base_url: str = Field(default="", alias="SESSIO_BACKEND_BASE_URL")

    # Long-lived AdminServiceToken used on POST /v1/admin/auth/exchange only.
    # Distinct from per-user bearers (which the backend mints in response to
    # the exchange). Rotation is an env-var swap + backend allowlist sync.
    sessio_admin_service_token: str = Field(default="", alias="SESSIO_ADMIN_SERVICE_TOKEN")

    # HTTP timeout for outbound backend calls. Conservative default; tighten
    # once we have real latency numbers.
    sessio_backend_timeout_seconds: float = 10.0

    @property
    def admin_emails(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails_csv.split(",") if e.strip()]


settings = Settings()
