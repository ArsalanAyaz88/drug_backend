from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "DrugGenix API"
    APP_VERSION: str = "0.1.0"

    # Security
    JWT_SECRET_KEY: str = Field("change-me", description="Secret key for JWT")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./druggenix.db",
        description="SQLAlchemy database URL. Use Postgres in production.",
    )

    # Storage
    STORAGE_DIR: str = "storage"
    PROTEINS_DIR: str = "storage/proteins"

    # External tools / docking (optional; can also come from DB settings)
    VINA_PATH: Optional[str] = None
    OBABEL_PATH: Optional[str] = None
    VINA_EXHAUSTIVENESS: Optional[str] = None
    VINA_CENTER: Optional[str] = None
    VINA_SIZE: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
