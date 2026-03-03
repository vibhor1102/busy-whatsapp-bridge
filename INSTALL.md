# Busy Whatsapp Bridge - Installation Guide

## System Requirements

| Requirement | Details |
|-------------|---------|
| **OS** | Windows 10 or later (64-bit) |
| **RAM** | 2 GB minimum, 4 GB recommended |
| **Disk** | 500 MB for installation |
| **Network** | Internet connection for WhatsApp |
| **Browser** | Any modern browser for the dashboard |
| **Busy Software** | Busy Accounting Software (for database integration) |

> **Note:** Node.js must be installed separately for the WhatsApp (Baileys) server.  
> Download from: https://nodejs.org/ (LTS version recommended)

---

## Installation

### Option 1: Installer (Recommended)

1. Download `BusyWhatsappBridge-v1.0.0-Setup.exe` from [GitHub Releases](https://github.com/vibhor1102/busy-whatsapp-bridge/releases)
2. Run the installer
3. Choose installation options:
   - ☑ Create desktop shortcut (default: yes)
   - ☑ Start with Windows login (default: yes)
4. Click **Install** and wait for setup to complete
5. The application will be installed to `C:\Program Files\Busy Whatsapp Bridge\` (or user-selected location)

### Option 2: Manual Setup (Development)

1. Clone the repository:
   ```bash
   git clone https://github.com/vibhor1102/busy-whatsapp-bridge.git
   cd busy-whatsapp-bridge
   ```
2. Run bundled setup:
   ```bash
   setup-bundled.bat
   ```
3. Start the application:
   ```bash
   Run-Dev.bat
   ```

---

## Post-Installation

### 1. Configure Database (Optional)

Edit `%APPDATA%\BusyWhatsappBridge\conf.json`:

```json
{
  "database": {
    "bds_file_path": "C:\\Path\\To\\Your\\db12025.bds",
    "bds_password": "YourPassword"
  }
}
```

Or use the dashboard Settings page.

### 2. Connect WhatsApp

1. Open http://localhost:8000/dashboard
2. Go to **WhatsApp** page
3. Scan the QR code with your phone

### 3. Configure Busy Webhook

In Busy Accounting Software, set the SMS webhook URL to:
```
http://localhost:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}
```

---

## Firewall Configuration

If accessing from other computers on your network, allow port 8000:

- Run **Start Menu → Busy Whatsapp Bridge → Configure Firewall** (as Administrator)
- Or manually: `netsh advfirewall firewall add rule name="BWB" dir=in action=allow protocol=TCP localport=8000`

---

## Uninstallation

1. **Via Windows Settings:** Settings → Apps → Busy Whatsapp Bridge → Uninstall
2. **Via Start Menu:** Start Menu → Busy Whatsapp Bridge → Uninstall

User data at `%APPDATA%\BusyWhatsappBridge\` is preserved by default. Delete manually to remove all traces.

---

## Upgrading

Simply run the new installer over the existing installation. Your configuration and data are preserved automatically.
