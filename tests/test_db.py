import json
import pyodbc

with open(r'C:\Users\Vibhor\AppData\Roaming\BusyWhatsappBridge\conf.json') as f:
    config = json.load(f)

db_path = config.get('database', {}).get('bds_file_path', '')
print(f"DB Path: {db_path}")

try:
    conn = pyodbc.connect(f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};pwd=bsw", timeout=5)
    cursor = conn.cursor()
    cursor.execute('SELECT TOP 1 * FROM Master1')
    print("COLUMNS:")
    print([c[0] for c in cursor.description])
    
    # Let's also find all debtor groups
    cursor.execute("SELECT Code, Name, ParentGrp FROM Master1 WHERE MasterType = 1")
    for r in cursor.fetchall():
        if "debtor" in r[1].lower() or "customer" in r[1].lower():
            print(f"Group: Code={r[0]}, Name={r[1]}, ParentGrp={r[2]}")
except Exception as e:
    print(f"Error: {e}")
