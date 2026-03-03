# Changelog

All notable changes to Busy Whatsapp Bridge will be documented in this file.

## [1.0.0] - 2026-03-03

### 🎉 First Production Release

#### Core Features
- **WhatsApp Integration** via Baileys (WhatsApp Web protocol)
  - QR code scanning with live SSE updates
  - Session persistence and auto-reconnect
  - Text and PDF/document message sending
  - Anti-detection measures (behavioral simulation, presence management, startup delays)

- **Busy Accounting Integration**
  - Webhook endpoint for automatic invoice sending from Busy
  - PDF extraction from `files.busy.in` URLs
  - Multi-company database support via `X-Company-Id` header

- **Payment Reminder System**
  - Automated payment reminders with ledger PDF attachments
  - Amount due calculation using Busy credit days (Master1.I2)
  - 5 customizable message templates with variable substitution
  - APScheduler for weekly/bi-weekly automated sending
  - Anti-spam controls with cooldown periods
  - Batch processing with rate limiting

- **Message Queue**
  - SQLite-based reliable delivery with retry logic
  - Exponential backoff (immediate → 30s → 5min → 15min → 1hr)
  - Dead letter queue for permanently failed messages
  - Full message history with filtering

- **React Dashboard**
  - Real-time system status monitoring
  - WhatsApp connection management
  - Message queue viewer and history
  - Payment reminder configuration and sending
  - Settings management with file browser
  - Built with React 19 + TypeScript + Vite + Tailwind CSS

#### System Features
- Windows system tray integration with status icons
- Single-instance enforcement via Windows mutex
- Auto-start via Windows Task Scheduler
- Professional Windows installer (Inno Setup)
- Bundled Python runtime (no Python installation required)
- Graceful process lifecycle management
- Structured logging with daily rotation

#### API
- Full REST API with OpenAPI/Swagger documentation
- Health check endpoint with component status
- WebSocket support for real-time updates
