from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # App Settings
    APP_NAME: str = "Busy WhatsApp Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database Settings
    BDS_FILE_PATH: str = ""
    BDS_PASSWORD: str = "ILoveMyINDIA"
    ODBC_DRIVER: str = "Microsoft Access Driver (*.mdb, *.accdb)"
    
    # WhatsApp Provider Settings
    WHATSAPP_PROVIDER: str = "meta"  # meta, webhook, baileys (future)
    
    # Meta Settings
    META_API_VERSION: str = "v18.0"
    META_PHONE_NUMBER_ID: Optional[str] = None
    META_ACCESS_TOKEN: Optional[str] = None
    META_BUSINESS_ID: Optional[str] = None
    
    # Webhook Settings
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_AUTH_TOKEN: Optional[str] = None
    
    # Baileys Settings (WhatsApp Web via Node.js)
    BAILEYS_SERVER_URL: str = "http://localhost:3001"
    BAILEYS_ENABLED: bool = False
    BAILEYS_AUTO_START: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def database_connection_string(self) -> str:
        """Generate ODBC connection string for MS Access."""
        if not self.BDS_FILE_PATH:
            raise ValueError("BDS_FILE_PATH must be set in environment")
        
        return (
            f"DRIVER={{{self.ODBC_DRIVER}}};"
            f"DBQ={self.BDS_FILE_PATH};"
            f"PWD={self.BDS_PASSWORD};"
            f"ExtendedAnsiSQL=1;"
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
