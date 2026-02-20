# Production Deployment Guide

## 📋 Pre-Deployment Checklist

Before deploying to production, ensure you have:

- [ ] Windows 10/11 Pro or Windows Server 2016/2019/2022
- [ ] Administrator access to the server
- [ ] Static IP address or DNS name
- [ ] Firewall configured to allow port 8000 (or your chosen port)
- [ ] SSL certificate (if using HTTPS via reverse proxy)
- [ ] Backup strategy for the application and logs

## 🔒 Security Configuration

### 1. Windows Firewall

```powershell
# Run as Administrator
# Allow incoming connections on port 8000
New-NetFirewallRule -DisplayName "Busy WhatsApp Gateway" `
    -Direction Inbound `
    -LocalPort 8000 `
    -Protocol TCP `
    -Action Allow

# If using HTTPS (port 443)
New-NetFirewallRule -DisplayName "Busy WhatsApp Gateway HTTPS" `
    -Direction Inbound `
    -LocalPort 443 `
    -Protocol TCP `
    -Action Allow
```

Or use the provided batch file:
```cmd
configure-firewall.bat
```

### 2. Service Account (Optional but Recommended)

Create a dedicated service account with limited privileges:

```powershell
# Create service account
$password = Read-Host -AsSecureString "Enter password for service account"
New-LocalUser -Name "BusyGateway" -Password $password -Description "Busy WhatsApp Gateway Service Account"

# Add to appropriate groups
Add-LocalGroupMember -Group "IIS_IUSRS" -Member "BusyGateway"

# Set folder permissions
$path = "C:\Busy WhatsApp Gateway"
icacls $path /grant "BusyGateway:(OI)(CI)F" /T
```

### 3. Database Security

- Change default Busy database password
- Limit database file permissions to service account only
- Enable Windows auditing on the .bds file

## 🚀 Deployment Steps

### Step 1: Prepare Server

```powershell
# Install required Windows features (if using IIS as reverse proxy)
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole
Enable-WindowsOptionalFeature -Online -FeatureName IIS-ApplicationDevelopment
Enable-WindowsOptionalFeature -Online -FeatureName IIS-ASPNET45
```

### Step 2: Install Python 32-bit

1. Download from https://www.python.org/downloads/windows/
2. **CRITICAL:** Select "Windows x86" (not x86-64)
3. Check "Add Python to PATH"
4. Check "Install for all users"
5. Customize installation: Install pip and py launcher

Verify installation:
```cmd
python -c "import struct; print(f'Python {struct.calcsize(chr(80))*8}-bit')"
# Output: Python 32-bit
```

### Step 3: Install Access Database Engine

Download and install **32-bit** version:
https://www.microsoft.com/en-us/download/details.aspx?id=54920

Verify ODBC driver:
```cmd
%windir%\syswow64\odbcad32.exe
# Look for: Microsoft Access Driver (*.mdb, *.accdb)
```

### Step 4: Deploy Application

```powershell
# Create application directory
mkdir "C:\Busy WhatsApp Gateway"
cd "C:\Busy WhatsApp Gateway"

# Copy project files (or clone from git)
# git clone https://your-repo.git .
# OR copy files manually

# Run production setup
.\setup-production.bat
```

### Step 5: Configure Environment

Edit `.env` with production values:

```ini
# Production Settings
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Database
BDS_FILE_PATH=C:\Busy\Production\Company.bds
BDS_PASSWORD=YourStrongPassword123

# WhatsApp Provider
WHATSAPP_PROVIDER=webhook
WEBHOOK_URL=http://localhost:3000/send

# Logging
LOG_LEVEL=WARNING
LOG_FORMAT=json
```

### Step 6: Install Windows Service

```cmd
# Install service
python app\service_wrapper.py install

# Start service
python app\service_wrapper.py start

# Verify
python app\service_wrapper.py status
```

### Step 7: Configure Reverse Proxy (Recommended)

#### Option A: IIS (Windows Native)

1. Install IIS with URL Rewrite module
2. Create new website binding to port 443 (HTTPS)
3. Install SSL certificate
4. Configure URL Rewrite rules:

```xml
<!-- web.config in IIS root -->
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="ReverseProxyInboundRule1" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://localhost:8000/{R:1}" />
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
</configuration>
```

#### Option B: Nginx (More Performant)

Download nginx for Windows: http://nginx.org/en/download.html

```nginx
# nginx.conf
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    # Logging
    access_log logs/access.log;
    error_log logs/error.log;

    # Gzip compression
    gzip on;
    gzip_types application/json;

    server {
        listen 80;
        server_name busy-gateway.yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name busy-gateway.yourdomain.com;

        # SSL Configuration
        ssl_certificate     C:/nginx/ssl/cert.pem;
        ssl_certificate_key C:/nginx/ssl/key.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        # Proxy to FastAPI
        location / {
            proxy_pass http://localhost:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
```

