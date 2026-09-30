"""
SmartWasteX Comprehensive Final Audit Verification Suite
=========================================================
Tests all 8 presentation flows outlined in Section 17 of user prompt:
1. Public Website (/, /home)
2. User Signup & Duplicate validation
3. User Login & Dynamic name display & Access control
4. Real Database Leaderboard & No fake users
5. Admin Login & Dynamic admin name & Controls
6. IoT Simulation: Fill increases -> 100% -> No auto reset -> URGENT alert
7. Admin Pickup Scheduling: PENDING -> SCHEDULED -> COMPLETED -> Reset to 0%
8. Session persistence & State stability across refreshes
"""

import os
import sys
import unittest
from datetime import datetime, timezone

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import app
from models import db
from models.models import User, Bin, CollectionRequest, WasteScan, GreenCreditTransaction
from services.iot_simulator import IoTSimulator

def run_final_audit():
    print("=" * 75)
    print("🚀 SMARTWASTEX COMPREHENSIVE FINAL AUDIT VERIFICATION")
    print("=" * 75)

    client = app.test_client()

    with app.app_context():
        # Clean any prior test user if exists
        test_email = "saimore_test@smartwastex.in"
        existing = User.query.filter_by(email=test_email).first()
        if existing:
            GreenCreditTransaction.query.filter_by(user_id=existing.id).delete()
            WasteScan.query.filter_by(user_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

        # -------------------------------------------------------------
        # TEST 1 — PUBLIC WEBSITE
        # -------------------------------------------------------------
        print("\n[TEST 1] Public Website Verification (/)")
        res1 = client.get('/')
        assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
        html1 = res1.data.decode('utf-8')
        assert "SmartWaste" in html1, "SmartWasteX brand missing on homepage"
        assert "Log In" in html1, "Log In button missing on homepage"
        assert "Create Account" in html1, "Create Account button missing on homepage"
        assert "John Doe" not in html1, "Dummy name 'John Doe' found on homepage!"
        assert "Demo User" not in html1, "Dummy name 'Demo User' found on homepage!"
        print("  ✓ TEST 1 PASSED: Homepage loaded cleanly, buttons verified, no dummy names.")

        # -------------------------------------------------------------
        # TEST 2 — USER SIGNUP
        # -------------------------------------------------------------
        print("\n[TEST 2] User Signup & Validation Verification (/signup)")
        # 2a. Signup page loads
        res_signup_page = client.get('/signup')
        assert res_signup_page.status_code == 200
        assert "Create Account" in res_signup_page.data.decode('utf-8')

        # 2b. Password mismatch test
        res_mismatch = client.post('/signup', data={
            'name': 'Sai More',
            'email': test_email,
            'password': 'password123',
            'confirm_password': 'mismatchPassword'
        }, follow_redirects=True)
        assert "Passwords do not match" in res_mismatch.data.decode('utf-8')

        # 2c. Successful signup
        res_signup_ok = client.post('/signup', data={
            'name': 'Sai More',
            'email': test_email,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert res_signup_ok.status_code == 200
        html_signup_ok = res_signup_ok.data.decode('utf-8')
        assert "account has been successfully created" in html_signup_ok.lower()

        # 2d. Prevent duplicate signup
        res_dup = client.post('/signup', data={
            'name': 'Sai More Duplicate',
            'email': test_email,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert "already exists" in res_dup.data.decode('utf-8')
        print("  ✓ TEST 2 PASSED: Signup validation, duplicate prevention, and DB storage verified.")

        # -------------------------------------------------------------
        # TEST 3 — USER LOGIN & DYNAMIC IDENTITY
        # -------------------------------------------------------------
        print("\n[TEST 3] User Login & Identity Verification (/login -> /user/dashboard)")
        res_login = client.post('/login', data={
            'email': test_email,
            'password': 'password123'
        }, follow_redirects=True)
        assert res_login.status_code == 200
        html_dash = res_login.data.decode('utf-8')
        
        # Verify authenticated user's actual registered name is displayed
        assert "Welcome back, Sai More!" in html_dash, "User's registered name not displayed in greeting!"
        assert "Sai More" in html_dash, "User's registered name not in navbar dropdown!"
        assert "John Doe" not in html_dash, "Dummy name 'John Doe' found on dashboard!"
        assert "Demo User" not in html_dash, "Dummy name 'Demo User' found on dashboard!"

        # Verify access control: normal user CANNOT access admin portal
        res_admin_forbidden = client.get('/admin/dashboard', follow_redirects=False)
        assert res_admin_forbidden.status_code in [302, 403], f"User reached admin dashboard! Status: {res_admin_forbidden.status_code}"
        print("  ✓ TEST 3 PASSED: Dynamic user identity verified ('Sai More'), admin routes protected.")

        # -------------------------------------------------------------
        # TEST 4 — LEADERBOARD INTEGRITY
        # -------------------------------------------------------------
        print("\n[TEST 4] Leaderboard Database-backed Integrity (/user/leaderboard)")
        # Give test user some score to verify they appear dynamically
        user_obj = User.query.filter_by(email=test_email).first()
        user_obj.green_credits = 420
        user_obj.items_recycled = 15
        user_obj.waste_diverted_kg = 12.5
        db.session.commit()

        res_lb = client.get('/user/leaderboard')
        assert res_lb.status_code == 200
        html_lb = res_lb.data.decode('utf-8')
        assert "Sai More" in html_lb, "Real user 'Sai More' not found in leaderboard!"
        assert "420" in html_lb, "Real score '420' not found in leaderboard!"
        
        # Verify no hardcoded sample users exist
        assert "Sai K." not in html_lb, "Fake user 'Sai K.' found in leaderboard!"
        assert "Priya M." not in html_lb, "Fake user 'Priya M.' found in leaderboard!"
        assert "Aditya V." not in html_lb, "Fake user 'Aditya V.' found in leaderboard!"
        assert "Sneha R." not in html_lb, "Fake user 'Sneha R.' found in leaderboard!"
        assert "Karan T." not in html_lb, "Fake user 'Karan T.' found in leaderboard!"
        print("  ✓ TEST 4 PASSED: Leaderboard displays real registered users & actual scores only.")

        # -------------------------------------------------------------
        # TEST 5 — ADMIN LOGIN & DYNAMIC IDENTITY
        # -------------------------------------------------------------
        print("\n[TEST 5] Admin Login & Command Center Verification (/login -> /admin/dashboard)")
        client.get('/logout')
        res_admin_login = client.post('/login', data={
            'email': 'admin@smartwastex.in',
            'password': 'admin@123'
        }, follow_redirects=True)
        assert res_admin_login.status_code == 200
        html_admin_dash = res_admin_login.data.decode('utf-8')
        assert "Campus Sustainability Command Center" in html_admin_dash
        assert "Welcome, <strong class=\"text-dark\">Dr. Ananya Rao</strong>" in html_admin_dash
        print("  ✓ TEST 5 PASSED: Admin authenticated, real name ('Dr. Ananya Rao') dynamically rendered.")

        # -------------------------------------------------------------
        # TEST 6 — IoT SIMULATOR: 100% -> NO AUTO-RESET -> FULL ALERT
        # -------------------------------------------------------------
        print("\n[TEST 6] IoT Simulation: Fill to 100%, No Auto-Reset, Alert Generation")
        test_bin = Bin.query.filter_by(id='BIN-02').first()
        assert test_bin is not None
        # Clean any existing active requests on test_bin
        CollectionRequest.query.filter_by(bin_id='BIN-02').delete()
        db.session.commit()

        # Step 1: Set fill level to 100% via IoT telemetry API
        res_iot = client.post('/api/iot/bin-update', json={'bin_id': 'BIN-02', 'fill_level': 100.0})
        assert res_iot.status_code == 200
        iot_data = res_iot.get_json()
        assert iot_data['status'] == 'OVERFLOW'
        assert iot_data['fill_level'] == 100.0
        
        # Verify no automatic reset occurred
        bin_after = Bin.query.get('BIN-02')
        assert bin_after.fill_percentage == 100.0, f"Expected 100.0%, found {bin_after.fill_percentage}% (Auto-reset detected!)"

        # Verify collection request created
        col_req = CollectionRequest.query.filter_by(bin_id='BIN-02', status='PENDING').first()
        assert col_req is not None, "Automated collection request was not created at 100%!"
        assert col_req.priority == 'URGENT'
        print(f"  ✓ TEST 6 PASSED: Bin reached 100.0%, did NOT reset, alert ticket generated: {col_req.request_code}")

        # -------------------------------------------------------------
        # TEST 7 — ADMIN PICKUP LIFECYCLE (PENDING -> SCHEDULED -> COMPLETED -> 0%)
        # -------------------------------------------------------------
        print("\n[TEST 7] Pickup Lifecycle: PENDING -> SCHEDULED -> COMPLETED -> 0% Reset")
        # Step 7a: Admin schedules pickup
        res_sched = client.post(f'/admin/collections/{col_req.id}/schedule', data={
            'pickup_date': '2026-10-02',
            'pickup_time': '10:00'
        }, follow_redirects=True)
        assert res_sched.status_code == 200
        req_sched = CollectionRequest.query.get(col_req.id)
        assert req_sched.status == 'SCHEDULED'
        print(f"  ✓ Lifecycle step 1: Request {col_req.request_code} transitioned to SCHEDULED.")

        # Step 7b: Bin remains full while scheduled
        bin_during = Bin.query.get('BIN-02')
        assert bin_during.fill_percentage == 100.0

        # Step 7c: Admin marks pickup as COMPLETED
        res_comp = client.post(f'/admin/collections/{col_req.id}/status', data={
            'status': 'COMPLETED'
        }, follow_redirects=True)
        assert res_comp.status_code == 200
        req_comp = CollectionRequest.query.get(col_req.id)
        assert req_comp.status == 'COMPLETED'

        # Step 7d: Bin now resets to 0.0%
        bin_reset = Bin.query.get('BIN-02')
        assert bin_reset.fill_percentage == 0.0, f"Expected 0.0% after completion, got {bin_reset.fill_percentage}%"
        print(f"  ✓ Lifecycle step 2: Request marked COMPLETED. Bin reset to 0.0% [NORMAL].")
        print("  ✓ TEST 7 PASSED: Full pickup lifecycle verified from dispatch to tank clearance.")

        # -------------------------------------------------------------
        # TEST 8 — REFRESH & PERSISTENCE
        # -------------------------------------------------------------
        print("\n[TEST 8] Refresh & State Persistence Verification")
        res_refresh = client.get('/admin/dashboard')
        assert res_refresh.status_code == 200
        html_refresh = res_refresh.data.decode('utf-8')
        assert "Dr. Ananya Rao" in html_refresh
        bin_persist = Bin.query.get('BIN-02')
        assert bin_persist.fill_percentage == 0.0
        print("  ✓ TEST 8 PASSED: State persists across requests with no session corruption.")

    print("\n" + "=" * 75)
    print("🏆 ALL 8 FINAL AUDIT TESTS COMPLETED WITH 100% SUCCESS!")
    print("=" * 75)

if __name__ == '__main__':
    run_final_audit()
