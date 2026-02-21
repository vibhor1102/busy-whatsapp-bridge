#!/usr/bin/env python3
"""
Check ODBC drivers and database connectivity
"""
import sys

def check_odbc():
    print("Checking ODBC Drivers...")
    print("=" * 50)
    
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        
        print(f"\nFound {len(drivers)} ODBC drivers:")
        access_drivers = [d for d in drivers if 'access' in d.lower()]
        
        if access_drivers:
            print("\n✓ Access drivers found:")
            for d in access_drivers:
                print(f"  - {d}")
        else:
            print("\n✗ No Access drivers found!")
            print("\nInstall Microsoft Access Database Engine 2016 (32-bit):")
            print("https://www.microsoft.com/en-us/download/details.aspx?id=54920")
            return False
            
    except ImportError:
        print("✗ pyodbc not installed")
        print("Run: pip install pyodbc")
        return False
    
    # Test connection
    print("\n" + "=" * 50)
    print("Testing database connection...")
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        print(f"\nDatabase path: {settings.BDS_FILE_PATH}")
        print(f"ODBC Driver: {settings.ODBC_DRIVER}")
        
        conn_str = settings.database_connection_string
        print("\nConnecting...")
        
        conn = pyodbc.connect(conn_str, timeout=10)
        print("✓ Connection successful!")
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Verify database path in .env file")
        print("2. Ensure network path is accessible")
        print("3. Try mapping network drive (e.g., F:\\) and using local path")
        print("4. Check if 32-bit Access driver is installed")
        return False

if __name__ == "__main__":
    success = check_odbc()
    sys.exit(0 if success else 1)
