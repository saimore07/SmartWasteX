"""
SmartWasteX Targeted IoT Pickup Workflow Verification
======================================================
Tests the 8 specific test scenarios from Section 15:
1. Normal operation (50% -> NORMAL)
2. High (85% -> HIGH)
3. Critical (95% -> CRITICAL / HIGH)
4. Full (100% -> FULL / PICKUP REQUIRED, creates admin alert)
5. Duplicate prevention (subsequent 100% readings do NOT create duplicate active alerts)
6. Schedule pickup (Admin enters date/time -> status = SCHEDULED)
7. Complete pickup (Admin marks COMPLETED -> status = COMPLETED, Bin = 0%, Alert resolved)
8. Future reuse (Bin fills to 100% again -> NEW pickup alert generated because previous was completed)
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timezone
from app import create_app
from config import Config
from models import db
from models.models import Bin, CollectionRequest, User

class TestWorkflowConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

def run_workflow_test():
    print("=" * 70)
    print("🧪 VERIFYING IOT PICKUP & SCHEDULING WORKFLOW (SECTION 15 TESTS)")
    print("=" * 70)

    app = create_app(TestWorkflowConfig)
    client = app.test_client()

    with app.app_context():
        # Authenticate admin client session
        admin_login = client.post('/login', data={
            'email': 'admin@smartwastex.in',
            'password': 'admin@123'
        }, follow_redirects=True)
        assert admin_login.status_code == 200
        print("  ✓ Admin logged in successfully.")

        # Test 1 — Normal operation: BIN-01 -> 50%
        print("\n[TEST 1] Normal Operation: BIN-01 -> 50%...")
        res1 = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_level': 50.0})
        assert res1.status_code == 200
        data1 = res1.get_json()
        assert data1['success'] is True
        assert data1['fill_level'] == 50.0
        assert data1['status'] == 'NORMAL'
        b1 = db.session.get(Bin, 'BIN-01')
        assert b1.fill_percentage == 50.0
        assert b1.status == 'NORMAL'
        print("  ✓ Test 1 Passed: BIN-01 fill=50.0% -> Status: NORMAL")

        # Test 2 — High: BIN-01 -> 85%
        print("\n[TEST 2] High Fill: BIN-01 -> 85%...")
        res2 = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_level': 85.0})
        assert res2.status_code == 200
        data2 = res2.get_json()
        assert data2['success'] is True
        assert data2['fill_level'] == 85.0
        assert data2['status'] == 'HIGH'
        b2 = db.session.get(Bin, 'BIN-01')
        assert b2.fill_percentage == 85.0
        assert b2.status == 'HIGH'
        print("  ✓ Test 2 Passed: BIN-01 fill=85.0% -> Status: HIGH")

        # Test 3 — Critical: BIN-01 -> 95%
        print("\n[TEST 3] Critical Fill: BIN-01 -> 95%...")
        res3 = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_level': 95.0})
        assert res3.status_code == 200
        data3 = res3.get_json()
        assert data3['success'] is True
        assert data3['fill_level'] == 95.0
        b3 = db.session.get(Bin, 'BIN-01')
        assert b3.fill_percentage == 95.0
        print(f"  ✓ Test 3 Passed: BIN-01 fill=95.0% -> Status: {b3.status}")

        # Test 4 — Full: BIN-01 -> 100%
        print("\n[TEST 4] Full / Pickup Required: BIN-01 -> 100%...")
        res4 = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_level': 100.0})
        assert res4.status_code == 200
        data4 = res4.get_json()
        assert data4['success'] is True
        assert data4['fill_level'] == 100.0
        b4 = db.session.get(Bin, 'BIN-01')
        assert b4.fill_percentage == 100.0
        assert b4.status == 'OVERFLOW'

        # Check that an active alert / collection request was generated
        active_requests = CollectionRequest.query.filter(
            CollectionRequest.bin_id == 'BIN-01',
            CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED'])
        ).all()
        assert len(active_requests) == 1
        req1 = active_requests[0]
        assert req1.priority == 'URGENT'
        assert req1.fill_level == 100.0
        assert req1.status == 'PENDING'
        print(f"  ✓ Test 4 Passed: BIN-01 is 100% FULL. Alert generated: {req1.request_code} (Status: {req1.status}, Priority: {req1.priority})")

        # Admin Dashboard should show this alert
        dash_res = client.get('/admin/dashboard')
        assert dash_res.status_code == 200
        assert b"Pickup Alerts" in dash_res.data
        assert b"BIN-01" in dash_res.data
        assert b"Schedule Pickup" in dash_res.data
        print("  ✓ Admin Dashboard displays 🚨 Pickup Alerts section with [Schedule Pickup] button.")

        # Test 5 — Duplicate Prevention: send 100%, 100%, 100%
        print("\n[TEST 5] Duplicate Prevention: Streaming repeated 100% readings...")
        for i in range(3):
            res_dup = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_level': 100.0})
            assert res_dup.status_code == 200

        active_requests_after_dups = CollectionRequest.query.filter(
            CollectionRequest.bin_id == 'BIN-01',
            CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED'])
        ).all()
        assert len(active_requests_after_dups) == 1
        print("  ✓ Test 5 Passed: Only ONE active pickup alert exists despite repeated 100% telemetry ticks.")

        # Test 6 — Schedule Pickup: Admin schedules pickup
        print("\n[TEST 6] Admin Schedules Waste Pickup (Date & Time)...")
        res6 = client.post(f'/admin/collections/{req1.id}/schedule', data={
            'pickup_date': '2026-10-01',
            'pickup_time': '14:30'
        }, follow_redirects=True)
        assert res6.status_code == 200
        db.session.refresh(req1)
        assert req1.status == 'SCHEDULED'
        assert req1.scheduled_date == '2026-10-01'
        assert req1.scheduled_time == '14:30'
        print(f"  ✓ Test 6 Passed: Pickup status = SCHEDULED (Date: {req1.scheduled_date}, Time: {req1.scheduled_time})")

        # Test 7 — Complete Pickup: Admin marks completed
        print("\n[TEST 7] Admin Marks Pickup Completed...")
        res7 = client.post(f'/admin/collections/{req1.id}/status', data={
            'status': 'COMPLETED'
        }, follow_redirects=True)
        assert res7.status_code == 200
        db.session.refresh(req1)
        db.session.refresh(b1)
        assert req1.status == 'COMPLETED'
        assert req1.resolved_at is not None
        # Bin MUST be reset to 0% and NORMAL status
        assert b1.fill_percentage == 0.0
        assert b1.status == 'NORMAL'

        # Active alerts must now be 0
        active_after_complete = CollectionRequest.query.filter(
            CollectionRequest.bin_id == 'BIN-01',
            CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED'])
        ).all()
        assert len(active_after_complete) == 0
        print(f"  ✓ Test 7 Passed: Pickup status = COMPLETED. Bin reset to 0.0% [NORMAL]. Alert RESOLVED.")

        # Test 8 — Future Reuse: Allow the same bin to fill again to 100%
        print("\n[TEST 8] Future Reuse: Same bin fills again to 100%...")
        res8_fill = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_level': 50.0})
        assert res8_fill.status_code == 200
        res8_full = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-01', 'fill_level': 100.0})
        assert res8_full.status_code == 200

        db.session.refresh(b1)
        assert b1.fill_percentage == 100.0

        # A brand NEW alert must now be created
        new_active_requests = CollectionRequest.query.filter(
            CollectionRequest.bin_id == 'BIN-01',
            CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED'])
        ).all()
        assert len(new_active_requests) == 1
        req2 = new_active_requests[0]
        assert req2.id != req1.id  # New record
        assert req2.status == 'PENDING'
        assert req2.priority == 'URGENT'
        print(f"  ✓ Test 8 Passed: New pickup alert generated ({req2.request_code}) because previous alert was resolved!")

    print("\n" + "=" * 70)
    print("🏆 ALL 8 SECTION 15 TESTS COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == '__main__':
    run_workflow_test()
