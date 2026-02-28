# Dashboard Build Workflow Guide

## Overview

The React dashboard build process is now **fully integrated** into the startup workflow. You don't need to manually run `npm run build` anymore!

## For Developers (Daily Development)

### Using `Run-Dev.bat`

**Location:** `C:\Program Files\BusyWhatsappBridge\Run-Dev.bat`

**What it does:**
1. **Automatically checks** if the dashboard is built
2. **Automatically builds** if needed (only on first run or when source files change)
3. **Starts the application** in tray mode with console logs

**Usage:**
```bash
# Simply double-click Run-Dev.bat
# Or from command line:
Run-Dev.bat
```

**Behavior:**
- ✅ First run: Builds dashboard automatically (takes 1-2 minutes)
- ✅ Subsequent runs: Checks if source files changed, rebuilds only if needed
- ✅ Shows build progress in console
- ✅ Falls back gracefully if build fails

### Manual Dashboard Control (Optional)

If you need more control, use the build manager script:

```bash
# Check if dashboard is built
python check-dashboard-build.py --check

# Build production dashboard
python check-dashboard-build.py --build

# Force rebuild (even if already built)
python check-dashboard-build.py --force

# Start Vite dev server with hot-reload (for active frontend development)
cd dashboard-react
npm run dev
# Then access http://localhost:5173
```

### Development Workflow Summary

| Scenario | What Happens | Action Needed |
|----------|--------------|---------------|
| First time setup | Dashboard auto-builds | Just run `Run-Dev.bat` |
| Daily development | Dashboard ready instantly | Just run `Run-Dev.bat` |
| Changed React code | Auto-detects and rebuilds | Just run `Run-Dev.bat` |
| Active React dev | Use Vite dev server | Run `npm run dev` in dashboard-react/ |
| Production testing | Use built files | Run `Run-Dev.bat` (uses built files) |

## For End Users (Production)

### Using `BusyWhatsappBridge.exe`

**What it does:**
1. **Checks** if dashboard is pre-built (included in installer)
2. **Shows error** if dashboard is missing (corrupted installation)
3. **Starts normally** if dashboard is present

**Workflow:**
```
User installs application
    ↓
Installer includes pre-built dashboard-react/dist/
    ↓
User runs BusyWhatsappBridge.exe
    ↓
Application verifies dashboard exists
    ↓
Application starts normally
```

**No build step required for users!**

### If Dashboard Is Missing

Users will see this helpful message:
```
WARNING: Dashboard not found!
The dashboard needs to be built before first use.

For development:
  cd "C:\Program Files\BusyWhatsappBridge"
  python check-dashboard-build.py --build

For production:
  Please reinstall the application or contact support.
```

## Build Integration Details

### Smart Build Detection

The system intelligently decides when to build:

1. **File existence check**: Does `dashboard-react/dist/index.html` exist?
2. **Source staleness check**: Are any `.tsx` or `.ts` files in `src/` newer than the build?
3. **Auto-build**: Only builds if necessary

### Build Script (`check-dashboard-build.py`)

**Features:**
- ✅ Automatic dependency installation (`npm install`)
- ✅ Source file change detection
- ✅ Exit codes for script integration
- ✅ Progress messages
- ✅ Error handling with helpful messages

**Usage modes:**
```bash
python check-dashboard-build.py --check    # Exit code 0 if built, 1 if not
python check-dashboard-build.py --build    # Build if needed
python check-dashboard-build.py --force    # Force rebuild
python check-dashboard-build.py --dev      # Start Vite dev server
python check-dashboard-build.py --install  # Just install dependencies
```

## Production Build Process

### Using `build-all.bat`

When creating a release:

```bash
# Builds everything for distribution:
build-all.bat

# Steps:
# 1. Build dashboard-react (npm run build)
# 2. Build launcher EXE (PyInstaller)
# 3. Build installer (Inno Setup)
# 4. Verify output

# Output: BusyWhatsappBridge-vX.X.X-Setup.exe
```

**The installer includes:**
- Pre-built `dashboard-react/dist/` (production files)
- No build step needed for end users
- Dashboard is served as static files by FastAPI

## File Structure

```
C:\Program Files\BusyWhatsappBridge\
├── dashboard-react/              # React dashboard source
│   ├── src/                      # TypeScript/React source files
│   ├── dist/                     # Built production files (auto-generated)
│   ├── node_modules/             # npm dependencies
│   └── package.json
├── app/
│   └── main.py                   # Serves dashboard-react/dist/
├── Run-Dev.bat                   # Developer launcher (auto-builds)
├── Start-Gateway.py              # User launcher (checks pre-built)
├── check-dashboard-build.py      # Build manager script
├── build-all.bat                 # Release builder
└── installer.iss                 # Installer config
```

## Technical Details

### FastAPI Static File Serving

In `app/main.py`:
```python
# Mount static files for dashboard
dashboard_path = Path(__file__).parent.parent / "dashboard-react" / "dist"
if dashboard_path.exists():
    app.mount("/dashboard-static", StaticFiles(directory=str(dashboard_path)), name="dashboard-static")
```

Dashboard URL: `http://localhost:8000/dashboard`

### Hot-Reload Development

For active frontend development with instant refresh:

```bash
cd dashboard-react
npm run dev
```

- Vite dev server runs on `http://localhost:5173`
- Changes to source files trigger instant reload
- Backend API still runs on `http://localhost:8000`
- Proxy configuration in `vite.config.ts` routes API calls

### Production vs Development

| Aspect | Development | Production |
|--------|-------------|------------|
| Dashboard source | `dashboard-react/src/` | `dashboard-react/dist/` |
| Build step | Automatic on first run | Pre-built in installer |
| File serving | Static files via FastAPI | Static files via FastAPI |
| Hot reload | Available via `npm run dev` | N/A |
| Build tool | Vite (on demand) | Vite (pre-built) |

## Troubleshooting

### "Dashboard not built" Error

**For Developers:**
```bash
# Auto-build
python check-dashboard-build.py --build

# Or force rebuild
python check-dashboard-build.py --force
```

**For Users:**
- Reinstall the application
- Or contact support

### Build Fails

**Check:**
1. Node.js installed: `node --version`
2. npm working: `npm --version`
3. Dependencies installed: `cd dashboard-react && npm install`

**Fix:**
```bash
cd dashboard-react
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Slow First Build

**Normal!** First build downloads dependencies and compiles TypeScript:
- Initial build: 1-2 minutes
- Subsequent builds: 10-30 seconds
- Daily use: Instant (cached)

## Summary

✅ **Developers:** Just run `Run-Dev.bat` - it handles everything automatically
✅ **Users:** Dashboard is pre-built in installer - no action needed
✅ **Builds:** Smart detection prevents unnecessary rebuilds
✅ **Flexibility:** Manual control available via `check-dashboard-build.py`

The build process is now **invisible** for daily use while remaining **flexible** when needed!
