# Build System Guide

## Summary

Professional Windows application build system for Busy Whatsapp Bridge. Produces a self-contained installer that bundles Python, all dependencies, the pre-built dashboard, and the Baileys Node.js server.

---

## Architecture

```
BusyWhatsappBridge.exe (PyInstaller launcher, ~8 MB)
    ↓ locates venv & runs
Start-Gateway.py (entry point)
    ↓ delegates to
run.py (process orchestration, tray icon)
    ├── Baileys Node.js server (port 3001)
    └── FastAPI + uvicorn (port 8000)
```

**Key point:** The `.exe` is a thin launcher — it finds the bundled `venv/` Python and executes `run.py`. All application logic lives in `app/`, `run.py`, and `baileys-server/`.

---

## File Structure

```
project-root/
├── BusyWhatsappBridge.exe          ← Launcher (built by PyInstaller)
├── Start-Gateway.py               ← EXE entry point 
├── run.py                         ← Production orchestrator (ONE FILE)
├── Run-Dev.bat                    ← Development launcher (ONE FILE)
├── build-all.bat                  ← Master build script
├── build-installer.bat            ← Inno Setup compiler wrapper
├── build-launcher-exe.py          ← PyInstaller build script
├── installer.iss                  ← Inno Setup installer config
├── app.ico                        ← Application icon
├── app/                           ← Python backend (FastAPI)
│   └── version.py                 ← Single source of truth for version
├── dashboard-react/               ← React + TypeScript frontend
│   ├── src/                       ← Source files (.tsx)
│   └── dist/                      ← Built dashboard (production)
├── baileys-server/                ← Node.js WhatsApp server
├── python/                        ← Bundled Python (embeddable)
└── venv/                          ← Python virtual environment
```

---

## Development Workflow

### `Run-Dev.bat` — One-File Development

Double-click to start. It handles everything:
1. Checks prerequisites (venv, Node.js, npm)
2. Auto-builds dashboard if source is newer than dist
3. Cleans up existing processes on ports 3001/8000
4. Starts the application with console logging enabled

```bash
# Copy to desktop for convenience
copy Run-Dev.bat "%USERPROFILE%\Desktop\"
```

**Access:**
- Dashboard: http://localhost:8000/dashboard
- API Docs: http://localhost:8000/docs
- Tray icon appears automatically

---

## Production Build

### Prerequisites
- Inno Setup 6 installed ([download](https://jrsoftware.org/isdl.php))
- Node.js 18+ and npm
- Virtual environment set up (`setup-bundled.bat`)

### Build Command
```bash
.\build-all.bat
```

### What It Does (4 Steps)
1. **Builds dashboard** — `npm install` + `npm run build` in `dashboard-react/`
2. **Builds EXE** — PyInstaller creates `BusyWhatsappBridge.exe` with app icon
3. **Builds installer** — Passes version to Inno Setup, compiles `installer.iss`
4. **Verifies output** — Confirms installer file exists and reports size

### Output
```
BusyWhatsappBridge-v1.0.0-Setup.exe  (~50-100 MB)
```

### Version Management
- Single source of truth: `app/version.py`
- `build-all.bat` & `build-installer.bat` read version dynamically
- Version is passed to Inno Setup via `/DMyAppVersion=X.X.X`
- To bump version: edit `app/version.py`, then rebuild

---

## Installer Features

| Feature | Details |
|---------|---------|
| Publisher | vibhor1102 |
| Desktop shortcut | Optional (default: enabled) |
| Auto-start with Windows | Optional (default: enabled) |
| System tray | Always enabled |
| Start Menu | Shortcuts for app, auto-start manager, firewall config |
| Uninstaller | Full uninstall with optional data purge |
| Post-install setup | Runs `setup.py --silent` automatically |

### What Gets Installed
- `app/` — Python backend (excludes `__pycache__`)
- `dashboard-react/dist/` — Pre-built React dashboard (dist only, not source)
- `baileys-server/` — Node.js server + dependencies
- `python/` — Bundled Python runtime
- `venv/` — Virtual environment with all pip packages
- `run.py`, `Start-Gateway.py` — Launchers
- `setup.py`, `uninstall.py` — Setup/cleanup scripts
- Documentation: README, USER-GUIDE, INSTALL, CHANGELOG, LICENSE

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Inno Setup not found" | Install from https://jrsoftware.org/isdl.php |
| "Dashboard build failed" | Check Node.js 18+. Delete `dashboard-react/node_modules`, retry |
| "EXE not found after build" | Check PyInstaller: `pip install pyinstaller` |
| "Virtual environment not found" | Run `setup-bundled.bat` first |
| "Dashboard not built" | Run `build-all.bat` or `cd dashboard-react && npm run build` |

---

## Release Process

1. Update version in `app/version.py`
2. Update `CHANGELOG.md`
3. Run `.\build-all.bat`
4. Test installer on a clean machine
5. Commit and tag: `git tag v1.0.0`
6. Push: `git push origin main --tags`
7. Create GitHub Release, attach the setup EXE