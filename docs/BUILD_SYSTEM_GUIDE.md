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
├── version.json                   ← Single source of truth for version
├── app/                           ← Python backend (FastAPI)
│   └── version.py                 ← Dynamic version loader
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

### What It Does (5 Steps)
1. **Builds dashboard** — `npm install` + `npm run build` in `dashboard-react/`
2. **Builds EXE** — PyInstaller creates `BusyWhatsappBridge.exe` with app icon
3. **Signs EXE** — PowerShell script applies developer signature to the launcher
4. **Builds installer** — Passes version to Inno Setup, compiles `installer.iss`
5. **Signs installer** — Applies signature to the final setup EXE

### Output
```
BusyWhatsappBridge-vX.X.X-Setup.exe  (~50-100 MB)
```

### Version Management
- Single source of truth: `version.json` (root)
- Loaded by: `app/version.py` (which other scripts import)
- `build-all.bat` & `build-installer.bat` read version dynamically via `app.version.get_version()`
- Version is passed to Inno Setup via `/DMyAppVersion=X.X.X`
- To bump version: edit `version.json`, then rebuild

---

## Code Signing

To bypass Microsoft Smart App Control and Windows Defender "Unknown Publisher" warnings, executables are self-signed with a developer certificate.

### For Developers: Managing Certificates

The build scripts handle signing automatically. To manage certificates manually:

1.  **Generate Certificate**: Creates `vibhor1102-dev.pfx` (private) and `vibhor1102-dev.cer` (public).
    ```powershell
    powershell.exe -ExecutionPolicy Bypass -File scripts/manage-signing.ps1 -Action generate
    ```
2.  **Sign Files Manually**:
    ```powershell
    powershell.exe -ExecutionPolicy Bypass -File scripts/manage-signing.ps1 -Action sign -File "path/to/your.exe"
    ```

> [!CAUTION]
> The `vibhor1102-dev.pfx` file contains your private key. **Do not share this file** or commit it to public repositories.

### For Users: Trusting the Application

If users see a "Smart App Control" block, they must perform a one-time trust:

1.  Open the installer folder.
2.  Right-click `scripts/trust-certificate.bat` and select **Run as Administrator**.
3.  Once installed, run the setup EXE again.

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
- Documentation: README, USER-GUIDE, INSTALL, LICENSE

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

1. Update version in `version.json`
2. Run `.\build-all.bat`
4. Test installer on a clean machine
5. Commit and tag: `git tag vX.X.X`
6. Push: `git push origin main --tags`
7. Create GitHub Release, attach:
    - `BusyWhatsappBridge-vX.X.X-Setup.exe` (The installer)
    - `scripts/trust-certificate.bat` (For users to trust the app)
    - `vibhor1102-dev.cer` (The public certificate required by the script)