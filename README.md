# Busy Accounting WhatsApp/SMS Integration Gateway

**Production-Ready Windows Service for Busy Accounting Software Integration**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-teal.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 🎯 Overview

Enterprise-grade middleware that seamlessly integrates **Busy Accounting Software** with **WhatsApp/SMS** providers. Designed to run as a **Windows Service** with automatic startup, crash recovery, and comprehensive logging.

### ✨ Key Features

- **🔧 Native Windows Service** - Auto-start on boot, runs in background
- **📊 32-bit ODBC Support** - Full compatibility with Busy .bds MS Access databases
- **📱 Multi-Provider** - Twilio, Meta Business API, or custom webhook
- **🔒 Production Ready** - Structured logging, error handling, health monitoring
- **⚡ High Performance** - Async FastAPI with connection pooling
- **📈 Scalable** - Event-driven architecture with webhook support

## 🏗️ Architecture

```
┌─────────────────┐     HTTP GET/POST      ┌──────────────────┐
│   Busy Software │ ─────────────────────→ │  Windows Service │
│   (Invoice Save)│                        │   (FastAPI App)  │
└─────────────────┘                        └────────┬─────────┘
                                                     │
                          ┌────────────────────────┼────────────────────────┐
                          │                        │                        │
                          ▼                        ▼                        ▼
                   ┌──────────────┐      ┌──────────────┐        ┌──────────────┐
                   │   Database   │      │   WhatsApp   │        │    Logs      │
                   │  (MS Access) │      │   Provider   │        │   (Event/    │
                   │   (.bds)     │      │ (Twilio/Meta)│        │    File)     │
                   └──────────────┘      └──────────────┘        └──────────────┘
```

## 🚀 Quick Start (Production)

### Prerequisites

- **Windows 10/11 or Server 2016+**
- **Python 3.9-3.13 (32-bit)** ⚠️ *Required for ODBC*
- **Microsoft Access Database Engine 2010/2016 (32-bit)**
- **Administrator privileges** (for service installation)

### 1. Installation

```cmd
# Download and extract the project
cd "C:\Busy WhatsApp Gateway"

# Run production setup (as Administrator)
setup-production.bat
```

### 2. Configuration

Edit `.env` file with your settings:

```ini
# Database (REQUIRED)
BDS_FILE_PATH=C:\Busy\Data\YourCompany.bds
BDS_PASSWORD=ILoveMyINDIA

# WhatsApp Provider (REQUIRED)
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

### 3. Install Windows Service

```cmd
# Interactive menu
manage-service.bat

# Or command line
python app\service_wrapper.py install
python app\service_wrapper.py start
```

### 4. Configure Busy Software

**In Busy Accounting Software:**

1. Go to: **Configuration → SMS Configuration → Config**
2. Select: **Custom SMS Provider**
3. Enter URL:

```
http://localhost:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

### 5. Verify Installation

```cmd
# Check service status
python app\service_wrapper.py status

# Test API
run-tests.bat

# View logs
manage-service.bat logs
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Detailed installation guide |
| [QUICKSTART.md](QUICKSTART.md) | Quick reference card |
| [API Documentation](http://localhost:8000/docs) | Interactive Swagger UI (when running) |

## 🔧 Service Management

### Windows Service Commands

```cmd
# Install service (auto-start on boot)
python app\service_wrapper.py install

# Start service
python app\service_wrapper.py start

# Stop service
python app\service_wrapper.py stop

# Restart service
python app\service_wrapper.py restart

# Check status
python app\service_wrapper.py status

# Remove service
python app\service_wrapper.py remove
```

### Interactive Menu

```cmd
manage-service.bat
```

Provides menu-driven interface for all service operations.

## 📊 Monitoring & Logging

### Log Locations

- **Application Logs:** `logs/service.log` (rotated automatically)
- **Windows Event Log:** Applications and Services Logs → BusyWhatsAppGateway
- **Access Logs:** Included in service.log

### View Logs

```cmd
# Last 50 lines
manage-service.bat logs

# Or PowerShell
Get-Content logs\service.log -Tail 50 -Wait

# Windows Event Viewer
eventvwr.msc → Windows Logs → Application
```

### Health Monitoring

```bash
# Check health
curl http://localhost:8000/api/v1/health

# Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2024-02-18T10:30:00"
}
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check with DB status |
| `/api/v1/send-invoice` | GET | Busy webhook (GET method) |
| `/api/v1/send-invoice` | POST | Alternative webhook (JSON) |
| `/api/v1/parties/{phone}` | GET | Get party by phone number |
| `/api/v1/vouchers/{party_code}` | GET | Get vouchers for party |
| `/api/v1/parties/search/{term}` | GET | Search parties |

## 🛠️ Troubleshooting

### Common Issues

**Service won't start**
```cmd
# Check Python architecture (must be 32-bit)
python -c "import struct; print(struct.calcsize('P') * 8)"
# Should print: 32

# Check ODBC driver
%windir%\syswow64\odbcad32.exe
# Look for: Microsoft Access Driver (*.mdb, *.accdb)
```

**Database connection failed**
- Verify `.bds` file path in `.env`
- Check database password
- Ensure file is not open in Busy
- Run as Administrator if permission issues

**WhatsApp messages not sending**
- Verify Twilio/Meta credentials
- Check phone number format (with country code)
- Review logs in Windows Event Viewer

### Debug Mode

For debugging, run without service:

```cmd
# Development mode (with auto-reload)
start-server.bat

# Or manually
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🏢 Production Deployment

### Security Checklist

- [ ] Change default database password
- [ ] Use HTTPS (configure reverse proxy)
- [ ] Restrict firewall rules (port 8000)
- [ ] Enable Windows Firewall
- [ ] Set strong service account password
- [ ] Configure log rotation
- [ ] Set up monitoring alerts

### HTTPS Configuration

Use IIS or nginx as reverse proxy:

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name busy-gateway.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🤝 Support

- **Issues:** Check `logs/service.log` and Windows Event Viewer
- **Documentation:** See [INSTALL.md](INSTALL.md) for detailed guide
- **API Docs:** Visit http://localhost:8000/docs when service is running

## 📝 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- ODBC connectivity via [pyodbc](https://github.com/mkleehammer/pyodbc)
- Windows service support via [pywin32](https://github.com/mhammond/pywin32)

---

**Made with ❤️ for Busy Accounting Software users**
