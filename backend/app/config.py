"""
Centralized application settings, loaded from environment variables.

Never hardcode secrets here — this module only defines *how* settings are
loaded, the actual values come from the environment (.env locally, the
platform's env var UI in production).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    frontend_url: str = "http://localhost:5173"
    # bcrypt cost factor. 12 is a sane production default; tests set 4 (the
    # minimum) so the suite is not dominated by password hashing.
    bcrypt_rounds: int = 12


settings = Settings()
