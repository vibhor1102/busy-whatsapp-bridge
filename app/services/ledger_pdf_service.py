"""
Service to generate professional ledger PDFs using fpdf2.
"""
import structlog
from datetime import date
from pathlib import Path
from typing import Optional
from fpdf import FPDF

from app.models.ledger_schemas import (
    LedgerReport, 
    FinancialYearInfo, 
    CompanyInfo, 
    CustomerInfo,
    LedgerEntry
)
from app.exceptions.ledger_exceptions import PDFGenerationError

logger = structlog.get_logger()


class LedgerPDF(FPDF):
    """Custom PDF class for ledger reports."""
    
    def __init__(self, company_name: str = ""):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.company_name = company_name
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(left=15, top=15, right=15)
        self.alias_nb_pages()  # For {nb} placeholder in footer
        
    def header(self):
        """Company header on each page."""
        if not self.company_name:
            return
            
        # Company name - bold, centered
        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, self.company_name, align='C')
        self.ln(8)
        
        # Line separator
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        
    def footer(self):
        """Footer on each page."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')


class LedgerPDFService:
    """Service to generate ledger PDFs."""
    
    def __init__(self):
        pass
    
    def _format_amount(self, amount, include_dr_cr: bool = False, is_debit: Optional[bool] = None) -> str:
        """Format amount in Indian numbering style."""
        if amount is None:
            return ""
        
        # Format with Indian separators
        try:
            formatted = f"{float(amount):,.2f}"
        except (ValueError, TypeError):
            return str(amount)
        
        if include_dr_cr and is_debit is not None:
            suffix = " Dr" if is_debit else " Cr"
            return formatted + suffix
        
        return formatted
    
    def _format_date(self, dt) -> str:
        """Format date as DD/MM/YYYY."""
        if isinstance(dt, date):
            return dt.strftime("%d/%m/%Y")
        return str(dt)
    
    def generate(
        self,
        report: LedgerReport,
        output_path: str
    ) -> str:
        """
        Generate ledger PDF.
        
        Args:
            report: LedgerReport with all data
            output_path: Path to save PDF
            
        Returns:
            Path to generated PDF
            
        Raises:
            PDFGenerationError: If generation fails
        """
        try:
            pdf = LedgerPDF(company_name=report.company.name)
            pdf.add_page()
            
            # Company details (address, GST)
            self._add_company_details(pdf, report.company)
            
            # Customer info
            self._add_customer_info(pdf, report.customer, report.financial_year)
            
            # Ledger table
            self._add_ledger_table(pdf, report)
            
            # Summary
            self._add_summary(pdf, report)
            
            # Save
            pdf.output(output_path)
            
            logger.info(
                "ledger_pdf_generated",
                output_path=output_path,
                party_code=report.customer.code,
                entries_count=len(report.entries)
            )
            
            return output_path
            
        except Exception as e:
            logger.error("generate_pdf_error", error=str(e))
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")
    
    def _add_company_details(self, pdf: FPDF, company: CompanyInfo):
        """Add company address and GST."""
        pdf.set_font('Arial', '', 9)
        
        # Build address lines
        lines = []
        if company.address_line1:
            lines.append(company.address_line1)
        if company.address_line2:
            lines.append(company.address_line2)
        if company.address_line3:
            lines.append(company.address_line3)
        if company.address_line4:
            lines.append(company.address_line4)
        
        # Print address
        for line in lines[:2]:  # Limit to 2 lines for space
            pdf.cell(0, 5, line, align='C')
            pdf.ln(5)
        
        # GST number
        if company.gst_no:
            pdf.cell(0, 5, f"GST: {company.gst_no}", align='C')
            pdf.ln(5)
        
        pdf.ln(5)
    
    def _add_customer_info(
        self, 
        pdf: FPDF, 
        customer: CustomerInfo,
        fy_info: FinancialYearInfo
    ):
        """Add customer details and financial year."""
        # Title
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'LEDGER ACCOUNT')
        pdf.ln(10)
        
        # Customer name
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, f"M/s. {customer.name}")
        pdf.ln(6)
        
        # Print name if different
        if customer.print_name and customer.print_name != customer.name:
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, f"({customer.print_name})")
            pdf.ln(5)
        
        # Address
        pdf.set_font('Arial', '', 9)
        if customer.address_line1:
            pdf.cell(0, 5, customer.address_line1)
            pdf.ln(5)
        if customer.address_line2:
            pdf.cell(0, 5, customer.address_line2)
            pdf.ln(5)
        if customer.address_line3:
            pdf.cell(0, 5, customer.address_line3)
            pdf.ln(5)
        
        # GST
        if customer.gst_no:
            pdf.cell(0, 5, f"GST: {customer.gst_no}")
            pdf.ln(5)
        
        pdf.ln(3)
        
        # Financial Year info
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(95, 6, f"Financial Year: {fy_info.year_name}")
        pdf.cell(0, 6, f"As At: {self._format_date(fy_info.end_date)}", align='R')
        pdf.ln(11)
        pdf.ln(5)
    
    def _add_ledger_table(self, pdf: FPDF, report: LedgerReport):
        """Add the main ledger table with separate Dr and Cr columns."""
        # Prepare table data
        table_data = []
        
        # Header row - Date, Particulars, Dr Amount, Cr Amount, Balance
        table_data.append([
            "Date",
            "Particulars",
            "Dr Amount (Rs.)",
            "Cr Amount (Rs.)",
            "Balance (Rs.)"
        ])
        
        # Opening balance row
        table_data.append([
            self._format_date(report.financial_year.start_date),
            "Opening Balance",
            "",
            "",
            report.opening_balance_formatted
        ])
        
        # Transaction rows
        for entry in report.entries:
            # Particulars already include voucher number from data service
            particulars = entry.particulars
            
            # Separate Dr and Cr amounts
            dr_amount = self._format_amount(entry.amount) if entry.is_debit else ""
            cr_amount = self._format_amount(entry.amount) if not entry.is_debit else ""
            
            table_data.append([
                entry.date_formatted,
                particulars[:50],  # Limit length
                dr_amount,
                cr_amount,
                entry.balance_formatted
            ])
        
        # Closing balance row
        table_data.append([
            self._format_date(report.financial_year.end_date),
            "Closing Balance",
            "",
            "",
            report.closing_balance_formatted
        ])
        
        # Render table using fpdf2 table API
        pdf.set_font('Arial', '', 8)
        
        # Column widths (in mm) - total 180mm - must be tuple
        # Date: 18, Particulars: 75, Dr: 25, Cr: 25, Balance: 37
        col_widths = (18, 75, 25, 25, 37)
        alignments = ('C', 'L', 'R', 'R', 'R')
        
        try:
            # Use fpdf2 table method
            with pdf.table(
                col_widths=col_widths,
                text_align=alignments,
                line_height=6,
                padding=1
            ) as table:
                for i, row_data in enumerate(table_data):
                    row = table.row()
                    
                    # Bold for header and balance rows
                    if i == 0 or i == len(table_data) - 1:
                        pdf.set_font('Arial', 'B', 8)
                    elif i == 1 and "Opening" in str(row_data[1]):
                        pdf.set_font('Arial', 'B', 8)
                    else:
                        pdf.set_font('Arial', '', 8)
                    
                    for cell_data in row_data:
                        row.cell(str(cell_data))
                        
        except Exception as e:
            # Fallback: manual table rendering if fpdf2 table fails
            logger.warning("fpdf2_table_failed", error=str(e))
            self._render_manual_table(pdf, table_data, list(col_widths), list(alignments))
    
    def _render_manual_table(
        self, 
        pdf: FPDF, 
        table_data: list, 
        col_widths: list,
        alignments: list
    ):
        """Fallback manual table rendering."""
        pdf.set_font('Arial', '', 8)
        
        for i, row_data in enumerate(table_data):
            # Check if we need a new page
            if pdf.get_y() > 250:
                pdf.add_page()
            
            # Bold for header
            if i == 0:
                pdf.set_font('Arial', 'B', 8)
            else:
                pdf.set_font('Arial', '', 8)
            
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            max_height = 0
            
            # Calculate cell heights
            for j, cell_data in enumerate(row_data):
                pdf.set_xy(x_start + sum(col_widths[:j]), y_start)
                pdf.multi_cell(col_widths[j], 5, str(cell_data), border=1, align=alignments[j])
                max_height = max(max_height, pdf.get_y() - y_start)
            
            pdf.set_xy(x_start, y_start + max_height)
    
    def _add_summary(self, pdf: FPDF, report: LedgerReport):
        """Add summary section at the end."""
        pdf.ln(8)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "Summary")
        pdf.ln(6)
        
        pdf.set_font('Arial', '', 9)
        pdf.cell(95, 6, f"Total Debits: Rs. {report.total_debits_formatted}")
        pdf.cell(0, 6, f"Total Credits: Rs. {report.total_credits_formatted}", align='R')
        pdf.ln(6)
        pdf.cell(0, 6, f"Closing Balance: Rs. {report.closing_balance_formatted}")
        pdf.ln(6)
        
        # Generated timestamp
        pdf.ln(5)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 5, f"Generated on: {report.generated_at.strftime('%d/%m/%Y %H:%M')}")
        pdf.ln(5)


# Global instance
ledger_pdf_service = LedgerPDFService()
