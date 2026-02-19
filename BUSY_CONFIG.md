# Busy SMS Provider Configuration Guide

## Overview

This guide shows you how to configure Busy Accounting Software to send invoice notifications to your custom API gateway.

## Prerequisites

Before configuring Busy, ensure:
1. Backend server is running (verify with `test-backend.py`)
2. You know your server's IP address
3. Server is accessible from the machine running Busy

## Step-by-Step Configuration

### Step 1: Open Busy Configuration

1. Open **Busy Accounting Software**
2. Go to: **Configuration → SMS Configuration → Config**

### Step 2: Select Provider Type

1. In the SMS Configuration window:
   - **SMS API Provider**: Select `Custom`
   - **Service Provider**: Select `Other`

### Step 3: Configure API URL

Enter this URL in the **Config** field:

```
http://YOUR_SERVER_IP:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

**Replace `YOUR_SERVER_IP` with:**
- If running on same machine: `localhost` or `127.0.0.1`
- If running on different machine: The actual IP address (e.g., `192.168.1.100`)

**Example:**
```
http://192.168.1.100:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

### Step 4: Configure Message Template (Optional)

1. Go to: **Configuration → SMS Configuration → Message Templates**
2. Select voucher type (e.g., Sales Invoice)
3. Create your message template using Busy variables:

```
Dear {PartyName}, your invoice {VchNo} dated {VchDate} for Rs. {NetAmount} is ready. Please check the attachment.
```

**Available Variables:**
- `{MobileNo}` - Customer mobile number
- `{PartyName}` - Party/Customer name
- `{VchNo}` - Voucher/Invoice number
- `{VchDate}` - Voucher date
- `{NetAmount}` - Invoice amount
- `{Message}` - Full message text
- `{AttachmentURL}` - URL to invoice PDF

### Step 5: Enable SMS for Voucher Type

1. Go to: **Configuration → SMS Configuration → Voucher Wise**
2. Find your voucher type (e.g., Sales Invoice)
3. Check the box to enable SMS for that voucher
4. Select the message template you created

### Step 6: Test the Configuration

1. Create a new Sales Invoice
2. Enter a customer with a valid mobile number
3. Save the invoice
4. Check if the webhook is triggered:
   - Look at your server console (should show incoming request)
   - Check if database is queried (if customer exists)

## Troubleshooting

### "Connection refused" error in Busy

**Problem:** Busy cannot connect to your server

**Solutions:**
1. Verify server is running: Open browser to `http://YOUR_IP:8000/api/v1/health`
2. Check Windows Firewall: Run `configure-firewall.bat` on server
3. Verify IP address is correct
4. Ensure both machines are on same network

### Request reaches server but no response

**Problem:** Server receives request but Busy shows error

**Solutions:**
1. Check server logs for errors
2. Verify database connection is working
3. Test manually with browser: 
   ```
   http://YOUR_IP:8000/api/v1/send-invoice?phone=+919876543210&msg=Test&pdf_url=http://test.com/1.pdf
   ```

### Database query fails

**Problem:** Server can't read customer data

**Solutions:**
1. Check `.env` file has correct `BDS_FILE_PATH`
2. Verify database password is correct
3. Ensure Busy is not locking the database file
4. Check if phone number format matches Master1 table

## Verification Checklist

After configuration, verify:

- [ ] Server is running and accessible
- [ ] Busy Config URL is correct
- [ ] Message template is set up
- [ ] Voucher type has SMS enabled
- [ ] Test invoice triggers webhook
- [ ] Server logs show request received
- [ ] Customer data is queried from database (if customer exists)

## Next Steps

Once frontend-backend integration is working:

1. **Monitor logs** during testing to see actual requests
2. **Verify parameters** are being passed correctly
3. **Test with different customers** to ensure phone number matching works
4. **Add WhatsApp messaging support** (Twilio/Meta integration)

## API Reference for Busy

When Busy sends a webhook, it makes a GET request to:

```
GET /api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

**Parameters:**
- `phone` - Customer mobile number (e.g., +919876543210)
- `msg` - Message text from template
- `pdf_url` - URL to invoice PDF on Busy cloud

**What the server does:**
1. Receives the request
2. Looks up customer in Master1 table (if phone matches)
3. Logs the request
4. Returns success/error response to Busy

**Current behavior:**
- ✓ Request is received and logged
- ✓ Customer lookup works (if phone number in database)
- ✓ Response sent back to Busy
- ⚠ WhatsApp messaging NOT yet implemented (Phase 2)

## Testing Without Busy

You can test the integration without Busy using curl or browser:

```bash
# Test endpoint
curl "http://localhost:8000/api/v1/send-invoice?phone=+919876543210&msg=Test%20message&pdf_url=http://example.com/test.pdf"
```

Or open in browser:
```
http://localhost:8000/api/v1/send-invoice?phone=+919876543210&msg=Test&pdf_url=http://test.com/1.pdf
```

This will show you exactly what Busy will experience.
