#!/usr/bin/env python3
"""
Test Phase 2: Overview Dashboard with Stats Cards
Tests the dashboard page serving and stats API.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

print("=" * 60)
print("Phase 2: Overview Dashboard Tests")
print("=" * 60)
print()

client = TestClient(app)

# Test 1: Dashboard page serving
print("Test 1: Dashboard Page Serving")
print("-" * 40)
response = client.get("/dashboard")
if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
    print("[OK] Dashboard serves HTML successfully")
    print(f"  Content length: {len(response.text)} characters")
else:
    print(f"[FAIL] Status: {response.status_code}")
print()

# Test 2: Dashboard stats API
print("Test 2: Dashboard Stats API")
print("-" * 40)
response = client.get("/api/v1/dashboard/stats")
if response.status_code == 200:
    data = response.json()
    print("[OK] Stats API returns data")
    print(f"  Keys: {', '.join(data.keys())}")
    
    # Check required fields
    checks = [
        ("system.version", data.get("system", {}).get("version")),
        ("system.database_connected", data.get("system", {}).get("database_connected") is not None),
        ("queue.pending", data.get("queue", {}).get("pending") is not None),
        ("queue.total_sent", data.get("queue", {}).get("total_sent") is not None),
        ("messages.sent_today", data.get("messages", {}).get("sent_today") is not None),
    ]
    
    for field, value in checks:
        if value:
            print(f"  [OK] {field}")
        else:
            print(f"  [FAIL] {field} missing")
else:
    print(f"[FAIL] Status: {response.status_code}")
    print(f"  Error: {response.text[:100]}")
print()

# Test 3: Activity API
print("Test 3: Activity API")
print("-" * 40)
response = client.get("/api/v1/dashboard/activity")
if response.status_code == 200:
    data = response.json()
    print("[OK] Activity API works")
    print(f"  Messages: {data.get('count', 0)}")
else:
    print(f"[FAIL] Status: {response.status_code}")
print()

# Test 4: Dashboard HTML content
print("Test 4: Dashboard HTML Content")
print("-" * 40)
response = client.get("/dashboard")
content = response.text

checks = [
    ("HTML structure", "<!DOCTYPE html>" in content),
    ("Title", "Busy WhatsApp Gateway" in content),
    ("Stats cards", 'id="messages-today"' in content),
    ("JavaScript", "fetch('/api/v1/dashboard/stats')" in content),
    ("Styling", "style" in content),
]

for check_name, result in checks:
    status = "OK" if result else "FAIL"
    print(f"  [{status}] {check_name}")
print()

print("=" * 60)
print("Phase 2 Tests Complete!")
print("=" * 60)
print("\nNext: Phase 3 - WhatsApp Manager and Queue Management")
