import json
import os
import logging
from pathlib import Path
from typing import Optional
from functools import lru_cache
from pydantic import BaseModel, Field

from app.version import get_version

class ServerSettings(BaseModel):
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


class CompanyDatabase(BaseModel):
    """Specific company database configuration."""
    bds_file_path: str = ""
    bds_password: str = "ILoveMyINDIA"
    company_name: Optional[str] = None
    contact_phone: Optional[str] = None
    company_address: Optional[str] = None


class DatabaseSettings(BaseModel):
    """Database configuration."""
    # Legacy fields
    bds_file_path: str = ""
    bds_password: str = "ILoveMyINDIA"
    
    # Advanced fields
    odbc_driver: str = "Microsoft Access Driver (*.mdb, *.accdb)"
    
    # Multi-company mapping
    companies: dict[str, CompanyDatabase] = Field(default_factory=dict)

    class Config:
        pass


class WhatsAppSettings(BaseModel):
    """WhatsApp provider configuration."""
    provider: str = "baileys"
    # =============================================================================
    # REMOVED PROVIDER CONFIGURATIONS
    # The following settings were for Meta, Evolution, and Webhook providers
    # which have been removed. Only Baileys is now used.
    # Configuration keys kept for backward compatibility but are no longer used.
    default_country_code: str = "91"


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
    # =============================================================================
    # REMOVED: provider setting was previously "meta"
    # Now using "baileys" as the only provider
    # TODO: Re-add other providers via Baileys integration when needed
    # =============================================================================
    provider: str = "baileys"
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

    def resolve_company_id(self, company_id: Optional[str] = None) -> str:
        """
        Resolve an effective company id for database-bound operations.

        Behavior:
        - Use requested id if it exists in configured companies.
        - For missing/blank/default requests:
          - Use legacy database path if present.
          - Otherwise, fall back to the first configured company.
        """
        requested = (company_id or "default").strip() or "default"

        if requested in self.database.companies:
            return requested

        if requested == "default":
            if self.database.bds_file_path:
                return "default"
            if self.database.companies:
                return next(iter(self.database.companies.keys()))

        return requested
    
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
        # Backward compatibility property; getting the path for 'default' company if it exists
        effective_company_id = self.resolve_company_id("default")
        if effective_company_id in self.database.companies:
            return self.database.companies[effective_company_id].bds_file_path
        return self.database.bds_file_path
    
    @property
    def BDS_PASSWORD(self) -> str:
        effective_company_id = self.resolve_company_id("default")
        if effective_company_id in self.database.companies:
            return self.database.companies[effective_company_id].bds_password
        return self.database.bds_password
    
    @property
    def ODBC_DRIVER(self) -> str:
        return self.database.odbc_driver
    
    @property
    def WHATSAPP_PROVIDER(self) -> str:
        return self.whatsapp.provider
    
    @property
    def WHATSAPP_DEFAULT_COUNTRY_CODE(self) -> str:
        return self.whatsapp.default_country_code
    
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
    
    def get_database_connection_string(self, company_id: str = "default") -> str:
        """Generate ODBC connection string for MS Access for a specific company."""
        company_id = self.resolve_company_id(company_id)

        # 1. Look in companies dictionary
        if company_id in self.database.companies:
            path = self.database.companies[company_id].bds_file_path
            pwd = self.database.companies[company_id].bds_password
        # 2. Fallback to legacy config if "default" is requested
        elif company_id == "default" and self.database.bds_file_path:
            path = self.database.bds_file_path
            pwd = self.database.bds_password
        else:
            raise ValueError(f"No configured database found for company '{company_id}'")
            
        if not path:
            raise ValueError(f"Database path cannot be empty for company '{company_id}'")
        if ";" in path:
            raise ValueError(f"Database path contains invalid character ';' for company '{company_id}'")
        
        return (
            f"DRIVER={{{self.ODBC_DRIVER}}};"
            f"DBQ={path};"
            f"PWD={pwd};"
            "Exclusive=0;"
            f"ExtendedAnsiSQL=1;"
        )


def get_roaming_appdata_path() -> Path:
    """Get the Roaming AppData directory for user configuration and data."""
    appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    config_dir = appdata / "BusyWhatsappBridge"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_roaming_appdata_path() / "conf.json"


def get_config_details() -> dict:
    """Return config location for diagnostics."""
    config_path = get_config_path()
    return {
        "effective_path": str(config_path),
        "config_exists": config_path.exists(),
    }

def load_settings() -> Settings:
    """Load settings from conf.json."""
    config_path = get_config_path()
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return Settings(**data)
    except Exception as e:
        logger.warning("failed_loading_settings_falling_back_to_defaults", error=str(e))
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
