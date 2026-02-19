# Windows Environment Adaptation Guide

**Environment:** Git Bash (MinGW) on Windows

**Critical Differences from Linux:**

1. **Python:** Use `python` NOT `python3`
2. **Batch files:** Always use `./script.bat` NOT `script.bat`
3. **Avoid Windows commands:** `del`, `type` don't work - use `rm`, `cat` instead
4. **Environment variables:** Use `$VAR` NOT `%VAR%`
5. **Paths:** Git Bash converts to `/c/Users/...` format

**Available Tools:** Python 3.13, Node.js v25.6.1, NPM 11.4.0, Git 2.53.0, Pip 25.2

**Working Commands:** All standard Unix commands (ls, cat, rm, cp, mv, grep, find, head, tail, chmod, etc.)

**NOT Available:** `man`, `python3`

**Path with spaces (User's Name is `Vibhor Goel`):** Always quote - `"C:\Users\Name\path"`

**Virtual Environment:** Always use the virtual environment (`venv`) for all Python operations - activate it first before running any Python commands.
