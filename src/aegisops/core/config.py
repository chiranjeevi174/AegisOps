import json
from contextlib import suppress
from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AegisOps"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices(
            "environment", "app_env", "ENVIRONMENT", "APP_ENV"
        ),
    )
    debug: bool = False
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    alertmanager_webhook_token: SecretStr = SecretStr("")

    prometheus_url: str = "http://localhost:9090"

    database_url: str = (
        "postgresql+asyncpg://aegisops:aegisops_local@localhost:5432/aegisops"
    )

    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"

    approval_validity_minutes: int = 1440
    execution_eligibility_minutes: int = 120
    enforce_separation_of_duties: bool = True
    human_auth_tokens: SecretStr = SecretStr("")
    live_diagnostics_enabled: bool = False
    verification_min_coverage_pct: float = 20.0
    verification_max_allowed_gap_seconds: int = 300

    # Security & Persona Restrictions
    enable_dev_persona_switching: bool = True

    # Session & CSRF Protection
    session_cookie_name: str = "aegisops_session"
    csrf_cookie_name: str = "aegisops_csrf"
    session_max_age_seconds: int = 28800  # 8-hour bounded session
    session_cookie_secure: bool = False
    csrf_secret_key: SecretStr = SecretStr(
        "aegisops-default-csrf-secret-key-change-in-prod"
    )

    # Network Security & Proxies
    cors_allowed_origins: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://testserver",
    ]
    trusted_proxies: list[str] | str = ["127.0.0.1", "::1"]
    enable_hsts: bool = False

    @field_validator("cors_allowed_origins", "trusted_proxies", mode="after")
    @classmethod
    def _split_str_to_list(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            clean = v.strip()
            if clean.startswith("[") and clean.endswith("]"):
                with suppress(json.JSONDecodeError, TypeError, ValueError):
                    parsed = json.loads(clean)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
            return [item.strip() for item in clean.split(",") if item.strip()]
        return v

    # Targeted Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 10
    rate_limit_webhook_per_minute: int = 60
    rate_limit_analysis_per_minute: int = 15
    rate_limit_decisions_per_minute: int = 30
    rate_limit_executions_per_minute: int = 30

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def dev_persona_switching_allowed(self) -> bool:
        return (
            self.environment.lower() == "development"
            and self.enable_dev_persona_switching
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
