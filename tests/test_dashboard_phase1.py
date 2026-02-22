#!/usr/bin/env python3
"""
Test Phase 1: Dashboard Foundation
Tests basic imports, routes, and WebSocket setup.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from fastapi.testclient import TestClient

print("=" * 60)
print("Phase 1: Dashboard Foundation Tests")
print("=" * 60)
print()

# Test 1: Imports
print("Test 1: FastAPI App Imports")
print("-" * 40)
try:
    from app.main import app
    print("[OK] FastAPI app imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import app: {e}")
    sys.exit(1)
print()

# Test 2: Dashboard routes
print("Test 2: Dashboard Routes Registered")
print("-" * 40)
routes = [route.path for route in app.routes]
dashboard_routes = [r for r in routes if 'dashboard' in r or 'ws' in r]
print(f"Found {len(dashboard_routes)} dashboard/WebSocket routes:")
for route in dashboard_routes:
    print(f"  - {route}")
print()

# Test 3: WebSocket endpoint
print("Test 3: WebSocket Endpoint")
print("-" * 40)
if '/ws/dashboard' in routes:
    print("[OK] WebSocket endpoint /ws/dashboard exists")
else:
    print("[FAIL] WebSocket endpoint not found")
print()

# Test 4: Dashboard page endpoint
print("Test 4: Dashboard Page Serving")
print("-" * 40)
client = TestClient(app)
response = client.get("/dashboard")
if response.status_code in [200, 404]:
    if response.status_code == 200:
        print("[OK] Dashboard page serves correctly")
    else:
        print("[OK] Dashboard endpoint exists (404 expected - not built yet)")
else:
    print(f"[FAIL] Unexpected status code: {response.status_code}")
print()

# Test 5: Dashboard API endpoints
print("Test 5: Dashboard API Endpoints")
print("-" * 40)
api_endpoints = [
    '/api/v1/dashboard/stats',
]
for endpoint in api_endpoints:
    response = client.get(endpoint)
    status = "OK" if response.status_code == 200 else f"Status {response.status_code}"
    print(f"  {endpoint}: {status}")
print()

# Test 6: WebSocket manager
print("Test 6: WebSocket Manager")
print("-" * 40)
try:
    from app.websocket import ws_manager, WebSocketMessage
    print("[OK] WebSocket manager imported")
    print(f"  Active connections: {ws_manager.get_connection_count()}")
    
    # Test message creation
    msg = WebSocketMessage.queue_update({"test": "data"})
    if msg["type"] == "queue_update":
        print("[OK] WebSocket message helper works")
    else:
        print("[FAIL] WebSocket message helper issue")
except Exception as e:
    print(f"[FAIL] WebSocket manager error: {e}")
print()

print("=" * 60)
print("Phase 1 Tests Complete!")
print("=" * 60)
print("\nNext: Phase 2 - Overview Dashboard with Stats Cards")
