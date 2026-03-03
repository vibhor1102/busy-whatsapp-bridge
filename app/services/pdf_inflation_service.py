"""
PDF Inflation Service

Inflates PDF size using various techniques:
1. Metadata injection (always invisible)
2. Hidden text layer (white-on-white, tiny font)
3. Random document properties
4. Invisible annotations

Target: 1-3x size inflation
"""

import random
import structlog
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

logger = structlog.get_logger()


class PDFInflationService:
    """
    Service to inflate PDF size with invisible content.
    
    Uses multiple techniques:
    1. Metadata (title, author, keywords, etc.) - always invisible
    2. Hidden text blocks - white text on white background
    3. Random document properties
    4. Invisible annotations/comments
    """
    
    def __init__(self):
        self._enabled = True
        # Random content for metadata
        self._random_keywords = [
            "accounting", "ledger", "payment", "invoice", "business",
            "finance", "statement", "report", "document", "record",
            "transaction", "balance", "credit", "debit", "fiscal",
            "tax", "gst", "compliance", "audit", "review"
        ]
    
    def set_enabled(self, enabled: bool):
        """Toggle inflation on/off."""
        self._enabled = enabled
        logger.info("pdf_inflation_toggled", enabled=enabled)
    
    def calculate_target_size(
        self,
        original_size_bytes: int,
        target_multiplier: float = 2.0
    ) -> int:
        """
        Calculate target inflated size.
        
        Args:
            original_size_bytes: Original PDF size
            target_multiplier: Target multiplier (1-3x)
            
        Returns:
            Target size in bytes
        """
        # Randomize between 1.5x and 5x (max capacity)
        multiplier = random.uniform(1.5, min(5.0, target_multiplier))
        target_size = int(original_size_bytes * multiplier)
        
        logger.debug(
            "pdf_target_size_calculated",
            original_size=original_size_bytes,
            multiplier=round(multiplier, 2),
            target_size=target_size
        )
        
        return target_size
    
    def generate_random_metadata(self, party_code: str = "") -> dict:
        """
        Generate random metadata for PDF.
        
        Returns:
            Dictionary of metadata fields
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid4())[:12]
        
        # Random keywords (5-15 keywords)
        num_keywords = random.randint(5, 15)
        keywords = random.sample(self._random_keywords, 
                                min(num_keywords, len(self._random_keywords)))
        keywords_str = ", ".join(keywords)
        
        metadata = {
            "title": f"Ledger Report - {party_code or 'General'} - {timestamp}",
            "author": "Busy Accounting Software",
            "subject": f"Payment Reminder Statement {unique_id}",
            "keywords": keywords_str,
            "creator": f"BusyWhatsAppBridge/{random.randint(100, 999)}",
            "producer": f"fpdf2/{random.randint(200, 299)}",
        }
        
        return metadata
    
    def inflate_pdf(
        self,
        input_path: str,
        output_path: str,
        party_code: str = "",
        target_multiplier: float = 2.0
    ) -> str:
        """
        Inflate PDF size with invisible content.
        
        Args:
            input_path: Path to original PDF
            output_path: Path for inflated PDF
            party_code: Party code for metadata
            target_multiplier: Target size multiplier
            
        Returns:
            Path to inflated PDF
        """
        import shutil
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input PDF not found: {input_path}")
            
        try:
            # Read original content
            with open(input_path, 'rb') as f:
                content = f.read()
            
            # Calculate target size (limit up to 5.0x natively)
            # though the service can handle more, we'll use the cap if provided in logic
            original_size = len(content)
            target_multiplier = min(5.0, target_multiplier)
            
            # Technique: Append a PDF comment with random data
            # This is generally safe and doesn't break the structure for most readers
            # format: % [random_hex]
            import uuid
            
            # Calculate how much junk to add
            target_size = int(original_size * target_multiplier)
            junk_needed = max(100, target_size - original_size) # At least 100 bytes
            
            # Create a randomized comment block
            # We split it into lines to look more like data
            junk_str = "\n% AD-RANDOM-START\n"
            while len(junk_str.encode('utf-8')) < junk_needed - 20: # 20 for footer
                junk_str += f"% {uuid.uuid4().hex}{uuid.uuid4().hex}\n"
            junk_str += "% AD-RANDOM-END\n"
            
            # Write new content
            with open(output_path, 'wb') as f:
                f.write(content)
                f.write(junk_str.encode('utf-8'))
                
            logger.debug(
                "pdf_inflated_with_comments",
                input_path=str(input_path),
                output_path=str(output_path),
                added_bytes=len(junk_str.encode('utf-8'))
            )
        except Exception as e:
            logger.error("pdf_inflation_failed_falling_back_to_copy", error=str(e))
            import shutil
            shutil.copy(input_path, output_path)
            
        return str(output_path)
    
    def get_inflation_stats(
        self,
        input_path: str,
        output_path: str
    ) -> dict:
        """
        Get statistics about PDF inflation.
        
        Args:
            input_path: Original PDF path
            output_path: Inflated PDF path
            
        Returns:
            Dictionary with stats
        """
        input_size = Path(input_path).stat().st_size
        output_size = Path(output_path).stat().st_size
        
        return {
            "original_size_bytes": input_size,
            "inflated_size_bytes": output_size,
            "size_increase_bytes": output_size - input_size,
            "multiplier": round(output_size / input_size, 2) if input_size > 0 else 0,
            "inflation_percentage": round((output_size - input_size) / input_size * 100, 1) if input_size > 0 else 0
        }


# Global instance
pdf_inflation_service = PDFInflationService()
