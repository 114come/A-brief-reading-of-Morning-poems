from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Master DB
    MASTER_DB_HOST: str = "localhost"
    MASTER_DB_PORT: int = 3306
    MASTER_DB_USER: str = "root"
    MASTER_DB_PASSWORD: str = ""
    MASTER_DB_NAME: str = "lowcode_master"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    @property
    def MASTER_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MASTER_DB_USER}:{self.MASTER_DB_PASSWORD}"
            f"@{self.MASTER_DB_HOST}:{self.MASTER_DB_PORT}/{self.MASTER_DB_NAME}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
