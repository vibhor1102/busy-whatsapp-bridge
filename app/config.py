import json
import os
import logging
from pathlib import Path
from typing import Optional
from functools import lru_cache
from pydantic import BaseModel, Field

from app.version import get_version

logger = logging.getLogger(__name__)

class ServerSettings(BaseModel):
    """Server runtime configuration (user-configurable)."""
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
    meta_webhook_verify_token: Optional[str] = None
    default_country_code: str = "91"
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
    """Application configuration (user-configurable settings only)."""
    
    # App metadata - hardcoded, not configurable
    APP_NAME: str = "Busy Whatsapp Bridge"
    APP_VERSION: str = Field(default_factory=get_version)
    
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    whatsapp: WhatsAppSettings = Field(default_factory=WhatsAppSettings)
    baileys: BaileysSettings = Field(default_factory=BaileysSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    reminders: ReminderSettings = Field(default_factory=ReminderSettings)
    
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
    def META_WEBHOOK_VERIFY_TOKEN(self) -> Optional[str]:
        return self.whatsapp.meta_webhook_verify_token

    @property
    def WHATSAPP_DEFAULT_COUNTRY_CODE(self) -> str:
        return self.whatsapp.default_country_code
    
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
        return str(get_roaming_appdata_path() / "data" / "reminder_config.json")
    
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


def get_local_appdata_path() -> Path:
    """Get the Local AppData directory for machine-specific data (databases, auth)."""
    appdata = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    data_dir = appdata / "BusyWhatsappBridge"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_roaming_appdata_path() -> Path:
    """Get the Roaming AppData directory for user configuration."""
    appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    config_dir = appdata / "BusyWhatsappBridge"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Resolve effective configuration path with explicit precedence."""
    roaming = get_roaming_appdata_path() / "conf.json"
    local = get_local_appdata_path() / "conf.json"

    if roaming.exists() and local.exists():
        try:
            roaming_data = roaming.read_text(encoding="utf-8", errors="ignore")
            local_data = local.read_text(encoding="utf-8", errors="ignore")
            if roaming_data != local_data:
                logger.warning(
                    "Both Roaming and Local conf.json exist; using Roaming path. "
                    "Update/migrate Local copy if unintended.",
                    extra={"roaming_path": str(roaming), "local_path": str(local)},
                )
        except Exception:
            logger.warning(
                "Both Roaming and Local conf.json exist; using Roaming path.",
                extra={"roaming_path": str(roaming), "local_path": str(local)},
            )
    if roaming.exists():
        return roaming
    if local.exists():
        logger.warning(
            "Falling back to Local conf.json because Roaming conf.json is missing.",
            extra={"local_path": str(local)},
        )
        return local
    return roaming


def get_config_details() -> dict:
    """Return effective and alternate config locations for diagnostics."""
    effective = get_config_path()
    roaming = get_roaming_appdata_path() / "conf.json"
    local = get_local_appdata_path() / "conf.json"
    roaming_token_configured = False
    local_token_configured = False
    token_mismatch = False
    try:
        if roaming.exists():
            roaming_data = json.loads(roaming.read_text(encoding="utf-8", errors="ignore"))
            roaming_token = (roaming_data.get("whatsapp", {}) or {}).get("meta_webhook_verify_token")
            roaming_token_configured = bool(str(roaming_token or "").strip())
        else:
            roaming_token = None
        if local.exists():
            local_data = json.loads(local.read_text(encoding="utf-8", errors="ignore"))
            local_token = (local_data.get("whatsapp", {}) or {}).get("meta_webhook_verify_token")
            local_token_configured = bool(str(local_token or "").strip())
        else:
            local_token = None
        if roaming.exists() and local.exists():
            token_mismatch = (str(roaming_token or "").strip() != str(local_token or "").strip())
    except Exception:
        pass
    return {
        "effective_path": str(effective),
        "effective_source": "roaming" if effective == roaming else "local",
        "roaming_path": str(roaming),
        "roaming_exists": roaming.exists(),
        "local_path": str(local),
        "local_exists": local.exists(),
        "meta_webhook_token_mismatch": token_mismatch,
        "roaming_meta_webhook_token_configured": roaming_token_configured,
        "local_meta_webhook_token_configured": local_token_configured,
    }


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
