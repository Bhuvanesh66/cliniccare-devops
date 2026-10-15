from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ClinicCare API"
    app_version: str = "1.0.0"
    # Commit SHA baked into the image by CI, so a running pod can be traced back to source.
    git_sha: str = "local"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://cliniccare:cliniccare@localhost:5432/cliniccare"
    # "Today" on the dashboard is the clinic's local day, not the UTC day.
    clinic_timezone: str = "Asia/Kolkata"
    seed_demo_data: bool = False
    migration_wait_seconds: int = 90


settings = Settings()
