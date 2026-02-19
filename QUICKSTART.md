# Quick Reference Guide

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env
# Edit .env with your settings

# 3. Start server
start-server.bat

# 4. Test
run-tests.bat
```

## 📋 Busy URL Template

**Paste this in Busy SMS Configuration:**

```
http://YOUR_SERVER_IP:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/send-invoice` | GET/POST | Receive Busy webhook |
| `/api/v1/parties/{phone}` | GET | Get party by phone |
| `/api/v1/vouchers/{party_code}` | GET | Get vouchers for party |
| `/api/v1/parties/search/{term}` | GET | Search parties |

## 🧪 Testing

```bash
# Test all endpoints
python tests/test_webhook.py

# Test specific endpoint
python tests/test_webhook.py --phone "+919876543210"

# Skip WhatsApp sending (database tests only)
python tests/test_webhook.py --skip-send
```

## ⚙️ Configuration (.env)

```ini
# Required
BDS_FILE_PATH=C:\Busy\Data\YourCompany.bds
BDS_PASSWORD=ILoveMyINDIA

# WhatsApp Provider
WHATSAPP_PROVIDER=twilio

# Twilio (if using Twilio)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=whatsapp:+1234567890
```

## 📞 Phone Number Format

- **With country code:** `+919876543210`
- **With whatsapp: prefix:** `whatsapp:+919876543210`

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Driver not found | Install 32-bit Access Database Engine |
| Architecture mismatch | Use 32-bit Python |
| Connection refused | Check if server is running |
| Party not found | Verify phone number in Master1 table |

## 📁 Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database/
│   │   └── connection.py    # ODBC database handler
│   ├── models/
│   │   └── schemas.py       # Data models
│   └── services/
│       ├── busy_handler.py  # Busy webhook processor
│       └── whatsapp.py      # WhatsApp providers
├── tests/
│   └── test_webhook.py      # Test suite
├── .env.example             # Environment template
├── requirements.txt         # Dependencies
└── start-server.bat         # Server startup script
```

## 📊 Database Schema

### Master1 (Parties)
- `Code`, `Name`, `PrintName`
- `Phone`, `Email`
- `Address1-4`, `GSTNo`

### Tran1 (Vouchers)
- `VchCode`, `VchType`, `VchNo`
- `VchDate`, `PartyCode`, `NetAmt`

### Tran2 (Voucher Items)
- `VchCode`, `SrNo`, `ItemCode`
- `Qty`, `Rate`, `Amount`
