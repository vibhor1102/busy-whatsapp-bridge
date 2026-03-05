"""
Template Service

Handles message template rendering and variable substitution.
"""
import re
from typing import Dict, Any, Optional

import structlog

from app.config import get_settings
from app.models.reminder_schemas import MessageTemplate
from app.services.reminder_config_service import reminder_config_service
from app.services.ledger_data_service import ledger_data_service
from app.utils.number_format import format_indian_number

logger = structlog.get_logger()


class TemplateService:
    """Service for rendering message templates"""
    
    # Regex to find template variables: {variable_name} or {{number}}
    VARIABLE_PATTERN = re.compile(r'\{\{?([a-zA-Z_][a-zA-Z0-9_]*|\d+)\}??}')
    
    def __init__(self):
        self.config_service = reminder_config_service

    def _resolve_company_display_name(
        self,
        company_id: str,
        config_company_name: Optional[str] = None,
        company_info_name: Optional[str] = None,
    ) -> str:
        """Resolve company display name with settings company_name as top priority."""
        settings = get_settings()
        companies = settings.database.companies or {}

        if company_id in companies:
            configured_name = (companies[company_id].company_name or "").strip()
            if configured_name:
                return configured_name

        # Avoid surfacing generic placeholder names when a real one is available elsewhere.
        if company_info_name and company_info_name not in ("Unknown Company", "Company"):
            return company_info_name

        if config_company_name and config_company_name not in ("Your Company Name", "Company"):
            return config_company_name

        try:
            effective_default = settings.resolve_company_id("default")
            if effective_default in companies:
                default_name = (companies[effective_default].company_name or "").strip()
                if default_name:
                    return default_name
        except Exception:
            pass

        return "Company"
    
    def extract_variables(self, template_content: str) -> list:
        """Extract all variables from template content"""
        return self.VARIABLE_PATTERN.findall(template_content)
    
    def validate_variables(self, template_content: str, available_vars: Dict[str, Any]) -> tuple:
        """
        Validate that all variables in template have values
        
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        required_vars = self.extract_variables(template_content)
        missing = [var for var in required_vars if var not in available_vars]
        
        return len(missing) == 0, missing
    
    def render_template(
        self,
        template: MessageTemplate,
        variables: Dict[str, Any]
    ) -> str:
        """
        Render template with variable substitution
        
        Args:
            template: MessageTemplate to render
            variables: Dictionary of variable names and values
            
        Returns:
            Rendered message string
            
        Raises:
            ValueError: If required variables are missing
        """
        is_valid, missing = self.validate_variables(template.content, variables)
        
        if not is_valid:
            logger.error(
                "missing_template_variables",
                template_id=template.id,
                missing=missing
            )
            raise ValueError(f"Missing variables: {', '.join(missing)}")
        
        # Perform substitution
        rendered = template.content
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            rendered = rendered.replace(placeholder, str(var_value))
        
        logger.debug(
            "template_rendered",
            template_id=template.id,
            variables=list(variables.keys())
        )
        
        return rendered
    
    def get_template_variables(
        self,
        party_code: str,
        amount_due: float,
        company_name: Optional[str] = None,
        company_id: str = "default",
    ) -> Dict[str, str]:
        """
        Get all available variables for a party
        
        Args:
            party_code: Party code
            amount_due: Amount due value
        company_name: Company name (optional, fetched from config if not provided)
        company_id: Company scope key
            
        Returns:
            Dictionary of variable names and values
        """
        # Get config for company settings and currency
        config = self.config_service.get_config(scope_key=company_id)
        currency_symbol = config.currency_symbol
        party_info = ledger_data_service.get_customer_info(party_code, company_id)
        # Get company info first, since that will contain our new DB-specific contact details
        company_info = ledger_data_service.get_company_info(company_id)
        contact_phone = company_info.phone or config.company.contact_phone
        company_name = company_name or self._resolve_company_display_name(
            company_id=company_id,
            config_company_name=config.company.name,
            company_info_name=company_info.name,
        )
        
        # Get credit days
        credit_days, _ = ledger_data_service.get_credit_days(party_code, company_id)
        
        # Format amount
        amount_formatted = format_indian_number(amount_due)
        
        return {
            "customer_name": party_info.name or party_info.print_name or "Valued Customer",
            "company_name": company_name,
            "amount_due": amount_formatted,
            "currency_symbol": currency_symbol,
            "credit_days": str(credit_days),
            "contact_phone": contact_phone,
            "party_code": party_code,
            "phone": party_info.phone or "",
        }
    
    def preview_template(
        self,
        template_id: str,
        party_code: str,
        amount_due: float
    ) -> str:
        """
        Preview a template with actual party data
        
        Args:
            template_id: Template ID to preview
            party_code: Party code for variable data
            amount_due: Amount due for this party
            
        Returns:
            Rendered message preview
        """
        template = self.config_service.get_template(template_id)
        
        if template is None:
            raise ValueError(f"Template '{template_id}' not found")
        
        variables = self.get_template_variables(party_code, amount_due)
        return self.render_template(template, variables)
    
    def get_default_variables(self, company_id: str = "default") -> Dict[str, str]:
        """Get sample variables for template preview/testing"""
        config = self.config_service.get_config(scope_key=company_id)
        company_info = ledger_data_service.get_company_info(company_id)
        company_name = self._resolve_company_display_name(
            company_id=company_id,
            config_company_name=config.company.name,
            company_info_name=company_info.name,
        )
        
        return {
            "customer_name": "ABC Textiles",
            "company_name": company_name,
            "amount_due": "50,000.00",
            "currency_symbol": config.currency_symbol,
            "credit_days": "30",
            "contact_phone": company_info.phone or config.company.contact_phone or "+91 98765 43210",
            "party_code": "1234",
            "phone": "+91 98765 43210",
        }


# Global instance
template_service = TemplateService()
