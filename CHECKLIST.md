# 🚀 Quick Deployment Checklist

Use this checklist to deploy Busy WhatsApp Gateway to production.

## ✅ Pre-Deployment (5 minutes)

- [ ] **Server Requirements Met**
  - Windows 10/11 Pro or Server 2016+
  - Administrator access
  - Static IP or DNS name
  - 4GB RAM minimum

- [ ] **Software Installed**
  - Python 3.9-3.13 (32-bit) ✓
  - Microsoft Access Database Engine 2010/2016 (32-bit) ✓
  - Git (optional, for cloning)

## ⚙️ Installation (10 minutes)

### Step 1: Setup (Run as Administrator)
```cmd
cd "C:\Busy WhatsApp Gateway"
setup-production.bat
```
**Expected:** Creates venv, installs deps, tests DB connection

### Step 2: Configure Environment
```cmd
notepad .env
```
**Edit these required fields:**
```ini
BDS_FILE_PATH=C:\Busy\Data\YourCompany.bds
BDS_PASSWORD=YourActualPassword
META_API_VERSION=v19.0
META_PHONE_NUMBER_ID=your_phone_number_id
META_ACCESS_TOKEN=your_access_token
```

### Step 3: Test Database
```cmd
python -c "from app.database.connection import db; print('OK' if db.test_connection() else 'FAIL')"
```
**Expected:** Prints "OK"

### Step 4: Configure Firewall
```cmd
configure-firewall.bat
```
**Expected:** Opens ports 8000 and 443

## 🏭 Service Installation (5 minutes)

### Step 5: Install Windows Service
```cmd
manage-service.bat
```
**Select:** [1] Install Service

**Alternative:**
```cmd
python app\service_wrapper.py install
python app\service_wrapper.py start
```

### Step 6: Verify Service
```cmd
python app\service_wrapper.py status
```
**Expected:** `Service 'BusyWhatsAppGateway': Running`

### Step 7: Test API
```cmd
run-tests.bat
```
**Expected:** All tests pass (or database tests pass if WhatsApp not configured)

## 🔗 Busy Software Configuration (5 minutes)

### Step 8: Configure Busy SMS Provider

**In Busy Accounting:**
1. Configuration → SMS Configuration → Config
2. Select: **Custom SMS Provider**
3. URL Template:
```
http://YOUR_SERVER_IP:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}&pdf_url={AttachmentURL}
```

### Step 9: Test End-to-End
1. Create test Sales Invoice in Busy
2. Save invoice
3. Check WhatsApp is received
4. Check logs: `manage-service.bat` → [7] View Logs

## 🛡️ Production Hardening (Optional - 15 minutes)

- [ ] **Enable HTTPS**
  - Install IIS or nginx
  - Configure SSL certificate
  - Update Busy URL to `https://...`

- [ ] **Security**
  - [ ] Change database password
  - [ ] Restrict Windows service account permissions
  - [ ] Enable Windows Firewall (already done)
  - [ ] Configure backup strategy

- [ ] **Monitoring**
  - [ ] Set up log rotation (already configured)
  - [ ] Schedule health checks
  - [ ] Configure alerts

## 📊 Daily Operations

### Check Service Status
```cmd
python app\service_wrapper.py status
```

### View Recent Logs
```cmd
powershell Get-Content logs\service.log -Tail 50
```

### Restart Service
```cmd
python app\service_wrapper.py restart
```

## 🚨 Emergency Commands

**Service won't start:**
```cmd
# Check what's wrong
python app\service_wrapper.py status
Get-Content logs\service.log -Tail 20

# Run in debug mode
start-server.bat
```

**Database connection failed:**
```cmd
# Test ODBC
python -c "
import pyodbc
conn = pyodbc.connect(
    'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    'DBQ=C:\\Busy\\Data\\YourCompany.bds;'
    'PWD=ILoveMyINDIA;'
)
print('OK')
"
```

**Complete restart:**
```cmd
python app\service_wrapper.py stop
python app\service_wrapper.py start
```

## 📞 Support

**Service Issues:**
- Check logs: `logs/service.log`
- Windows Event Viewer: Applications → BusyWhatsAppGateway
- API docs: http://localhost:8000/docs

**Database Issues:**
- Verify .bds file path
- Check file permissions
- Ensure Busy is not locking the file

**WhatsApp Issues:**
- Check Meta Business dashboard
- Verify phone number format (+countrycode)
- Check API credentials

## 🎯 Success Criteria

✅ Service shows "Running"  
✅ API responds at http://localhost:8000/api/v1/health  
✅ Database connection test passes  
✅ Test invoice sends WhatsApp message  
✅ Logs show no errors  

**Total Setup Time:** ~30 minutes  
**Go-Live:** Ready! 🎉

---

**Need Help?** See DEPLOYMENT.md for detailed instructions
