# Busy WhatsApp Gateway - Quick Start

## One-Click Startup

Double-click **`Start-Gateway.bat`**

That's it! The tray icon appears near your clock.

## Using the Tray Icon

Right-click the green icon for menu options:

| Option | What it does |
|--------|--------------|
| **Status** | Show which servers are running |
| **Stop/Start Baileys** | Toggle WhatsApp server |
| **Open QR Code Page** | Connect WhatsApp Web |
| **Stop/Start FastAPI** | Toggle API server |
| **Open API Docs** | View API documentation |
| **Stop All & Exit** | Shutdown everything |

## Connecting WhatsApp

1. Right-click tray icon → "Open QR Code Page"
2. Open WhatsApp on your phone
3. Settings → Linked Devices → Link a Device
4. Scan the QR code
5. Done!

## URLs

- **QR Page**: http://localhost:3001/qr/page
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Busy Webhook**: `http://localhost:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}`

## Troubleshooting

**Icon not showing?** Check system tray overflow (^ arrow)

**Servers won't start?** Check if ports 3001 and 8000 are free

**Database errors?** Check `BDS_FILE_PATH` in `.env` file

**WhatsApp not sending?** Make sure QR code is scanned

## Files

| File | Purpose |
|------|---------|
| `Start-Gateway.bat` | **Run this** - Main launcher |
| `gateway-manager.py` | Tray manager (auto-runs) |
| `.env` | Your settings (database path, etc.) |
