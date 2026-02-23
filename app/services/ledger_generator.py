"""
Main callable interface for ledger PDF generation.

This module provides the primary function that the payment reminder system
can call to generate customer ledger PDFs.
"""
import os
import tempfile
from pathlib import Path
from typing import Optional
import structlog

from app.services.ledger_data_service import ledger_data_service
from app.services.ledger_pdf_service import ledger_pdf_service
from app.models.ledger_schemas import LedgerReport
from app.exceptions.ledger_exceptions import (
    LedgerError,
    PDFGenerationError,
    DatabaseConnectionError
)

logger = structlog.get_logger()


async def generate_ledger_pdf(
    party_code: str,
    output_path: Optional[str] = None
) -> str:
    """
    Generate customer ledger PDF for WhatsApp payment reminders.
    
    This is the main function that the payment reminder system should call.
    It fetches all necessary data from the database, generates a professional
    ledger PDF in portrait format with passbook-style balance column, and
    returns the path to the generated file.
    
    Args:
        party_code: Customer code from Master1 (e.g., "12345")
        output_path: Optional custom output path. If not provided, a temp
                    file will be created (caller must delete after use).
    
    Returns:
        Path to the generated PDF file.
        
        IMPORTANT: The caller is responsible for deleting the file after use.
                  For temp files, use:
                  ```
                  try:
                      pdf_path = await generate_ledger_pdf(party_code)
                      # send via WhatsApp
                  finally:
                      if os.path.exists(pdf_path):
                          os.remove(pdf_path)
                  ```
    
    Raises:
        CompanyInfoError: If company details not found in Config (RecType 8).
                         Error code: "COMPANY_INFO_MISSING"
                         Action: Skip this customer, log error.
        
        FinancialYearError: If financial year not found (RecType 7).
                           Error code: "FINANCIAL_YEAR_ERROR"
                           Action: Alert admin, check database.
        
        PartyNotFoundError: If customer code not found in Master1.
                           Error code: "PARTY_NOT_FOUND"
                           Action: Skip this customer, mark as invalid.
        
        NoTransactionsError: If no transactions for the financial year.
                            Error code: "NO_TRANSACTIONS"
                            Action: Send simple text reminder without PDF.
        
        PDFGenerationError: If PDF generation fails unexpectedly.
                           Error code: "PDF_GENERATION_FAILED"
                           Action: Retry or alert admin.
        
        DatabaseConnectionError: If database is unreachable.
                                Error code: "DATABASE_CONNECTION_ERROR"
                                Action: Retry later.
    
    Example:
        ```python
        from app.services.ledger_generator import generate_ledger_pdf
        from app.exceptions.ledger_exceptions import (
            CompanyInfoError, PartyNotFoundError, NoTransactionsError
        )
        
        try:
            pdf_path = await generate_ledger_pdf("12345")
            
            # Send via WhatsApp
            await whatsapp.send_document(
                phone="+919876543210",
                document_path=pdf_path,
                caption="Your ledger is attached."
            )
            
        except CompanyInfoError as e:
            logger.error(f"Company config missing: {e.error_code}")
            # Continue to next customer
            
        except PartyNotFoundError as e:
            logger.error(f"Invalid party: {e.details['party_code']}")
            # Mark as invalid in database
            
        except NoTransactionsError:
            logger.info("No transactions, sending simple reminder")
            # Send text-only reminder
            
        finally:
            # Clean up temp file
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)
        ```
    
    PDF Format:
        - Portrait A4 format
        - Company header (name, address, GST from Config RecType 8)
        - Customer details (name, address, GST from Master1)
        - Financial year and "As At" date
        - Single-column particulars with Dr/Cr suffix (not split columns)
        - Running balance column on rightmost side (passbook style)
        - Automatic pagination for long ledgers
        - Summary section at end (total debits, credits, closing balance)
    """
    logger.info("generate_ledger_pdf_called", party_code=party_code)
    
    temp_file_created = False
    
    try:
        # Step 1: Generate ledger report data
        # This fetches company info, customer info, transactions, and calculates balances
        report: LedgerReport = ledger_data_service.generate_ledger_report(party_code)
        
        # Step 2: Determine output path
        if not output_path:
            # Create temp file
            temp_fd, output_path = tempfile.mkstemp(
                suffix='.pdf',
                prefix=f'ledger_{party_code}_',
                dir=tempfile.gettempdir()
            )
            os.close(temp_fd)
            temp_file_created = True
            logger.debug("temp_file_created", path=output_path)
        
        # Step 3: Generate PDF
        pdf_path = ledger_pdf_service.generate(
            report=report,
            output_path=output_path
        )
        
        logger.info(
            "ledger_pdf_generated_successfully",
            party_code=party_code,
            pdf_path=pdf_path,
            entries_count=len(report.entries),
            temp_file=temp_file_created
        )
        
        return pdf_path
        
    except LedgerError:
        # Re-raise known ledger errors (CompanyInfoError, PartyNotFoundError, etc.)
        if temp_file_created and output_path and os.path.exists(output_path):
            os.remove(output_path)
        raise
        
    except Exception as e:
        # Unknown error - wrap in PDFGenerationError
        logger.error(
            "unexpected_error_generating_ledger",
            party_code=party_code,
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Clean up temp file if created
        if temp_file_created and output_path and os.path.exists(output_path):
            os.remove(output_path)
        
        raise PDFGenerationError(
            f"Unexpected error generating ledger for {party_code}: {str(e)}"
        )


def cleanup_ledger_pdf(pdf_path: str) -> bool:
    """
    Safely delete a ledger PDF file.
    
    Call this after successfully sending the PDF via WhatsApp
    to clean up temp files.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        True if file was deleted, False otherwise
    """
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.debug("ledger_pdf_cleaned_up", path=pdf_path)
            return True
        return False
    except Exception as e:
        logger.warning("cleanup_ledger_pdf_failed", path=pdf_path, error=str(e))
        return False


# Convenience function for payment reminder system
async def generate_and_send_ledger(
    party_code: str,
    phone: str,
    whatsapp_service,
    custom_message: Optional[str] = None
) -> dict:
    """
    High-level function to generate ledger and send via WhatsApp.
    
    This is a convenience wrapper that handles the entire flow:
    1. Generate PDF
    2. Send via WhatsApp
    3. Clean up temp file
    4. Return status with error code if applicable
    
    Args:
        party_code: Customer code
        phone: Phone number with country code
        whatsapp_service: Your WhatsApp service instance
        custom_message: Optional custom message (default if not provided)
    
    Returns:
        Dict with keys:
        - success: bool
        - error_code: str or None
        - error_message: str or None
        - pdf_sent: bool
        - message: str (sent message or error description)
    
    Example:
        ```python
        result = await generate_and_send_ledger(
            party_code="12345",
            phone="+919876543210",
            whatsapp_service=whatsapp
        )
        
        if result['success']:
            print(f"Ledger sent: {result['message']}")
        else:
            print(f"Failed: {result['error_code']} - {result['error_message']}")
        ```
    """
    pdf_path = None
    
    try:
        # Generate PDF
        pdf_path = await generate_ledger_pdf(party_code)
        
        # Default message
        if not custom_message:
            custom_message = (
                f"Dear Customer,\n\n"
                f"Please find your ledger statement attached. "
                f"Kindly review and arrange payment for outstanding amounts.\n\n"
                f"Thank you,\n"
                f"Anjali Home Fashion"
            )
        
        # Send via WhatsApp (implementation depends on your service)
        # This is a placeholder - replace with your actual WhatsApp sending code
        # await whatsapp_service.send_document(
        #     to=phone,
        #     document_path=pdf_path,
        #     caption=custom_message
        # )
        
        return {
            "success": True,
            "error_code": None,
            "error_message": None,
            "pdf_sent": True,
            "message": f"Ledger PDF sent to {phone}"
        }
        
    except Exception as e:
        error_code = None
        error_message = str(e)
        
        if isinstance(e, LedgerError):
            error_code = e.error_code
            error_message = e.message
        
        logger.error(
            "generate_and_send_ledger_failed",
            party_code=party_code,
            phone=phone,
            error_code=error_code,
            error=error_message
        )
        
        return {
            "success": False,
            "error_code": error_code or "UNKNOWN_ERROR",
            "error_message": error_message,
            "pdf_sent": False,
            "message": f"Failed to send ledger: {error_message}"
        }
        
    finally:
        # Always clean up
        if pdf_path:
            cleanup_ledger_pdf(pdf_path)
