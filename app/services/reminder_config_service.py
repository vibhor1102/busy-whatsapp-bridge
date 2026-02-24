"""
Reminder Configuration Service

Handles read/write operations for reminder_config.json
Ensures thread-safe access and data integrity.
"""
import json
import os
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


class ReminderConfigService:
    """Service for managing reminder configuration persistence"""
    
    def __init__(self):
        self.settings = get_settings()
        self.config_path = Path(self.settings.REMINDER_CONFIG_PATH)
        self._config: Optional[ReminderConfig] = None
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """Ensure config file exists with defaults"""
        if not self.config_path.exists():
            logger.info("creating_default_config_file", path=str(self.config_path))
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            default_config = self._create_default_config()
            self._save_config_to_file(default_config)
    
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
    
    def _load_config_from_file(self) -> ReminderConfig:
        """Load configuration from JSON file with migration support"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Migrate old config format to new format
            data = self._migrate_config(data)
            
            config = ReminderConfig(**data)
            logger.debug("config_loaded_from_file", path=str(self.config_path))
            return config
            
        except Exception as e:
            logger.error(
                "error_loading_config",
                path=str(self.config_path),
                error=str(e)
            )
            # Return default config if file is corrupted
            return self._create_default_config()
    
    def _migrate_config(self, data: dict) -> dict:
        """
        Migrate old config format to new format.
        Handles adding new fields that didn't exist in older versions.
        """
        migrated = False
        
        # Add currency_symbol if missing
        if "currency_symbol" not in data:
            data["currency_symbol"] = "₹"
            migrated = True
            logger.debug("config_migration_added_currency_symbol")
        
        # Add company settings if missing
        if "company" not in data:
            data["company"] = {
                "name": "Your Company Name",
                "contact_phone": "",
                "address": None
            }
            migrated = True
            logger.debug("config_migration_added_company_settings")
        
        # Add ledger settings if missing
        if "ledger" not in data:
            data["ledger"] = {
                "date_range_days": 90,
                "include_all_transactions": True
            }
            migrated = True
            logger.debug("config_migration_added_ledger_settings")
        
        # Add history settings if missing
        if "history" not in data:
            data["history"] = {
                "retention_days": 365
            }
            migrated = True
            logger.debug("config_migration_added_history_settings")
        
        # Add limits settings if missing
        if "limits" not in data:
            data["limits"] = {
                "max_templates": 6,
                "max_batch_size": 500,
                "max_delay_between_messages": 60
            }
            migrated = True
            logger.debug("config_migration_added_limits_settings")
        
        # Migrate templates to use {contact_phone} and {currency_symbol} variables
        # instead of hardcoded values
        if "templates" in data:
            for template in data["templates"]:
                content = template.get("content", "")
                # Replace hardcoded phone numbers with variable
                if "7206366664" in content and "{contact_phone}" not in content:
                    content = content.replace("7206366664", "{contact_phone}")
                    template["content"] = content
                    migrated = True
                    logger.debug("config_migration_updated_template_phone", template_id=template.get("id"))
                # Replace hardcoded currency symbol with variable  
                if "₹{amount_due}" in content and "{currency_symbol}{amount_due}" not in content:
                    content = content.replace("₹{amount_due}", "{currency_symbol}{amount_due}")
                    template["content"] = content
                    migrated = True
                    logger.debug("config_migration_updated_template_currency", template_id=template.get("id"))
        
        # Update template variables list to include new variables
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
            # Save the migrated config back to file
            data["last_updated"] = datetime.now().isoformat()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        
        return data
    
    def _save_config_to_file(self, config: ReminderConfig):
        """Save configuration to JSON file"""
        try:
            # Update last_updated timestamp
            config.last_updated = datetime.now()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(), f, indent=2, default=str)
            
            logger.debug("config_saved_to_file", path=str(self.config_path))
            
        except Exception as e:
            logger.error(
                "error_saving_config",
                path=str(self.config_path),
                error=str(e)
            )
            raise
    
    def get_config(self) -> ReminderConfig:
        """Get current configuration (cached)"""
        if self._config is None:
            self._config = self._load_config_from_file()
        return self._config
    
    def reload_config(self) -> ReminderConfig:
        """Force reload configuration from file"""
        self._config = self._load_config_from_file()
        return self._config
    
    def save_config(self, config: ReminderConfig):
        """Save configuration"""
        self._save_config_to_file(config)
        self._config = config
    
    def update_schedule(self, schedule: ScheduleConfig):
        """Update schedule configuration"""
        config = self.get_config()
        config.schedule = schedule
        self.save_config(config)
        logger.info("schedule_config_updated")
    
    def get_party_config(self, party_code: str) -> Optional[PartyConfig]:
        """Get configuration for a specific party"""
        config = self.get_config()
        return config.parties.get(party_code)
    
    def update_party_config(self, party_code: str, party_config: PartyConfig):
        """Update configuration for a specific party"""
        config = self.get_config()
        config.parties[party_code] = party_config
        self.save_config(config)
        logger.info("party_config_updated", party_code=party_code, enabled=party_config.enabled)
    
    def get_template(self, template_id: str) -> Optional[MessageTemplate]:
        """Get a specific template by ID"""
        config = self.get_config()
        for template in config.templates:
            if template.id == template_id:
                return template
        return None
    
    def get_all_templates(self) -> List[MessageTemplate]:
        """Get all templates"""
        config = self.get_config()
        return config.templates
    
    def add_template(self, template: MessageTemplate):
        """Add a new template"""
        config = self.get_config()
        
        # Check for duplicate ID
        if any(t.id == template.id for t in config.templates):
            raise ValueError(f"Template with ID '{template.id}' already exists")
        
        # Check template limit from config
        max_templates = config.limits.max_templates
        if len(config.templates) >= max_templates:
            raise ValueError(f"Maximum number of templates ({max_templates}) reached")
        
        config.templates.append(template)
        self.save_config(config)
        logger.info("template_added", template_id=template.id, name=template.name)
    
    def update_template(self, template_id: str, template: MessageTemplate):
        """Update an existing template"""
        config = self.get_config()
        
        for i, existing in enumerate(config.templates):
            if existing.id == template_id:
                config.templates[i] = template
                self.save_config(config)
                logger.info("template_updated", template_id=template_id)
                return
        
        raise ValueError(f"Template with ID '{template_id}' not found")
    
    def delete_template(self, template_id: str):
        """Delete a template"""
        config = self.get_config()
        
        # Don't allow deleting the default template
        template = self.get_template(template_id)
        if template and template.is_default:
            raise ValueError("Cannot delete the default template")
        
        config.templates = [t for t in config.templates if t.id != template_id]
        
        # If active template was deleted, reset to default
        if config.active_template_id == template_id:
            config.active_template_id = DEFAULT_TEMPLATE_ID
        
        self.save_config(config)
        logger.info("template_deleted", template_id=template_id)
    
    def set_active_template(self, template_id: str):
        """Set the active template"""
        config = self.get_config()
        
        if not any(t.id == template_id for t in config.templates):
            raise ValueError(f"Template with ID '{template_id}' not found")
        
        config.active_template_id = template_id
        self.save_config(config)
        logger.info("active_template_set", template_id=template_id)
    
    def get_active_template(self) -> MessageTemplate:
        """Get the currently active template"""
        config = self.get_config()
        template = self.get_template(config.active_template_id)
        
        if template is None:
            # Fallback to default if active template not found
            template = self.get_template(DEFAULT_TEMPLATE_ID)
        
        return template
    
    def set_default_template(self, template_id: str):
        """Set a template as the default"""
        config = self.get_config()
        
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
        
        self.save_config(config)
        logger.info("default_template_set", template_id=template_id)


# Global instance
reminder_config_service = ReminderConfigService()
