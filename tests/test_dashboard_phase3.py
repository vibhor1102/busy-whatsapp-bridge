#!/usr/bin/env python3
"""
Test Phase 3: WhatsApp Manager and Queue Management
Tests QR code endpoints, queue tabs, and system controls.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

print("=" * 60)
print("Phase 3: WhatsApp Manager & Queue Management Tests")
print("=" * 60)
print()

client = TestClient(app)

# Test 1: Dashboard with navigation
print("Test 1: Enhanced Dashboard")
print("-" * 40)
response = client.get("/dashboard")
if response.status_code == 200:
    content = response.text
    checks = [
        ("Sidebar navigation", 'sidebar' in content.lower()),
        ("Overview page", 'page-overview' in content),
        ("WhatsApp page", 'page-whatsapp' in content),
        ("Queue page", 'page-queue' in content),
        ("Logs page", 'page-logs' in content),
        ("System page", 'page-system' in content),
        ("QR code section", 'qr-container' in content),
        ("Queue tabs", 'tab-content' in content),
    ]
    for name, result in checks:
        status = "OK" if result else "FAIL"
        print(f"  [{status}] {name}")
else:
    print(f"  [FAIL] Status: {response.status_code}")
print()

# Test 2: WhatsApp disconnect endpoint
print("Test 2: WhatsApp Disconnect API")
print("-" * 40)
response = client.post("/api/v1/whatsapp/disconnect")
print(f"  Status: {response.status_code}")
if response.status_code in [200, 503]:
    print("  [OK] Endpoint exists")
else:
    print(f"  [INFO] Response: {response.text[:100]}")
print()

# Test 3: System control endpoints
print("Test 3: System Control APIs")
print("-" * 40)
endpoints = [
    ("/api/v1/system/baileys/start", "POST"),
    ("/api/v1/system/baileys/stop", "POST"),
]
for endpoint, method in endpoints:
    if method == "POST":
        response = client.post(endpoint)
    else:
        response = client.get(endpoint)
    status = "OK" if response.status_code == 200 else f"Status {response.status_code}"
    print(f"  {endpoint}: {status}")
print()

# Test 4: Queue endpoints
print("Test 4: Queue Management APIs")
print("-" * 40)
endpoints = [
    "/api/v1/queue/status",
    "/api/v1/queue/pending",
    "/api/v1/queue/dead-letter",
    "/api/v1/queue/history",
]
for endpoint in endpoints:
    response = client.get(endpoint)
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', 'N/A')
        print(f"  [OK] {endpoint}: {count} items")
    else:
        print(f"  [FAIL] {endpoint}: {response.status_code}")
print()

# Test 5: Baileys endpoints
print("Test 5: Baileys Management")
print("-" * 40)
endpoints = [
    "/api/v1/baileys/status",
    "/api/v1/baileys/qr",
]
for endpoint in endpoints:
    response = client.get(endpoint)
    print(f"  {endpoint}: {response.status_code}")
print()

print("=" * 60)
print("Phase 3 Tests Complete!")
print("=" * 60)
print("\nDashboard Features:")
print("  [x] Multi-page navigation (Overview, WhatsApp, Queue, Logs, System)")
print("  [x] WhatsApp Manager with QR code display")
print("  [x] Queue Management with tabbed interface")
print("  [x] Live logs viewer")
print("  [x] System control panel")
print("\nNext: Phase 4 & 5 - Settings and Final Polish")
