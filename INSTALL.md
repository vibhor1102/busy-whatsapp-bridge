# Busy WhatsApp Gateway - Installation Guide

## Prerequisites

### 1. Required Software
- **Python 3.9-3.13 (32-bit)** - CRITICAL: Must be 32-bit for ODBC compatibility
- **Microsoft Access Database Engine 2010/2016 (32-bit)**
- **Busy Accounting Software** configured for SMS/WhatsApp

### 2. Download Links
- Python 32-bit: https://www.python.org/downloads/windows/
- Access Database Engine: https://www.microsoft.com/en-us/download/details.aspx?id=54920

## Installation Steps

### Step 1: Install Python 32-bit

1. Download Python 3.9+ 32-bit installer from python.org
2. Run installer and check:
   - ☑ Add Python to PATH
   - ☑ Install pip
   - ☑ Install for all users (optional)
3. Verify installation:
   ```cmd
   python --version
   python -c "import platform; print(platform.architecture())"
   ```
   Should show: `('32bit', 'WindowsPE')`

### Step 2: Install Access Database Engine

1. Download Microsoft Access Database Engine 2010 or 2016 (32-bit)
2. Run the installer
3. Verify ODBC driver is installed:
   ```cmd
   # Open ODBC Data Sources (32-bit)
   %windir%\syswow64\odbcad32.exe
   ```
   Look for: `Microsoft Access Driver (*.mdb, *.accdb)`

### Step 3: Setup the Gateway

1. Open terminal in project folder:
   ```cmd
   cd "C:\Path\To\Busy Whatsapp Application"
   ```

2. Create virtual environment (recommended):
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```cmd
   copy .env.example .env
   notepad .env
   ```

5. Edit `.env` file with your settings:
   ```ini
   BDS_FILE_PATH=C:\Busy\Data\YourCompany.bds
   BDS_PASSWORD=ILoveMyINDIA
WHATSAPP_PROVIDER=webhook
WEBHOOK_URL=http://localhost:3000/send
   ```

### Step 4: Test Database Connection

Run this PowerShell script to verify ODBC connectivity:

```powershell
# Save as test-odbc.ps1
$conn = New-Object System.Data.Odbc.OdbcConnection
$conn.ConnectionString = "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Busy\Data\YourCompany.bds;PWD=ILoveMyINDIA"
try {
    $conn.Open()
    Write-Host "✓ Connection successful!"
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "SELECT COUNT(*) FROM Master1"
    $result = $cmd.ExecuteScalar()
    Write-Host "✓ Master1 table has $result records"
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)"
} finally {
    $conn.Close()
}
```

Run with:
```powershell
# Use 32-bit PowerShell
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe -File test-odbc.ps1
```

### Step 5: Start the Server

```cmd
start-server.bat
```

Or manually:
```cmd
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server will start at: http://localhost:8000

### Step 6: Test the API

In another terminal:
```cmd
run-tests.bat
```

Or:
```cmd
python tests/test_webhook.py
```

## Busy Software Configuration

### Configure SMS/WhatsApp Provider

1. Open Busy Accounting Software
2. Go to: **Configuration → SMS Configuration → Config**
3. Select: **Custom SMS Provider**
4. Paste this URL template:

```
http://YOUR_SERVER_IP:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

**Parameter Mapping:**
- `{MobileNo}` → Customer's phone number (e.g., +919876543210)
- `{Message}` → Message text from invoice template
- `{AttachmentURL}` → PDF URL from Busy Cloud (BDEP)

### Configure Invoice Template

1. Go to: **Configuration → SMS Configuration → Message Templates**
2. Create template for Sales Invoice:
   ```
   Dear {PartyName}, your invoice {VchNo} dated {VchDate} for Rs. {NetAmount} is ready. Please find the PDF attached.
   ```

### Test Integration

1. Create a test Sales Invoice in Busy
2. Save the invoice
3. Check if webhook is triggered:
   - Check server logs
   - WhatsApp message should be sent

## Troubleshooting

### Issue: "Driver not found"
**Solution:** Install 32-bit Access Database Engine, not 64-bit

### Issue: "Architecture mismatch"
**Solution:** Use 32-bit Python, not 64-bit

### Issue: "Database password incorrect"
**Solution:** Verify BDS_PASSWORD in .env matches Busy database password

### Issue: WhatsApp messages not sending
**Solution:** 
1. Check Twilio/Meta credentials in .env
2. Verify phone number format (include country code)
3. Check Twilio console for message logs

### Issue: "Module not found"
**Solution:** 
```cmd
pip install -r requirements.txt
```

## API Documentation

Once server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture Overview

```
Busy Accounting → HTTP GET/POST → FastAPI Gateway → ODBC → .bds Database
                                         ↓
                                    WhatsApp API → Customer
```

## Support

For issues or questions, please check:
1. Server logs in terminal
2. API documentation at /docs
3. Test with provided test scripts

## Security Notes

- Never commit `.env` file to version control
- Use strong password for production
- Consider HTTPS for production deployment
- Restrict API access with authentication if needed
