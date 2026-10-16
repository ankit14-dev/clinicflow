from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClinicFlow API"
    # CI passes the git commit SHA so the UI can show exactly which build is running
    app_version: str = "dev"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://clinicflow:clinicflow@localhost:5432/clinicflow"
    # comma separated list; "*" only for local development
    cors_origins: str = "*"
    # "today" on the dashboard means today at the clinic, not today in UTC
    clinic_timezone: str = "Asia/Kolkata"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
