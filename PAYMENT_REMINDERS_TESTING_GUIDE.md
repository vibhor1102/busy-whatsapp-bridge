# Payment Reminders Testing Guide

## Overview

The payment reminder system has been fully fixed and is ready to test. Here's how to use it:

## Prerequisites

1. **Database configured** - Busy .bds file path set in config
2. **WhatsApp provider configured** - Meta API credentials or Baileys enabled
3. **Start the gateway** - Run: `./Start-Gateway.py`

## Sample Templates Created

The following templates have been created in `%LOCALAPPDATA%\BusyWhatsappBridge\reminder_config.json`:

**Templates using {{1}}, {{2}}, {{3}} format:**

1. **Standard Reminder** (default)
   - {{1}} = Customer Name
   - {{2}} = Company Name (Anjali Home Fashion)
   - {{3}} = Amount Due

2. **Gentle Reminder**
   - More polite tone for valued customers

3. **Urgent Reminder**
   - For overdue payments

## Testing Step-by-Step

### 1. Start the Gateway

```bash
cd "C:\Program Files\BusyWhatsappBridge"
./Start-Gateway.py
```

### 2. Check System Health

```bash
curl "http://localhost:8000/api/v1/health"
```

Expected response:
```json
{
  "status": "healthy",
  "database_connected": true,
  "whatsapp": {
    "provider": "meta",
    "connected": true
  }
}
```

### 3. View Configuration

```bash
curl "http://localhost:8000/api/v1/reminders/config" | python -m json.tool
```

### 4. View Available Templates

```bash
curl "http://localhost:8000/api/v1/reminders/templates" | python -m json.tool
```

Expected: List of 3 templates (standard, gentle, urgent)

### 5. List Eligible Parties (with amount due > 0)

```bash
curl "http://localhost:8000/api/v1/reminders/parties" | python -m json.tool | head -100
```

This calculates:
- Closing Balance from ledger
- Recent Sales (within credit days from Master1.I2)
- Amount Due = Closing Balance - Recent Sales

### 6. View Specific Party Details

```bash
# Replace PARTY001 with an actual party code from your database
curl "http://localhost:8000/api/v1/reminders/parties/PARTY001" | python -m json.tool
```

### 7. Calculate Amount Due for a Party

```bash
curl -X POST "http://localhost:8000/api/v1/reminders/parties/PARTY001/calculate" | python -m json.tool
```

Shows detailed breakdown:
- Closing balance
- Credit days used
- Recent sales within credit period
- Calculation formula applied

### 8. Generate Ledger PDF

```bash
curl "http://localhost:8000/api/v1/reminders/parties/PARTY001/ledger" --output ledger_PARTY001.pdf
```

### 9. Enable Party for Automated Reminders

```bash
curl -X PUT "http://localhost:8000/api/v1/reminders/parties/PARTY001" \
  -H "Content-Type: application/json" \
  -d '{"permanent_enabled": true}'
```

### 10. Send Manual Batch Reminders

**Send to specific parties:**
```bash
curl -X POST "http://localhost:8000/api/v1/reminders/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "party_codes": ["PARTY001", "PARTY002"],
    "template_id": "standard"
  }'
```

**Response:**
```json
{
  "status": "success",
  "batch_id": "uuid-here",
  "message": "Reminders queued for 2 parties"
}
```

### 11. Check Scheduler Status

```bash
curl "http://localhost:8000/api/v1/reminders/scheduler/status" | python -m json.tool
```

### 12. Configure Automated Schedule

```bash
curl -X PUT "http://localhost:8000/api/v1/reminders/config/schedule" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "weekly",
    "day_of_week": 1,
    "time": "10:00",
    "timezone": "Asia/Kolkata",
    "batch_size": 50,
    "delay_between_messages": 5
  }'
```

### 13. Start Scheduler Manually

```bash
curl -X POST "http://localhost:8000/api/v1/reminders/scheduler/start"
```

### 14. Trigger Manual Run (Sends to all enabled parties)

```bash
curl -X POST "http://localhost:8000/api/v1/reminders/scheduler/trigger"
```

### 15. View Statistics

```bash
curl "http://localhost:8000/api/v1/reminders/stats" | python -m json.tool
```

## Key Fixed Issues

1. **SQL Injection Fixed** - All database queries now use parameterized queries
2. **Balance Calculation Fixed** - Running balance now correctly calculated
3. **Bi-weekly Scheduling Fixed** - Uses proper 14-day intervals instead of broken ISO week logic
4. **API Paths Fixed** - Endpoints now match documentation (`/batch`, `/active`)
5. **Temp File Cleanup** - PDF files properly cleaned up after queuing
6. **Windows Path Fixed** - Uses `tempfile.gettempdir()` instead of hardcoded `/tmp`
7. **Template Variables** - Added `currency_symbol` to available variables
8. **Vue State Management** - Fixed direct mutation of computed properties

## Template Variables

All templates support these variables:

- `{customer_name}` - Party name from Master1
- `{company_name}` - Your company name (Anjali Home Fashion)
- `{amount_due}` - Calculated amount due
- `{currency_symbol}` - ₹ (or configured symbol)
- `{credit_days}` - Credit days from Master1.I2
- `{contact_phone}` - Your contact phone
- `{party_code}` - Party code
- `{phone}` - Party phone number

**Note:** Templates use format `{{1}}`, `{{2}}`, `{{3}}` internally but the system converts these automatically based on the mapping:
- {{1}} = {customer_name}
- {{2}} = {company_name}
- {{3}} = {amount_due}

## Viewing Logs

Monitor the logs to see reminder operations:

```bash
# In another terminal
tail -f "%LOCALAPPDATA%\BusyWhatsappBridge\logs\gateway_$(date +%Y%m%d).log"
```

Look for:
- `reminder_queued` - Message queued successfully
- `batch_completed` - Batch finished processing
- `scheduled_reminders_completed` - Automated run finished

## Troubleshooting

### "No eligible parties found"
- Check if database connection is working
- Verify parties have positive closing balance
- Check if credit days are set in Master1.I2

### "Template not found"
- Verify templates exist in config
- Check `reminder_config.json` in AppData

### "Scheduler not starting"
- Check scheduler status endpoint
- Verify schedule configuration is valid
- Check logs for errors

### "Messages not sending"
- Verify WhatsApp provider is connected
- Check queue status: `curl "http://localhost:8000/api/v1/queue/status"`
- Check message queue logs

## Dashboard Access

Even though the dashboard build has issues, you can still use the API directly with the commands above.

To access the API documentation:
```
http://localhost:8000/docs
```

## Configuration File Location

All reminder settings are stored in:
```
%LOCALAPPDATA%\BusyWhatsappBridge\reminder_config.json
```

You can edit this file directly or use the API endpoints to update configuration.