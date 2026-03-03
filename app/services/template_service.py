"""
Template Service

Handles message template rendering and variable substitution.
"""
import re
from typing import Dict, Any, Optional

import structlog

from app.models.reminder_schemas import MessageTemplate
from app.services.reminder_config_service import reminder_config_service
from app.services.ledger_data_service import ledger_data_service

logger = structlog.get_logger()


class TemplateService:
    """Service for rendering message templates"""
    
    # Regex to find template variables: {variable_name} or {{number}}
    VARIABLE_PATTERN = re.compile(r'\{\{?([a-zA-Z_][a-zA-Z0-9_]*|\d+)\}??}')
    
    def __init__(self):
        self.config_service = reminder_config_service
    
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
        company_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get all available variables for a party
        
        Args:
            party_code: Party code
            amount_due: Amount due value
            company_name: Company name (optional, fetched from config if not provided)
            
        Returns:
            Dictionary of variable names and values
        """
        # Get config for company settings and currency
        config = self.config_service.get_config()
        currency_symbol = config.currency_symbol
        # Get company info first, since that will contain our new DB-specific contact details
        company_info = ledger_data_service.get_company_info()
        contact_phone = company_info.phone or config.company.contact_phone
        company_name = company_name or company_info.name or config.company.name
        
        # Get credit days
        credit_days, _ = ledger_data_service.get_credit_days(party_code)
        
        # Format amount
        amount_formatted = f"{amount_due:,.2f}"
        
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
    
    def get_default_variables(self) -> Dict[str, str]:
        """Get sample variables for template preview/testing"""
        config = self.config_service.get_config()
        company_info = ledger_data_service.get_company_info()
        
        return {
            "customer_name": "ABC Textiles",
            "company_name": company_info.name or config.company.name,
            "amount_due": "50,000.00",
            "currency_symbol": config.currency_symbol,
            "credit_days": "30",
            "contact_phone": company_info.phone or config.company.contact_phone or "+91 98765 43210",
            "party_code": "1234",
            "phone": "+91 98765 43210",
        }


# Global instance
template_service = TemplateService()
