import asyncio
import os
import sys
import structlog

# Add project root to path
sys.path.append(os.getcwd())

from app.services.queue_service import queue_service
from app.database.message_queue import message_db

logger = structlog.get_logger()

async def verify():
    print("=== Testing Invoice Anti-Detection ===")
    
    phone = "917206366664"
    message = "Test invoice message for anti-detection verification."
    # Use a small public PDF
    pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    
    # Enqueue as 'busy' source
    print(f"Enqueuing test message to {phone}...")
    await queue_service.enqueue_invoice_notification(
        phone=phone,
        message=message,
        pdf_url=pdf_url,
        source="busy"
    )
    
    # Get the message ID
    pending = message_db.get_pending_messages(limit=1)
    if not pending:
        print("Error: Message not enqueued!")
        return
        
    msg = pending[-1] # Take the latest one
    print(f"Message ID: {msg['id']} enqueued with source: {msg['source']}")
    
    # We will process it and monitor logs
    queue_service._processing = True
    print("\nStarting process_queue_batch...")
    print("NOTE: Expecting 3-10 seconds startup delay, then reading delay, then typing indicator.")
    
    # We need to mock provider.send_message to avoid actual WhatsApp sending if possible,
    # or just let it fail/succeed if Baileys is running.
    # For verification of logic, we mostly care about the delays and inflation.
    
    count = await queue_service.process_queue_batch(batch_size=1)
    print(f"\nProcessing complete. Processed {count} messages.")
    
    # Check if cleaned up
    from app.config import get_roaming_appdata_path
    temp_dir = get_roaming_appdata_path() / "data" / "temp_media"
    if temp_dir.exists():
        files = list(temp_dir.glob("*"))
        print(f"Temp media files remaining: {len(files)}")
        for f in files:
            print(f" - {f.name}")
    else:
        print("Temp media directory does not exist (cleaned up or never created).")

if __name__ == "__main__":
    asyncio.run(verify())
