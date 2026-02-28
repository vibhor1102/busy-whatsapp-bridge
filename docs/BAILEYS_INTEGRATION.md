# Baileys Integration for Payment Reminders - Summary

## Overview
Successfully integrated Baileys (WhatsApp Web) as the sole provider for payment reminders. Meta Cloud API, Evolution API, and Webhook providers have been completely removed.

## Changes Made

### 1. Provider System (app/services/whatsapp.py)
- **Removed**: `MetaProvider`, `EvolutionProvider`, `WebhookProvider` classes
- **Kept**: Only `BaileysProvider` remains
- **Added**: Comments with TODOs for future re-integration if needed
- **Updated**: `get_whatsapp_provider()` factory to only support "baileys"

### 2. Configuration (app/config.py)
- **Removed**: Meta settings (`meta_api_version`, `meta_phone_number_id`, `meta_access_token`, `meta_business_id`, `meta_webhook_verify_token`)
- **Removed**: Webhook settings (`webhook_url`, `webhook_auth_token`)
- **Changed**: Default `WHATSAPP_PROVIDER` to "baileys"
- **Changed**: Default `REMINDER_PROVIDER` to "baileys"
- **Updated**: `conf.json.example` to reflect new defaults

### 3. API Endpoints (app/main.py)
- **Removed**: Meta webhook endpoints (verification, status updates, diagnostics)
- **Replaced**: With stub endpoints that return "removed" error messages
- **Updated**: Health check to only check Baileys connection
- **Updated**: Config validation to only accept "baileys" provider

### 4. Database Layer (app/database/message_queue.py)
- **Removed**: `meta_webhook_diagnostics` and `meta_webhook_errors` tables
- **Removed**: Meta webhook methods (`record_meta_webhook_verify`, `record_meta_webhook_post`, `record_meta_webhook_error`, `get_meta_webhook_status`)

### 5. Reminder Service (app/services/reminder_service.py)
- **Simplified**: `_resolve_delivery_provider()` to only use Baileys
- **Updated**: Media attachment logic to only support Baileys

### 6. Queue Service (app/services/queue_service.py)
- **Removed**: Meta-specific "accepted" delivery status handling
- **Kept**: Local file path handling for PDF attachments

### 7. Baileys Server (baileys-server/)
- **Enhanced**: `sendMedia()` method in `baileys-client.js` to handle local file paths
- **Supports**: Both HTTP URLs and local file paths for PDF attachments

### 8. Tests (tests/)
- **Updated**: `test_phone_delivery.py` to use Baileys instead of Meta
- **Removed**: Meta webhook diagnostic tests

### 9. Documentation
- **Updated**: `README.md` to reflect Baileys-only configuration
- **Updated**: `conf.json.example` with new defaults
- **Created**: `test-reminder-baileys.py` for integration testing

## How It Works

### Payment Reminder Flow
1. **Generate Ledger PDF**: `reminder_service.py` generates PDF using `ledger_pdf_service.py`
2. **Queue Message**: PDF path is saved to `message_queue` table with provider="baileys"
3. **Process Queue**: `queue_service.py` processes queued messages
4. **Send via Baileys**: `BaileysProvider` sends message with PDF attachment to Baileys server
5. **Baileys Server**: Receives local file path, reads PDF, sends via WhatsApp Web
6. **Cleanup**: `queue_service.py` deletes temporary PDF file after sending

### Baileys Server Endpoints
- `GET /status` - Check connection status
- `GET /qr` - Get QR code for authentication
- `GET /qr/page` - Web UI for QR scanning
- `POST /send` - Send text message
- `POST /send-media` - Send document/PDF
- `POST /restart` - Restart Baileys client
- `POST /logout` - Logout from WhatsApp

### Configuration
```json
{
  "whatsapp": {
    "provider": "baileys",
    "default_country_code": "91"
  },
  "baileys": {
    "server_url": "http://localhost:3001",
    "enabled": true,
    "auto_start": true
  },
  "reminders": {
    "provider": "baileys"
  }
}
```

## Testing

### Quick Test
```bash
# Start Baileys server
cd baileys-server && npm start

# Authenticate WhatsApp
# Visit: http://localhost:3001/qr/page
# Scan QR code with WhatsApp mobile app

# Test integration
python test-reminder-baileys.py
```

### Manual Test via API
```bash
# Check Baileys status
curl http://localhost:8000/api/v1/baileys/status

# Send test reminder
curl -X POST http://localhost:8000/api/v1/reminders/batch \
  -H "Content-Type: application/json" \
  -d '{"party_codes": ["TEST001"], "template_id": "standard"}'
```

## Migration Notes

### For Existing Users
If you had Meta or Webhook configured:
1. Update `conf.json`: Change `whatsapp.provider` to "baileys"
2. Update `reminders.provider` to "baileys"
3. Start Baileys server: `cd baileys-server && npm start`
4. Authenticate: Visit `http://localhost:3001/qr/page`
5. No database migration needed - queue system is provider-agnostic

### Backward Compatibility
- Provider "baileys" is the only valid option
- Any other provider name will log a warning and fall back to Baileys
- Existing queued messages with other providers will still be processed (fallback to Baileys)

## Future Enhancements (TODO)
Comments in code indicate these may be re-added via Baileys:
- Meta Cloud API (via Baileys or direct integration)
- Evolution API (if needed)
- Webhook provider (for custom integrations)

## Architecture
```
Busy Software → FastAPI App → Reminder Service → Queue Service
                                               ↓
Database (Ledger Data)                        Message Queue
                                               ↓
Ledger PDF Service ← PDF File              Baileys Provider
                                               ↓
                                        Baileys Server (Node.js)
                                               ↓
                                        WhatsApp Web (Baileys)
                                               ↓
                                        Customer Phone
```

## Benefits of Baileys-Only
1. **No API Costs** - Free WhatsApp Web usage
2. **No Rate Limits** - Send unlimited messages
3. **Local PDF Handling** - Direct file access, no upload needed
4. **Simple Setup** - No Meta Business account required
5. **Full Control** - No third-party dependencies

## Support
- Check Baileys status: `http://localhost:8000/api/v1/baileys/status`
- View QR code: `http://localhost:8000/baileys/qr`
- Test connection: `python test-reminder-baileys.py`
