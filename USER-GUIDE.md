# Busy Whatsapp Bridge - User Guide

## What is Busy Whatsapp Bridge?

Busy Whatsapp Bridge connects your **Busy Accounting Software** to **WhatsApp**, allowing you to:

- **Send invoices** automatically as WhatsApp messages with PDF attachments
- **Send payment reminders** to customers with outstanding balances
- **Manage everything** from a web dashboard

---

## Getting Started

### 1. First Launch

After installation, the application starts automatically (or launch from Start Menu).

- A **system tray icon** (green circle) appears near the clock
- The application runs two services:
  - **Baileys Server** (WhatsApp connection on port 3001)
  - **FastAPI Gateway** (API + Dashboard on port 8000)

### 2. Connect WhatsApp

1. Open the dashboard: **http://localhost:8000/dashboard**
2. Navigate to the **WhatsApp** page
3. Scan the **QR code** with your WhatsApp mobile app:
   - Open WhatsApp on your phone
   - Go to **Settings → Linked Devices → Link a Device**
   - Point your camera at the QR code on screen
4. Once connected, the status will show **"Connected"**

### 3. Configure Database

1. Go to **Settings** in the dashboard
2. Set the **BDS file path** to your Busy database file (e.g., `C:\BusyData\db12025.bds`)
3. Enter the **BDS password** (default: `ILoveMyINDIA`)
4. Click **Save**

---

## Features

### Invoice Sending

Busy Accounting Software sends invoices automatically via webhook:

1. In Busy, configure the SMS template URL:
   ```
   http://localhost:8000/api/v1/send-invoice?phone={MobileNo}&msg={Message}
   ```
2. When you create an invoice in Busy, it automatically sends via WhatsApp
3. PDF invoices from `files.busy.in` are attached automatically

### Payment Reminders

1. Go to **Reminders** in the dashboard
2. **Refresh data** to load customer balances from Busy
3. **Select customers** to send reminders to
4. **Choose a template** or create your own
5. Click **Send** to deliver reminders via WhatsApp

### Dashboard

Access at **http://localhost:8000/dashboard**:

- **Home** — System status and health overview
- **WhatsApp** — QR code scanning and connection status
- **Messages** — Message queue and delivery history
- **Reminders** — Payment reminder management
- **Settings** — Application configuration

---

## System Tray

Right-click the tray icon for quick actions:

| Menu Item | Action |
|-----------|--------|
| Open Dashboard | Opens the web dashboard in your browser |
| Open WhatsApp Page | Goes directly to WhatsApp connection page |
| Open API Docs | Opens the interactive API documentation |
| Stop/Start Baileys | Control the WhatsApp server |
| Stop/Start FastAPI | Control the API gateway |
| Show Status | Display current server status |
| Exit | Gracefully stop all servers |

---

## Managing Auto-Start

The application can start automatically when you log in to Windows:

1. **Start Menu → Busy Whatsapp Bridge → Manage Auto-Start**
2. Or run `manage-task.bat` from the installation folder

Options:
- **Enable Auto-Start** — Starts on login (tray mode)
- **Disable Auto-Start** — Manual start only
- **Check Status** — See current auto-start state

---

## Troubleshooting

### WhatsApp Won't Connect
- Ensure your phone has an active internet connection
- Try refreshing the QR code page
- Check that port 3001 is not blocked by firewall

### Dashboard Not Loading
- Verify the application is running (check tray icon)
- Try http://localhost:8000/api/v1/health to check API status
- Check logs at `%APPDATA%\BusyWhatsappBridge\logs\`

### Messages Not Sending
- Verify WhatsApp is connected (dashboard → WhatsApp page)
- Check the message queue (dashboard → Messages)
- Review failed messages in the dead letter queue

### Application Won't Start
- Check if another instance is already running
- Look for error details in `%APPDATA%\BusyWhatsappBridge\logs\`
- Try running `manage-task.bat` → option 5 (Stop), then restart

---

## File Locations

| Location | Purpose |
|----------|---------|
| `%APPDATA%\BusyWhatsappBridge\conf.json` | Configuration file |
| `%APPDATA%\BusyWhatsappBridge\data\` | Message database and reminder settings |
| `%APPDATA%\BusyWhatsappBridge\auth\` | WhatsApp session credentials |
| `%APPDATA%\BusyWhatsappBridge\logs\` | Application logs |

---

## Support

- **GitHub Issues:** https://github.com/vibhor1102/busy-whatsapp-bridge/issues
- **Releases:** https://github.com/vibhor1102/busy-whatsapp-bridge/releases
