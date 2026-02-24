import json
import os
from pathlib import Path
from typing import Optional
from functools import lru_cache
from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    """Server configuration."""
    app_name: str = "Busy Whatsapp Bridge"
    app_version: str = "0.0.1"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseSettings(BaseModel):
    """Database configuration."""
    bds_file_path: str = ""
    bds_password: str = "ILoveMyINDIA"
    odbc_driver: str = "Microsoft Access Driver (*.mdb, *.accdb)"


class WhatsAppSettings(BaseModel):
    """WhatsApp provider configuration."""
    provider: str = "baileys"
    meta_api_version: str = "v18.0"
    meta_phone_number_id: Optional[str] = None
    meta_access_token: Optional[str] = None
    meta_business_id: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_auth_token: Optional[str] = None


class BaileysSettings(BaseModel):
    """Baileys configuration."""
    server_url: str = "http://localhost:3001"
    enabled: bool = False
    auto_start: bool = True


class LoggingSettings(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"


class ReminderSettings(BaseModel):
    """Payment reminder configuration."""
    enabled: bool = True
    provider: str = "meta"
    default_credit_days: int = 30
    schedule_enabled: bool = False
    schedule_frequency: str = "weekly"
    schedule_day: int = 1
    schedule_time: str = "10:00"
    schedule_timezone: str = "Asia/Kolkata"
    batch_size: int = 50
    delay_between_messages: int = 5


class Settings(BaseModel):
    """Application configuration."""
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    whatsapp: WhatsAppSettings = Field(default_factory=WhatsAppSettings)
    baileys: BaileysSettings = Field(default_factory=BaileysSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    reminders: ReminderSettings = Field(default_factory=ReminderSettings)

    @property
    def APP_NAME(self) -> str:
        return self.server.app_name
    
    @property
    def APP_VERSION(self) -> str:
        return self.server.app_version
    
    @property
    def DEBUG(self) -> bool:
        return self.server.debug
    
    @property
    def HOST(self) -> str:
        return self.server.host
    
    @property
    def PORT(self) -> int:
        return self.server.port
    
    @property
    def BDS_FILE_PATH(self) -> str:
        return self.database.bds_file_path
    
    @property
    def BDS_PASSWORD(self) -> str:
        return self.database.bds_password
    
    @property
    def ODBC_DRIVER(self) -> str:
        return self.database.odbc_driver
    
    @property
    def WHATSAPP_PROVIDER(self) -> str:
        return self.whatsapp.provider
    
    @property
    def META_API_VERSION(self) -> str:
        return self.whatsapp.meta_api_version
    
    @property
    def META_PHONE_NUMBER_ID(self) -> Optional[str]:
        return self.whatsapp.meta_phone_number_id
    
    @property
    def META_ACCESS_TOKEN(self) -> Optional[str]:
        return self.whatsapp.meta_access_token
    
    @property
    def META_BUSINESS_ID(self) -> Optional[str]:
        return self.whatsapp.meta_business_id
    
    @property
    def WEBHOOK_URL(self) -> Optional[str]:
        return self.whatsapp.webhook_url
    
    @property
    def WEBHOOK_AUTH_TOKEN(self) -> Optional[str]:
        return self.whatsapp.webhook_auth_token
    
    @property
    def BAILEYS_SERVER_URL(self) -> str:
        return self.baileys.server_url
    
    @property
    def BAILEYS_ENABLED(self) -> bool:
        return self.baileys.enabled
    
    @property
    def BAILEYS_AUTO_START(self) -> bool:
        return self.baileys.auto_start
    
    @property
    def LOG_LEVEL(self) -> str:
        return self.logging.level
    
    @property
    def LOG_FORMAT(self) -> str:
        return self.logging.format
    
    @property
    def REMINDER_ENABLED(self) -> bool:
        return self.reminders.enabled
    
    @property
    def REMINDER_PROVIDER(self) -> str:
        return self.reminders.provider
    
    @property
    def REMINDER_DEFAULT_CREDIT_DAYS(self) -> int:
        return self.reminders.default_credit_days
    
    @property
    def REMINDER_CONFIG_PATH(self) -> str:
        return str(get_appdata_path() / "data" / "reminder_config.json")
    
    @property
    def REMINDER_SCHEDULE_ENABLED(self) -> bool:
        return self.reminders.schedule_enabled
    
    @property
    def REMINDER_SCHEDULE_FREQUENCY(self) -> str:
        return self.reminders.schedule_frequency
    
    @property
    def REMINDER_SCHEDULE_DAY(self) -> int:
        return self.reminders.schedule_day
    
    @property
    def REMINDER_SCHEDULE_TIME(self) -> str:
        return self.reminders.schedule_time
    
    @property
    def REMINDER_SCHEDULE_TIMEZONE(self) -> str:
        return self.reminders.schedule_timezone
    
    @property
    def REMINDER_BATCH_SIZE(self) -> int:
        return self.reminders.batch_size
    
    @property
    def REMINDER_DELAY_BETWEEN_MESSAGES(self) -> int:
        return self.reminders.delay_between_messages
    
    @property
    def database_connection_string(self) -> str:
        """Generate ODBC connection string for MS Access."""
        if not self.BDS_FILE_PATH:
            raise ValueError("BDS_FILE_PATH must be set in configuration")
        
        return (
            f"DRIVER={{{self.ODBC_DRIVER}}};"
            f"DBQ={self.BDS_FILE_PATH};"
            f"PWD={self.BDS_PASSWORD};"
            f"ExtendedAnsiSQL=1;"
        )


def get_appdata_path() -> Path:
    """Get the AppData base directory for Busy Whatsapp Bridge."""
    appdata = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    config_dir = appdata / "BusyWhatsappBridge"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path in AppData."""
    return get_appdata_path() / "conf.json"


def load_settings() -> Settings:
    """Load settings from conf.json."""
    config_path = get_config_path()
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Settings(**data)
    
    # Return defaults if file doesn't exist
    return Settings()


def save_settings(settings: Settings) -> None:
    """Save settings to conf.json."""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(settings.model_dump(), f, indent=2)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return load_settings()
