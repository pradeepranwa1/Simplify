"""
ENV variable setup inside application
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================ Team Matcher Server ============================

# You may modify this file as needed. All environment variables should be set here.

# =============================================================================


class Settings(BaseSettings):
    """
    Reads env variables from .env file and set values inside application for quick access
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # Secret key for optional JWT authentication challenge
    AUTH_SECRET_KEY: str
    MOCK_FLAKY_ENDPOINT: str
    REDIS_URL: str
    TMP_USERNAME_FOR_AUTH: str
    TMP_HASHED_PASSWORD_FOR_AUTH: str
    AUTH_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    CONSOLE_LOG_LEVEL: str


@lru_cache
def get_settings():
    """
    Caching ENV variables using lru_cache that makes it a Singleton
    """
    return Settings()

settings = get_settings()
