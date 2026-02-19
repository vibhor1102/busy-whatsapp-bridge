#!/usr/bin/env python3
"""
Example: Send template with PDF
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import httpx

load_dotenv()

async def send_template_with_pdf():
    token = os.getenv("META_ACCESS_TOKEN")
    phone_id = os.getenv("META_PHONE_NUMBER_ID")
    recipient = "919350561606"
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Template with PDF - this requires a custom template with DOCUMENT header
    # You need to create this template first in Meta dashboard
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": "invoice_notification",  # Your custom template name
            "language": {"code": "en_US"},
            "components": [
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "document",
                            "document": {
                                "link": "https://example.com/path/to/invoice.pdf",
                                "filename": "Invoice_001.pdf"
                            }
                        }
                    ]
                },
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": "INV-001"  # Invoice number variable
                        }
                    ]
                }
            ]
        }
    }
    
    print("Example payload for sending template with PDF:")
    print(json.dumps(payload, indent=2))
    print()
    print("NOTE: You need to create this template in Meta dashboard first!")
    print("URL: https://business.facebook.com/wa/manage/message-templates/")

if __name__ == "__main__":
    asyncio.run(send_template_with_pdf())
