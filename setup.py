#!/usr/bin/env python3
"""
Smart Setup and Migration System

Production-grade installation and upgrade system that:
1. Detects installation state (fresh/repair/upgrade)
2. Preserves all user configuration and data
3. Migrates configs and databases intelligently
4. Creates backups before any changes
5. Provides detailed logging and error recovery

Usage:
    python setup.py                    # Interactive setup
    python setup.py --silent           # Silent mode (no prompts)
    python setup.py --repair           # Force repair mode
    python setup.py --version          # Show version info
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Add project to path for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from app.version import get_version, compare_versions, parse_version


class Colors:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class SetupLogger:
    """Setup logging with file and console output."""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.errors = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Write to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        
        # Print to console with colors
        if level == "ERROR":
            print(f"{Colors.FAIL}[ERROR] {message}{Colors.ENDC}")
            self.errors.append(message)
        elif level == "WARNING":
            print(f"{Colors.WARNING}[WARNING] {message}{Colors.ENDC}")
        elif level == "SUCCESS":
            print(f"{Colors.OKGREEN}[OK] {message}{Colors.ENDC}")
        elif level == "INFO":
            print(f"[INFO] {message}")
    
    def error(self, message: str):
        self.log(message, "ERROR")
    
    def warning(self, message: str):
        self.log(message, "WARNING")
    
    def success(self, message: str):
        self.log(message, "SUCCESS")
    
    def info(self, message: str):
        self.log(message, "INFO")
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class SetupManager:
    """Manages the complete setup and migration process."""
    
    def __init__(self, silent: bool = False, repair: bool = False):
        self.silent = silent
        self.force_repair = repair
        self.logger: Optional[SetupLogger] = None
        
        # Paths
        self.program_dir = SCRIPT_DIR
        self.appdata_dir = self._get_appdata_dir()  # For all user data and config
        self.venv_dir = self.program_dir / "venv"
        self.python_dir = self.program_dir / "python"
        self.config_template = self.program_dir / "conf.json.example"
        self.config_file = self.appdata_dir / "conf.json"
        self.version_file = self.appdata_dir / ".version"
        
        # Current version from code
        self.current_version = get_version()
        
    def _get_appdata_dir(self) -> Path:
        """Get AppData directory for user configuration and data."""
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        return appdata / "BusyWhatsappBridge"
    
    def _detect_state(self) -> Dict:
        """Detect current installation state."""
        state = {
            'fresh': False,
            'repair': False,
            'upgrade': False,
            'has_data': False,
            'installed_version': None,
            'has_venv': self.venv_dir.exists(),
            'has_python': self.python_dir.exists(),
            'has_config': self.config_file.exists(),
        }
        
        # Check if AppData has existing data
        if self.appdata_dir.exists():
            state['has_data'] = any(self.appdata_dir.iterdir())
        
        # Check installed version
        if self.version_file.exists():
            try:
                state['installed_version'] = self.version_file.read_text().strip()
            except:
                pass
        elif state['has_config']:
            # Try to read version from config
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    state['installed_version'] = config.get('version', '0.0.0')
            except:
                state['installed_version'] = '0.0.0'
        
        # Determine state
        if self.force_repair:
            state['repair'] = True
        elif not state['has_data'] and not state['installed_version']:
            state['fresh'] = True
        elif state['installed_version'] and state['installed_version'] != self.current_version:
            state['upgrade'] = True
        elif not state['has_venv'] and state['has_data']:
            state['repair'] = True
        else:
            # Everything looks good, but re-run setup anyway
            state['repair'] = True
        
        return state
    
    def _create_backup(self, path: Path) -> Optional[Path]:
        """Create backup of file or directory."""
        if not path.exists():
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.appdata_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        if path.is_file():
            backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
            shutil.copy2(path, backup_path)
        else:
            backup_path = backup_dir / f"{path.name}_{timestamp}"
            shutil.copytree(path, backup_path)
        
        return backup_path
    
    def _restore_backup(self, backup_path: Path, original_path: Path):
        """Restore from backup."""
        if backup_path.is_file():
            shutil.copy2(backup_path, original_path)
        else:
            if original_path.exists():
                shutil.rmtree(original_path)
            shutil.copytree(backup_path, original_path)
    
    def _install_venv(self) -> bool:
        """Create/update virtual environment."""
        self.logger.info("Setting up virtual environment...")
        
        try:
            python_exe = self.python_dir / "python.exe"
            if not python_exe.exists():
                self.logger.error("Bundled Python not found!")
                return False
            
            # Check if venv already exists
            if self.venv_dir.exists():
                self.logger.info("Virtual environment exists, checking...")
                venv_python = self.venv_dir / "Scripts" / "python.exe"
                if venv_python.exists():
                    self.logger.success("Virtual environment is valid")
                    return True
                else:
                    self.logger.warning("Virtual environment is corrupted, recreating...")
                    shutil.rmtree(self.venv_dir)
            
            # Create venv using virtualenv (better for embedded Python)
            virtualenv_exe = self.python_dir / "Scripts" / "virtualenv.exe"
            if not virtualenv_exe.exists():
                self.logger.info("Installing virtualenv...")
                subprocess.run(
                    [str(python_exe), "-m", "pip", "install", "virtualenv", "-q"],
                    check=True,
                    capture_output=True
                )
                virtualenv_exe = self.python_dir / "Scripts" / "virtualenv.exe"
            
            self.logger.info("Creating virtual environment (this may take a minute)...")
            subprocess.run(
                [str(virtualenv_exe), str(self.venv_dir), "--python", str(python_exe)],
                check=True,
                capture_output=True
            )
            
            # Install dependencies
            self.logger.info("Installing dependencies...")
            pip_exe = self.venv_dir / "Scripts" / "pip.exe"
            requirements = self.program_dir / "requirements.txt"
            
            subprocess.run(
                [str(pip_exe), "install", "-r", str(requirements), "--no-warn-script-location", "-q"],
                check=True,
                capture_output=True
            )
            
            self.logger.success("Virtual environment ready")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to setup virtual environment: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False
    
    def _migrate_config(self, old_config: Dict, new_template: Dict) -> Dict:
        """Deep merge configs: preserve user settings, add new defaults."""
        result = json.loads(json.dumps(new_template))  # Deep copy template
        
        for key, value in old_config.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    # Recursive merge for nested dicts
                    result[key] = self._migrate_config(value, result[key])
                else:
                    # Keep user's value
                    result[key] = value
            else:
                # Old field not in new template - preserve it anyway
                result[key] = value
        
        return result
    
    def _setup_config(self) -> bool:
        """Setup configuration file."""
        self.logger.info("Setting up configuration...")
        
        try:
            self.appdata_dir.mkdir(parents=True, exist_ok=True)
            
            if not self.config_template.exists():
                self.logger.warning("Config template not found, using defaults")
                default_config = {"version": self.current_version}
            else:
                with open(self.config_template, 'r') as f:
                    default_config = json.load(f)
            
            if self.config_file.exists():
                # Migration needed
                self.logger.info("Existing config found, migrating...")
                backup = self._create_backup(self.config_file)
                
                with open(self.config_file, 'r') as f:
                    old_config = json.load(f)
                
                # Merge configs
                migrated = self._migrate_config(old_config, default_config)
                migrated['version'] = self.current_version
                
                with open(self.config_file, 'w') as f:
                    json.dump(migrated, f, indent=2)
                
                self.logger.success("Configuration migrated")
                if backup:
                    self.logger.info(f"Backup created: {backup}")
            else:
                # Fresh config
                default_config['version'] = self.current_version
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                self.logger.success("Configuration created")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup configuration: {e}")
            return False
    
    def _update_version_file(self):
        """Update version tracking file."""
        self.version_file.write_text(self.current_version)
    
    def _run_migration_scripts(self, old_version: str, new_version: str):
        """Run version-specific migration scripts."""
        migrations_dir = self.program_dir / "migrations"
        if not migrations_dir.exists():
            return
        
        self.logger.info(f"Running migrations {old_version} -> {new_version}...")
        
        # Find and run applicable migrations
        # Migration files: migrate_1.0.0_to_1.1.0.py
        old_tuple = parse_version(old_version)
        new_tuple = parse_version(new_version)
        
        # Get all migration files
        migrations = []
        for file in migrations_dir.glob("migrate_*.py"):
            # Parse version from filename
            try:
                parts = file.stem.replace("migrate_", "").split("_to_")
                if len(parts) == 2:
                    from_ver = parse_version(parts[0])
                    to_ver = parse_version(parts[1])
                    if old_tuple <= from_ver < new_tuple:
                        migrations.append((from_ver, to_ver, file))
            except:
                continue
        
        # Sort by version and run
        migrations.sort(key=lambda x: x[0])
        
        for from_ver, to_ver, migration_file in migrations:
            self.logger.info(f"Running migration {from_ver} -> {to_ver}...")
            try:
                # Import and run migration
                spec = __import__('importlib.util').util.spec_from_file_location(
                    migration_file.stem, migration_file
                )
                module = __import__('importlib.util').util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, 'migrate'):
                    module.migrate(self.appdata_dir, self.logger)
                    self.logger.success(f"Migration {from_ver} -> {to_ver} completed")
                else:
                    self.logger.warning(f"Migration file missing 'migrate' function")
            except Exception as e:
                self.logger.error(f"Migration failed: {e}")
                raise
    
    def run_fresh_install(self):
        """Perform fresh installation."""
        self.logger.info("=== Fresh Installation ===")
        
        if not self.silent:
            print(f"\n{Colors.OKGREEN}Welcome to Busy Whatsapp Bridge Setup{Colors.ENDC}")
            print(f"Version: {self.current_version}\n")
        
        # Setup venv
        if not self._install_venv():
            return False
        
        # Setup config
        if not self._setup_config():
            return False
        
        # Update version file
        self._update_version_file()
        
        self.logger.success("Installation completed successfully!")
        return True
    
    def run_upgrade(self, old_version: str):
        """Perform upgrade from old version."""
        self.logger.info(f"=== Upgrade {old_version} -> {self.current_version} ===")
        
        if not self.silent:
            print(f"\n{Colors.OKCYAN}Upgrading Busy Whatsapp Bridge{Colors.ENDC}")
            print(f"From: {old_version}")
            print(f"To: {self.current_version}\n")
        
        # Create backups
        self.logger.info("Creating backups...")
        if self.config_file.exists():
            self._create_backup(self.config_file)
        
        # Setup venv (update dependencies)
        if not self._install_venv():
            return False
        
        # Setup/migrate config
        if not self._setup_config():
            return False
        
        # Run migration scripts
        try:
            self._run_migration_scripts(old_version, self.current_version)
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False
        
        # Update version file
        self._update_version_file()
        
        self.logger.success(f"Upgrade completed successfully!")
        return True
    
    def run_repair(self):
        """Perform repair installation."""
        self.logger.info("=== Repair Installation ===")
        
        if not self.silent:
            print(f"\n{Colors.WARNING}Repairing Busy Whatsapp Bridge{Colors.ENDC}\n")
        
        # Setup venv
        if not self._install_venv():
            return False
        
        # Verify config exists
        if not self.config_file.exists():
            self.logger.warning("Configuration missing, creating default...")
            if not self._setup_config():
                return False
        
        # Update version file
        self._update_version_file()
        
        self.logger.success("Repair completed successfully!")
        return True
    
    def run(self) -> bool:
        """Main setup entry point."""
        # Initialize logger - logs go to install directory (overwritten on updates)
        log_dir = self.program_dir / "logs"
        self.logger = SetupLogger(log_dir)
        
        self.logger.info(f"Starting setup v{self.current_version}")
        self.logger.info(f"Program directory: {self.program_dir}")
        self.logger.info(f"AppData directory: {self.appdata_dir}")
        
        try:
            # Detect state
            state = self._detect_state()
            self.logger.info(f"Detected state: {state}")
            
            # Run appropriate setup
            if state['fresh']:
                success = self.run_fresh_install()
            elif state['upgrade']:
                success = self.run_upgrade(state['installed_version'])
            else:  # repair
                success = self.run_repair()
            
            if success:
                self.logger.info(f"Setup completed. Log: {self.logger.log_file}")
                if not self.silent:
                    print(f"\n{Colors.OKGREEN}Setup completed successfully!{Colors.ENDC}")
                    print(f"Log saved to: {self.logger.log_file}")
            else:
                self.logger.error("Setup failed")
                if not self.silent:
                    print(f"\n{Colors.FAIL}Setup failed!{Colors.ENDC}")
                    print(f"Check log: {self.logger.log_file}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.logger.error(traceback.format_exc())
            if not self.silent:
                print(f"\n{Colors.FAIL}Setup failed with error: {e}{Colors.ENDC}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Busy Whatsapp Bridge Setup and Migration"
    )
    parser.add_argument(
        "--silent", "-s",
        action="store_true",
        help="Silent mode (no user interaction)"
    )
    parser.add_argument(
        "--repair", "-r",
        action="store_true",
        help="Force repair mode"
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit"
    )
    
    args = parser.parse_args()
    
    if args.version:
        print(f"Busy Whatsapp Bridge Setup v{get_version()}")
        return 0
    
    manager = SetupManager(silent=args.silent, repair=args.repair)
    success = manager.run()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
