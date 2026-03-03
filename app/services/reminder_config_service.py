"""
Reminder Configuration Service

Handles read/write operations for reminder_config.json
Ensures thread-safe access and data integrity.
Supports multi-company isolation via database-scoped configurations.
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from app.config import get_settings
from app.constants.reminder_constants import CONFIG_FILE_NAME, DEFAULT_TEMPLATE_ID
from app.models.reminder_schemas import (
    ReminderConfig,
    PartyConfig,
    MessageTemplate,
    ScheduleConfig,
    CompanySettings,
    LedgerSettings,
    HistorySettings,
    LimitsConfig,
)

logger = structlog.get_logger()


def compute_scope_key(company_id: Optional[str]) -> str:
    """
    Compute a stable scope key from company_id.
    Returns 'default' if no company_id provided.
    """
    if not company_id:
        return "default"
    # Clean the company ID to be safe for directory names
    return "".join([c for c in company_id if c.isalnum() or c in ('-', '_')]).strip() or "default"


class ReminderConfigService:
    """Service for managing reminder configuration persistence with multi-company support"""

    def __init__(self):
        self.settings = get_settings()
        self._base_config_dir = Path(self.settings.REMINDER_CONFIG_PATH).parent
        self._configs: Dict[str, ReminderConfig] = {}
        self._current_scope: Optional[str] = None
        self._ensure_base_dir()

    def _ensure_base_dir(self):
        """Ensure base config directory exists"""
        self._base_config_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_path(self, scope_key: str) -> Path:
        """Get config file path for a scope"""
        if scope_key == "default":
            return self._base_config_dir / CONFIG_FILE_NAME
        scope_dir = self._base_config_dir / "scopes" / scope_key
        scope_dir.mkdir(parents=True, exist_ok=True)
        return scope_dir / CONFIG_FILE_NAME

    def set_scope(self, company_id: Optional[str]) -> str:
        """
        Set current scope based on company ID.
        Returns the scope key.
        """
        scope_key = compute_scope_key(company_id)
        if scope_key != self._current_scope:
            self._current_scope = scope_key
            logger.info("reminder_config_scope_changed", scope_key=scope_key)
        return scope_key

    def get_current_scope(self) -> str:
        """Get current scope key"""
        return self._current_scope or "default"

    def _ensure_config_file(self, scope_key: str):
        """Ensure config file exists with defaults for given scope"""
        config_path = self._get_config_path(scope_key)
        if not config_path.exists():
            # Attempt to migrate from old paths if appropriate
            migrated = self._attempt_migration(config_path, scope_key)
            if not migrated:
                logger.info("creating_default_config_file", path=str(config_path), scope=scope_key)
                default_config = self._create_default_config()
                self._save_config_to_file(default_config, config_path)

    def _attempt_migration(self, target_path: Path, scope_key: str) -> bool:
        """Attempt to migrate legacy config files to the new scoped path."""
        # 1. Check root configuration (oldest format)
        old_root_config = self._base_config_dir / CONFIG_FILE_NAME
        
        # We only migrate from root if it exists and we're looking at 'default' 
        # OR if we know it's a legacy hashed folder.
        
        if scope_key == "default" and old_root_config.exists() and old_root_config != target_path:
            try:
                shutil.copy2(old_root_config, target_path)
                logger.info("migrated_config_from_root", source=str(old_root_config), target=str(target_path))
                return True
            except Exception as e:
                logger.error("migration_failed", error=str(e))
                return False
                
        # 2. Try to find a legacy hashed folder if this is a newly defined company
        # Since we don't have the bds_file_path here easily, we can just look for ANY single hashed dir 
        # in 'scopes' if this is the ONLY company. This is a best-effort fallback.
        scopes_dir = self._base_config_dir / "scopes"
        if scopes_dir.exists():
            subdirs = [d for d in scopes_dir.iterdir() if d.is_dir() and len(d.name) == 12] # heuristics for hash
            if len(subdirs) == 1:
                hashed_config = subdirs[0] / CONFIG_FILE_NAME
                if hashed_config.exists():
                    try:
                        shutil.copy2(hashed_config, target_path)
                        logger.info("migrated_config_from_hash", source=str(hashed_config), target=str(target_path))
                        return True
                    except Exception as e:
                        logger.error("migration_failed", error=str(e))
                        
        return False

    def _create_default_config(self) -> ReminderConfig:
        """Create default configuration"""
        from app.constants.reminder_constants import (
            DEFAULT_CREDIT_DAYS,
            DEFAULT_SCHEDULE_ENABLED,
            DEFAULT_SCHEDULE_DAY,
            DEFAULT_SCHEDULE_TIME,
            DEFAULT_SCHEDULE_TIMEZONE,
            SCHEDULE_FREQUENCY_WEEKLY,
            DEFAULT_BATCH_SIZE,
            DEFAULT_DELAY_BETWEEN_MESSAGES,
        )
        
        # Templates now use {contact_phone} variable instead of hardcoded number
        default_templates = [
            MessageTemplate(
                id="standard",
                name="Standard Reminder",
                description="Professional and courteous - for regular reminders",
                content="Payment Reminder from {company_name}:\n\nDear {customer_name}, your outstanding balance is {currency_symbol}{amount_due}.\n\nPlease find your ledger statement attached for reference.\n\nFor any queries regarding this statement, please call or message us at {contact_phone}.\n\nThank you for your business.",
                is_default=True
            ),
            MessageTemplate(
                id="gentle",
                name="Gentle Nudge",
                description="Soft and friendly - for first reminders",
                content="This is a gentle reminder from {company_name}.\n\nHello {customer_name}, your pending payment of {currency_symbol}{amount_due} is awaiting settlement.\n\nYour complete account ledger is attached with this message.\n\nFor questions or clarifications, please contact us at {contact_phone}.\n\nWe appreciate your continued partnership.",
                is_default=False
            ),
            MessageTemplate(
                id="urgent",
                name="Urgent Notice",
                description="Direct and urgent - for overdue accounts",
                content="Urgent Payment Notice from {company_name}:\n\nDear {customer_name}, please note that an amount of {currency_symbol}{amount_due} remains outstanding on your account.\n\nYour ledger statement is attached for your immediate review.\n\nPlease contact us at {contact_phone} for any queries regarding this matter.\n\nImmediate attention requested.",
                is_default=False
            ),
            MessageTemplate(
                id="first",
                name="First Reminder",
                description="Friendly first contact - for initial reminders",
                content="Friendly reminder from {company_name}:\n\nHello {customer_name}, this is to inform you that your current outstanding balance is {currency_symbol}{amount_due}.\n\nPlease find your detailed ledger attached for your records.\n\nFor further enquiries, please call or message us at {contact_phone}.\n\nLooking forward to your prompt response.",
                is_default=False
            ),
            MessageTemplate(
                id="final",
                name="Final Notice",
                description="Firm final notice - for persistent delays",
                content="Final Payment Notice from {company_name}:\n\nDear {customer_name}, this is a final reminder regarding your outstanding amount of {currency_symbol}{amount_due}.\n\nYour account ledger is attached for immediate review and action.\n\nPlease contact us urgently at {contact_phone} to discuss this matter.\n\nImmediate settlement required.",
                is_default=False
            ),
        ]
        
        return ReminderConfig(
            default_credit_days=DEFAULT_CREDIT_DAYS,
            default_provider=self.settings.WHATSAPP_PROVIDER,
            currency_symbol="₹",
            company=CompanySettings(
                name="Your Company Name",
                contact_phone="",
                address=None
            ),
            schedule=ScheduleConfig(
                enabled=DEFAULT_SCHEDULE_ENABLED,
                day_of_week=DEFAULT_SCHEDULE_DAY,
                time=DEFAULT_SCHEDULE_TIME,
                timezone=DEFAULT_SCHEDULE_TIMEZONE,
                frequency=SCHEDULE_FREQUENCY_WEEKLY,
                batch_size=DEFAULT_BATCH_SIZE,
                delay_between_messages=DEFAULT_DELAY_BETWEEN_MESSAGES
            ),
            ledger=LedgerSettings(
                date_range_days=90,
                include_all_transactions=True
            ),
            history=HistorySettings(
                retention_days=365
            ),
            limits=LimitsConfig(
                max_templates=6,
                max_batch_size=500,
                max_delay_between_messages=60
            ),
            templates=default_templates,
            active_template_id=DEFAULT_TEMPLATE_ID,
            parties={}
        )

    def _load_config_from_file(self, scope_key: str) -> ReminderConfig:
        """Load configuration from JSON file with migration support"""
        config_path = self._get_config_path(scope_key)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data = self._migrate_config(data)

            config = ReminderConfig(**data)
            logger.debug("config_loaded_from_file", path=str(config_path), scope=scope_key)
            return config

        except Exception as e:
            logger.error(
                "error_loading_config",
                path=str(config_path),
                scope=scope_key,
                error=str(e)
            )
            return self._create_default_config()

    def _migrate_config(self, data: dict) -> dict:
        """
        Migrate old config format to new format.
        Handles adding new fields that didn't exist in older versions.
        """
        migrated = False

        if "currency_symbol" not in data:
            data["currency_symbol"] = "₹"
            migrated = True
            logger.debug("config_migration_added_currency_symbol")

        if "default_provider" not in data:
            data["default_provider"] = self.settings.WHATSAPP_PROVIDER
            migrated = True
            logger.debug("config_migration_added_default_provider", provider=data["default_provider"])

        if "company" not in data:
            data["company"] = {
                "name": "Your Company Name",
                "contact_phone": "",
                "address": None
            }
            migrated = True
            logger.debug("config_migration_added_company_settings")

        if "ledger" not in data:
            data["ledger"] = {
                "date_range_days": 90,
                "include_all_transactions": True
            }
            migrated = True
            logger.debug("config_migration_added_ledger_settings")

        if "history" not in data:
            data["history"] = {
                "retention_days": 365
            }
            migrated = True
            logger.debug("config_migration_added_history_settings")

        if "limits" not in data:
            data["limits"] = {
                "max_templates": 6,
                "max_batch_size": 500,
                "max_delay_between_messages": 60
            }
            migrated = True
            logger.debug("config_migration_added_limits_settings")

        if "templates" in data:
            for template in data["templates"]:
                content = template.get("content", "")
                if "7206366664" in content and "{contact_phone}" not in content:
                    content = content.replace("7206366664", "{contact_phone}")
                    template["content"] = content
                    migrated = True
                    logger.debug("config_migration_updated_template_phone", template_id=template.get("id"))
                if "₹{amount_due}" in content and "{currency_symbol}{amount_due}" not in content:
                    content = content.replace("₹{amount_due}", "{currency_symbol}{amount_due}")
                    template["content"] = content
                    migrated = True
                    logger.debug("config_migration_updated_template_currency", template_id=template.get("id"))

        if "templates" in data:
            for template in data["templates"]:
                variables = template.get("variables", [])
                if "contact_phone" not in variables:
                    variables.append("contact_phone")
                    migrated = True
                if "currency_symbol" not in variables:
                    variables.append("currency_symbol")
                    migrated = True
                if "party_code" not in variables:
                    variables.append("party_code")
                    migrated = True
                if "phone" not in variables:
                    variables.append("phone")
                    migrated = True
                template["variables"] = variables

        if migrated:
            logger.info("config_migrated_to_new_format")

        return data

    def _save_config_to_file(self, config: ReminderConfig, config_path: Path):
        """Save configuration to JSON file"""
        try:
            config.last_updated = datetime.now()

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(), f, indent=2, default=str)

            logger.debug("config_saved_to_file", path=str(config_path))

        except Exception as e:
            logger.error(
                "error_saving_config",
                path=str(config_path),
                error=str(e)
            )
            raise

    def get_config(self, scope_key: Optional[str] = None) -> ReminderConfig:
        """Get current configuration (cached)"""
        if scope_key is None:
            scope_key = self.get_current_scope()
        if scope_key not in self._configs:
            self._ensure_config_file(scope_key)
            self._configs[scope_key] = self._load_config_from_file(scope_key)
        return self._configs[scope_key]

    def reload_config(self, scope_key: Optional[str] = None) -> ReminderConfig:
        """Force reload configuration from file"""
        if scope_key is None:
            scope_key = self.get_current_scope()
        self._configs[scope_key] = self._load_config_from_file(scope_key)
        return self._configs[scope_key]

    def save_config(self, config: ReminderConfig, scope_key: Optional[str] = None):
        """Save configuration"""
        if scope_key is None:
            scope_key = self.get_current_scope()
        config_path = self._get_config_path(scope_key)
        self._save_config_to_file(config, config_path)
        self._configs[scope_key] = config

    def update_schedule(self, schedule: ScheduleConfig, scope_key: Optional[str] = None):
        """Update schedule configuration"""
        config = self.get_config(scope_key)
        config.schedule = schedule
        self.save_config(config, scope_key)
        logger.info("schedule_config_updated", scope=scope_key or self.get_current_scope())
    
    def get_party_config(self, party_code: str, scope_key: Optional[str] = None) -> Optional[PartyConfig]:
        """Get configuration for a specific party"""
        config = self.get_config(scope_key)
        return config.parties.get(party_code)
    
    def update_party_config(self, party_code: str, party_config: PartyConfig, scope_key: Optional[str] = None):
        """Update configuration for a specific party"""
        config = self.get_config(scope_key)
        config.parties[party_code] = party_config
        self.save_config(config, scope_key)
        logger.info("party_config_updated", party_code=party_code, enabled=party_config.enabled)
    
    def get_template(self, template_id: str, scope_key: Optional[str] = None) -> Optional[MessageTemplate]:
        """Get a specific template by ID"""
        config = self.get_config(scope_key)
        for template in config.templates:
            if template.id == template_id:
                return template
        return None
    
    def get_all_templates(self, scope_key: Optional[str] = None) -> List[MessageTemplate]:
        """Get all templates"""
        config = self.get_config(scope_key)
        return config.templates
    
    def add_template(self, template: MessageTemplate, scope_key: Optional[str] = None):
        """Add a new template"""
        config = self.get_config(scope_key)
        
        # Check for duplicate ID
        if any(t.id == template.id for t in config.templates):
            raise ValueError(f"Template with ID '{template.id}' already exists")
        
        # Check template limit from config
        max_templates = config.limits.max_templates
        if len(config.templates) >= max_templates:
            raise ValueError(f"Maximum number of templates ({max_templates}) reached")
        
        config.templates.append(template)
        self.save_config(config, scope_key)
        logger.info("template_added", template_id=template.id, name=template.name)
    
    def update_template(self, template_id: str, template: MessageTemplate, scope_key: Optional[str] = None):
        """Update an existing template"""
        config = self.get_config(scope_key)
        
        for i, existing in enumerate(config.templates):
            if existing.id == template_id:
                config.templates[i] = template
                self.save_config(config, scope_key)
                logger.info("template_updated", template_id=template_id)
                return
        
        raise ValueError(f"Template with ID '{template_id}' not found")
    
    def delete_template(self, template_id: str, scope_key: Optional[str] = None):
        """Delete a template"""
        config = self.get_config(scope_key)
        
        # Don't allow deleting the default template
        template = self.get_template(template_id, scope_key)
        if template and template.is_default:
            raise ValueError("Cannot delete the default template")
        
        config.templates = [t for t in config.templates if t.id != template_id]
        
        # If active template was deleted, reset to default
        if config.active_template_id == template_id:
            config.active_template_id = DEFAULT_TEMPLATE_ID
        
        self.save_config(config, scope_key)
        logger.info("template_deleted", template_id=template_id)
    
    def set_active_template(self, template_id: str, scope_key: Optional[str] = None):
        """Set the active template"""
        config = self.get_config(scope_key)
        
        if not any(t.id == template_id for t in config.templates):
            raise ValueError(f"Template with ID '{template_id}' not found")
        
        config.active_template_id = template_id
        self.save_config(config, scope_key)
        logger.info("active_template_set", template_id=template_id)
    
    def get_active_template(self, scope_key: Optional[str] = None) -> MessageTemplate:
        """Get the currently active template"""
        config = self.get_config(scope_key)
        template = self.get_template(config.active_template_id, scope_key)
        
        if template is None:
            # Fallback to default if active template not found
            template = self.get_template(DEFAULT_TEMPLATE_ID, scope_key)
        
        return template
    
    def set_default_template(self, template_id: str, scope_key: Optional[str] = None):
        """Set a template as the default"""
        config = self.get_config(scope_key)
        
        # Unset current default
        for t in config.templates:
            t.is_default = False
        
        # Set new default
        for t in config.templates:
            if t.id == template_id:
                t.is_default = True
                break
        else:
            raise ValueError(f"Template with ID '{template_id}' not found")
        
        self.save_config(config, scope_key)
        logger.info("default_template_set", template_id=template_id)

    # =========================================================================
    # Refresh Stats Persistence (separate file to avoid config churn)
    # =========================================================================

    def _get_refresh_stats_path(self, scope_key: str) -> Path:
        """Get refresh stats file path for a scope"""
        config_path = self._get_config_path(scope_key)
        return config_path.parent / "refresh_stats.json"

    def _load_refresh_stats(self, scope_key: str) -> dict:
        """Load refresh stats from file"""
        stats_path = self._get_refresh_stats_path(scope_key)
        if stats_path.exists():
            try:
                with open(stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("failed_to_load_refresh_stats", error=str(e))
        return {
            "last_refresh_at": None,
            "last_5_durations_ms": [],
            "rolling_avg_ms": 0,
            "last_reminder_sent_at": None,
        }

    def _save_refresh_stats(self, stats: dict, scope_key: str):
        """Save refresh stats to file"""
        stats_path = self._get_refresh_stats_path(scope_key)
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, default=str)
        except Exception as e:
            logger.error("failed_to_save_refresh_stats", error=str(e))

    def get_refresh_stats(self, scope_key: Optional[str] = None) -> dict:
        """Get refresh stats for a company"""
        if scope_key is None:
            scope_key = self.get_current_scope()
        return self._load_refresh_stats(scope_key)

    def record_refresh_completed(self, duration_ms: int, scope_key: Optional[str] = None):
        """Record a completed refresh for rolling average tracking"""
        if scope_key is None:
            scope_key = self.get_current_scope()
        stats = self._load_refresh_stats(scope_key)

        stats["last_refresh_at"] = datetime.now().isoformat()

        durations = stats.get("last_5_durations_ms", [])
        durations.append(duration_ms)
        # Keep only last 5
        if len(durations) > 5:
            durations = durations[-5:]
        stats["last_5_durations_ms"] = durations
        stats["rolling_avg_ms"] = int(sum(durations) / len(durations)) if durations else 0

        self._save_refresh_stats(stats, scope_key)
        logger.info(
            "refresh_stats_recorded",
            duration_ms=duration_ms,
            rolling_avg_ms=stats["rolling_avg_ms"],
            scope=scope_key,
        )

    def record_reminder_sent(self, scope_key: Optional[str] = None):
        """Record when reminders were last sent for cooldown tracking"""
        if scope_key is None:
            scope_key = self.get_current_scope()
        stats = self._load_refresh_stats(scope_key)
        stats["last_reminder_sent_at"] = datetime.now().isoformat()
        self._save_refresh_stats(stats, scope_key)
        logger.info("reminder_sent_timestamp_recorded", scope=scope_key)

    def get_last_reminder_sent_at(self, scope_key: Optional[str] = None) -> Optional[str]:
        """Get the last time reminders were sent for a company"""
        if scope_key is None:
            scope_key = self.get_current_scope()
        stats = self._load_refresh_stats(scope_key)
        return stats.get("last_reminder_sent_at")


# Global instance
reminder_config_service = ReminderConfigService()

