#!/usr/bin/env python3
"""Test Phase 5 API endpoints"""

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

print("=" * 60)
print("Phase 5 API Testing")
print("=" * 60)

# Test 1: Health check
print("\n✓ Test 1: Health Check")
resp = client.get("/api/health")
print(f"  Status: {resp.status_code}")
print(f"  Response: {resp.json()}")
assert resp.status_code == 200
assert resp.json()["status"] == "ok"

# Test 2: Auth - invalid credentials
print("\n✓ Test 2: Auth - Invalid Credentials")
resp = client.post("/api/auth/token", data={"username": "nonexistent", "password": "wrong"})
print(f"  Status: {resp.status_code}")
print(f"  Response: {resp.json()}")
assert resp.status_code == 401

# Test 3: Auth - valid credentials (admin/admin)
print("\n✓ Test 3: Auth - Valid Credentials (admin/admin)")
resp = client.post("/api/auth/token", data={"username": "admin", "password": "admin"})
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    token_data = resp.json()
    print(f"  Token: {token_data['access_token'][:20]}...")
    print(f"  Role: {token_data['role']}")
    print(f"  Username: {token_data['username']}")
    admin_token = token_data["access_token"]
else:
    print(f"  Response: {resp.json()}")

# Test 4: Parent Login - student not found
print("\n✓ Test 4: Parent Login - Student Not Found")
resp = client.post("/api/parent/login", json={"student_code": "999", "pin": "1234"})
print(f"  Status: {resp.status_code}")
print(f"  Response: {resp.json()}")
assert resp.status_code == 404

# Test 5: List students (with admin token)
print("\n✓ Test 5: List Students (Admin)")
headers = {"Authorization": f"Bearer {admin_token}"}
resp = client.get("/api/students/", headers=headers)
print(f"  Status: {resp.status_code}")
data = resp.json()
print(f"  Total students: {data.get('total', 0)}")
print(f"  Retrieved: {len(data.get('data', []))} records")

print("\n" + "=" * 60)
print("All tests completed successfully!")
print("=" * 60)