### Step 8: Configure Busy Software

**URL Template:**
```
https://busy-gateway.yourdomain.com/api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

**Note:** If not using HTTPS, use `http://your-server-ip:8000/...`

## 📊 Monitoring Setup

### Windows Performance Counters

Create monitoring script (`monitor.ps1`):

```powershell
# Check service status
$service = Get-Service -Name "BusyWhatsAppGateway" -ErrorAction SilentlyContinue
if ($service.Status -ne "Running") {
    Write-EventLog -LogName Application -Source "BusyWhatsAppGateway" `
        -EventId 1001 -EntryType Error `
        -Message "Service is not running!"
}

# Check API health
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 10
    if ($response.status -ne "healthy") {
        Write-EventLog -LogName Application -Source "BusyWhatsAppGateway" `
            -EventId 1002 -EntryType Warning `
            -Message "API health check failed"
    }
} catch {
    Write-EventLog -LogName Application -Source "BusyWhatsAppGateway" `
        -EventId 1003 -EntryType Error `
        -Message "API is not responding"
}

# Check disk space
$disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
$freePercent = [math]::Round(($disk.FreeSpace / $disk.Size) * 100, 2)
if ($freePercent -lt 10) {
    Write-EventLog -LogName Application -Source "BusyWhatsAppGateway" `
        -EventId 1004 -EntryType Warning `
        -Message "Low disk space: $freePercent% remaining"
}
```

Schedule with Task Scheduler to run every 5 minutes.

### Log Rotation

Already configured in service wrapper (10MB files, 5 backups).

For additional log management:

```powershell
# Schedule log cleanup (runs monthly)
Get-ChildItem "logs\*.log" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-30)
} | Remove-Item
```

## 🔧 Maintenance

### Regular Tasks

**Daily:**
- Check service status
- Review error logs
- Monitor WhatsApp delivery rates

**Weekly:**
- Review performance metrics
- Check disk space
- Backup configuration files

**Monthly:**
- Rotate and archive logs
- Update dependencies
- Review security settings
- Test disaster recovery

### Backup Strategy

```powershell
# Backup script (schedule daily)
$date = Get-Date -Format "yyyy-MM-dd"
$backupDir = "C:\Backups\BusyGateway\$date"

# Create backup directory
New-Item -ItemType Directory -Force -Path $backupDir

# Backup application
copy "C:\Busy WhatsApp Gateway\.env" $backupDir
Compress-Archive -Path "C:\Busy WhatsApp Gateway\logs" `
    -DestinationPath "$backupDir\logs.zip"

# Backup database (ensure not in use)
copy "C:\Busy\Production\Company.bds" "$backupDir\Company.bds"

# Cleanup old backups (keep 30 days)
Get-ChildItem "C:\Backups\BusyGateway" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-30)
} | Remove-Item -Recurse
```

## 🚨 Troubleshooting

### Service Won't Start

```cmd
# Check Python architecture
python -c "import struct; print(struct.calcsize('P') * 8)"
# Must be 32

# Check dependencies
python -c "import pyodbc; import fastapi; import uvicorn; print('OK')"

# Run in foreground for debugging
python app\service_wrapper.py
# Check for errors in console
```

### Database Connection Issues

```cmd
# Test ODBC connection
python -c "
import pyodbc
conn = pyodbc.connect(
    'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    'DBQ=C:\\Busy\\Production\\Company.bds;'
    'PWD=YourPassword;'
)
print('Connection successful!')
"
```

### High Memory Usage

- Check log rotation is working
- Monitor connection pool usage
- Restart service weekly if needed (schedule task)

### WhatsApp API Failures

- Check Meta Business API status page
- Verify rate limits not exceeded
- Check phone number format includes country code

## 📈 Scaling Considerations

If you need to handle high volume:

1. **Load Balancing:** Deploy multiple instances behind nginx
2. **Database:** Consider migrating from Access to SQL Server
3. **Caching:** Add Redis for party data caching
4. **Queue:** Implement message queue (RabbitMQ/Celery) for WhatsApp sends

## 🆘 Emergency Recovery

### Service Won't Start

1. Stop service: `python app\service_wrapper.py stop`
2. Check logs: `Get-Content logs\service.log -Tail 100`
3. Test database: `python -c "from app.database.connection import db; db.test_connection()"`
4. Test in development mode: `start-server.bat`
5. Fix issues
6. Restart service: `python app\service_wrapper.py start`

### Complete Failure

1. Restore from backup
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Restore `.env` from backup
4. Reinstall service
5. Start service

## 📞 Support Contacts

- **Internal IT:** [Your IT Department]
- **Busy Support:** [Busy Software Vendor]
- **WhatsApp Provider:** Meta Business API support portal

---

**Last Updated:** 2024-02-18  
**Version:** 1.0.0
