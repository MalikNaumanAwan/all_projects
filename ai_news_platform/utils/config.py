# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """configurations"""

    # Pydantic v2 config for env loading
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Define expected env variables
    pythonpath: str = Field(default="./")
    postgres_db: str = Field(..., validation_alias="POSTGRES_DB")
    postgres_user: str = Field(..., validation_alias="POSTGRES_USER")
    postgres_password: str = Field(..., validation_alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(..., validation_alias="POSTGRES_HOST")
    postgres_port: str = Field(..., validation_alias="POSTGRES_PORT")
    database_url: str = Field(..., validation_alias="DATABASE_URL")

    openai_api_key: str = Field(..., validation_alias="OPENAI_API_KEY")
    model: str = Field(default="llama3-8b-8192")
    openai_api_base: str = Field(default="https://api.groq.com/openai/v1")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")


# instantiate
settings = Settings()  # type: ignore
