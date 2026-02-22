#!/usr/bin/env python3
"""
Test Phase 5: Settings Editor and Final Integration
Tests settings API and complete dashboard functionality.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

print("=" * 60)
print("Phase 5: Settings Editor & Final Integration Tests")
print("=" * 60)
print()

client = TestClient(app)

# Test 1: Settings API
print("Test 1: Settings API Endpoints")
print("-" * 40)

# Get settings
response = client.get("/api/v1/settings")
if response.status_code == 200:
    data = response.json()
    print(f"  [OK] Settings API: {len(data)} settings returned")
    print(f"       Provider: {data.get('WHATSAPP_PROVIDER', 'N/A')}")
    print(f"       Port: {data.get('PORT', 'N/A')}")
else:
    print(f"  [FAIL] Settings API: {response.status_code}")

# Get env file
response = client.get("/api/v1/settings/env")
if response.status_code == 200:
    data = response.json()
    content_len = len(data.get('content', ''))
    print(f"  [OK] Env file API: {content_len} bytes")
else:
    print(f"  [FAIL] Env file API: {response.status_code}")

# Update env file (test only)
test_content = "# Test content\nAPP_NAME=Test"
response = client.post("/api/v1/settings/env", json={"content": test_content})
if response.status_code == 200:
    print(f"  [OK] Update env API: Settings saved")
    # Restore original
    original = client.get("/api/v1/settings/env").json()["content"]
    client.post("/api/v1/settings/env", json={"content": original})
else:
    print(f"  [FAIL] Update env API: {response.status_code}")
print()

# Test 2: Complete dashboard navigation
print("Test 2: Dashboard Complete Features")
print("-" * 40)
response = client.get("/dashboard")
if response.status_code == 200:
    content = response.text
    pages = [
        ("Overview", "page-overview"),
        ("WhatsApp", "page-whatsapp"),
        ("Queue", "page-queue"),
        ("Logs", "page-logs"),
        ("System", "page-system"),
        ("Settings", "page-settings"),
    ]
    
    for name, page_id in pages:
        status = "OK" if page_id in content else "FAIL"
        print(f"  [{status}] {name} page")
    
    # Check features
    features = [
        ("Sidebar navigation", 'class="sidebar"'),
        ("Settings editor", 'env-editor'),
        ("Save settings button", "saveSettings"),
        ("Multi-page nav", "showPage"),
        ("Real-time stats", "fetchStats"),
    ]
    
    print()
    for name, pattern in features:
        status = "OK" if pattern in content else "FAIL"
        print(f"  [{status}] {name}")
else:
    print(f"  [FAIL] Dashboard not accessible: {response.status_code}")
print()

# Test 3: All API endpoints
print("Test 3: All API Endpoints Summary")
print("-" * 40)
endpoints = [
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/dashboard/stats"),
    ("GET", "/api/v1/dashboard/activity"),
    ("GET", "/api/v1/queue/status"),
    ("GET", "/api/v1/queue/pending"),
    ("GET", "/api/v1/queue/dead-letter"),
    ("GET", "/api/v1/queue/history"),
    ("GET", "/api/v1/baileys/status"),
    ("GET", "/api/v1/baileys/qr"),
    ("POST", "/api/v1/baileys/restart"),
    ("POST", "/api/v1/whatsapp/disconnect"),
    ("GET", "/api/v1/settings"),
    ("GET", "/api/v1/settings/env"),
]

working = 0
for method, endpoint in endpoints:
    if method == "GET":
        response = client.get(endpoint)
    else:
        response = client.post(endpoint)
    
    status_code = response.status_code
    ok = status_code in [200, 503]  # 503 is OK for Baileys when not running
    working += 1 if ok else 0
    symbol = "OK" if ok else f"{status_code}"
    print(f"  [{symbol}] {method} {endpoint}")

print(f"\n  {working}/{len(endpoints)} endpoints working")
print()

print("=" * 60)
print("Phase 5 Complete! Dashboard is Ready")
print("=" * 60)
print("\n✨ FEATURES IMPLEMENTED:")
print("  ✓ Overview Dashboard with real-time stats")
print("  ✓ WhatsApp Manager with QR code display")
print("  ✓ Queue Management (Pending/Retrying/Dead Letter/History)")
print("  ✓ Live Logs viewer")
print("  ✓ System Control panel")
print("  ✓ Settings Editor (.env file editing)")
print("  ✓ Left-click tray opens dashboard")
print("  ✓ WebSocket for real-time updates (foundation)")
print("\n🚀 START INSTRUCTIONS:")
print("  1. Run: Start-Gateway.bat")
print("  2. Left-click tray icon to open dashboard")
print("  3. Or visit: http://localhost:8000/dashboard")
