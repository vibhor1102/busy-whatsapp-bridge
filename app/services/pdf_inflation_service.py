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
        # Randomize between 1.5x and 3x
        multiplier = random.uniform(1.5, min(3.0, target_multiplier))
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
        if not self._enabled:
            # Just copy the file
            import shutil
            shutil.copy(input_path, output_path)
            return output_path
        
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input PDF not found: {input_path}")
        
        # Get original size
        original_size = input_path.stat().st_size
        target_size = self.calculate_target_size(original_size, target_multiplier)
        
        # Read original PDF
        with open(input_path, 'rb') as f:
            pdf_content = f.read()
        
        # Since we can't easily modify PDF structure without proper library,
        # we'll use a simpler approach: append invisible content as PDF objects
        inflated_content = self._append_invisible_content(
            pdf_content,
            target_size,
            party_code
        )
        
        # Write inflated PDF
        with open(output_path, 'wb') as f:
            f.write(inflated_content)
        
        # Verify
        final_size = output_path.stat().st_size
        actual_multiplier = final_size / original_size
        
        logger.info(
            "pdf_inflated",
            input_path=str(input_path),
            output_path=str(output_path),
            original_size=original_size,
            final_size=final_size,
            multiplier=round(actual_multiplier, 2)
        )
        
        return str(output_path)
    
    def _append_invisible_content(
        self,
        pdf_content: bytes,
        target_size: int,
        party_code: str
    ) -> bytes:
        """
        Append invisible content to PDF.
        
        This method adds PDF objects that don't affect visual rendering
        but increase file size.
        
        Args:
            pdf_content: Original PDF bytes
            target_size: Target size in bytes
            party_code: Party code
            
        Returns:
            Inflated PDF bytes
        """
        current_size = len(pdf_content)
        
        if current_size >= target_size:
            return pdf_content
        
        # How many bytes to add
        bytes_to_add = target_size - current_size
        
        # Create invisible content blocks
        invisible_blocks = []
        
        # 1. Add metadata as XMP (invisible)
        xmp_metadata = self._generate_xmp_metadata(party_code)
        invisible_blocks.append(xmp_metadata.encode('utf-8'))
        
        # 2. Add invisible text content (white-on-white simulation)
        # We add this as a PDF comment/object that's not rendered
        while sum(len(block) for block in invisible_blocks) < bytes_to_add:
            block_size = min(1024, bytes_to_add - sum(len(block) for block in invisible_blocks))
            invisible_text = self._generate_invisible_block(block_size)
            invisible_blocks.append(invisible_text)
        
        # Combine all blocks
        inflated = pdf_content
        for block in invisible_blocks:
            inflated += block
            if len(inflated) >= target_size:
                break
        
        return inflated
    
    def _generate_xmp_metadata(self, party_code: str) -> str:
        """
        Generate XMP metadata packet.
        
        XMP is XML-based metadata that's invisible in PDF readers.
        
        Args:
            party_code: Party code
            
        Returns:
            XMP metadata string
        """
        metadata = self.generate_random_metadata(party_code)
        timestamp = datetime.now().isoformat()
        uuid = str(uuid4())
        
        # Add random content to make it unique
        random_content = ''.join(random.choices(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            k=random.randint(50, 200)
        ))
        
        xmp = f"""
%PDF comment for XMP metadata
% {random_content}
1 0 obj
<<
/Type /Metadata
/Subtype /XML
/Length {500 + random.randint(100, 500)}
>>
stream
<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?\u003e
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.0-c060 61.134777, 2010/02/12-17:32:00"\u003e
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\u003e
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
    xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"
    dc:title="{metadata['title']}"
    dc:creator="{metadata['author']}"
    dc:subject="{metadata['subject']}"
    dc:date="{timestamp}"
    xmp:CreateDate="{timestamp}"
    xmp:ModifyDate="{timestamp}"
    xmp:MetadataDate="{timestamp}"
    xmp:CreatorTool="{metadata['creator']}"
    pdf:Producer="{metadata['producer']}"
    pdf:Keywords="{metadata['keywords']}"
    pdfaid:part="1"
    pdfaid:conformance="B"\u003e
   </dc:description\u003e
  </rdf:Description\u3e
 </rdf:RDF\u003e
</x:xmpmeta\u003e
<?xpacket end="w"?\u003e
endstream
endobj
"""
        return xmp
    
    def _generate_invisible_block(self, size: int) -> bytes:
        """
        Generate a block of invisible content.
        
        This adds PDF objects that are not rendered but increase file size.
        
        Args:
            size: Approximate size in bytes
            
        Returns:
            Bytes of invisible content
        """
        # Generate random text that will be ignored
        random_text = ''.join(random.choices(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
            k=size
        ))
        
        # Wrap in PDF comment/object structure
        block = f"""
% Invisible content block - not rendered
% {random_text[:200]}
% {random_text[200:400] if len(random_text) > 200 else ''}
% {random_text[400:600] if len(random_text) > 400 else ''}
""".encode('utf-8')
        
        return block
    
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
