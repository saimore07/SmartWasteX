"""
SmartWasteX Comprehensive End-to-End Scenario Verification Script
Executes all 26 exact steps specified in the hackathon challenge prompt.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app
from config import Config
from models import db
from models.models import User, Bin, CollectionRequest, EWasteAsset, EWasteLifecycle, WasteScan, GreenCreditTransaction

class E2EConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

def run_end_to_end_test():
    print("=" * 70)
    print("🚀 STARTING SMARTWASTEX 26-STEP END-TO-END VERIFICATION")
    print("=" * 70)

    app = create_app(E2EConfig)
    client = app.test_client()

    with app.app_context():
        # STEP 1: Login as user
        print("\n[STEP 1] Logging in as user (user1@smartwastex.in)...")
        res1 = client.post('/login', data={
            'email': 'user1@smartwastex.in',
            'password': 'user1@123'
        }, follow_redirects=True)
        assert res1.status_code == 200
        assert b"Welcome back, Rahul" in res1.data or b"Dashboard" in res1.data
        user = User.query.filter_by(email='user1@smartwastex.in').first()
        initial_credits = user.green_credits
        initial_items = user.items_recycled
        print(f"  ✓ User logged in successfully! Credits: {initial_credits}, Items: {initial_items}")

        # STEP 2: Open Scan Waste
        print("\n[STEP 2] Opening Scan Waste page (/user/scan)...")
        res2 = client.get('/user/scan')
        assert res2.status_code == 200
        assert b"AI Waste Segregation Scanner" in res2.data
        print("  ✓ Scan Waste page loaded.")

        # STEP 3: Upload a sample waste image
        print("\n[STEP 3] Uploading sample waste image ('battery')...")
        res3 = client.post('/user/scan', data={'sample_item': 'battery'}, follow_redirects=False)
        assert res3.status_code == 302
        redirect_url = res3.headers['Location']
        print(f"  ✓ Image submitted. Redirecting to analysis: {redirect_url}")

        # STEP 4 & 5: Receive classification & Show disposal recommendation
        print("\n[STEP 4 & 5] Receiving classification and disposal recommendation...")
        res4 = client.get(redirect_url)
        assert res4.status_code == 200
        assert b"AI Waste Analysis" in res4.data
        assert b"Hazardous / E-Waste" in res4.data
        assert b"Recommended Action" in res4.data
        assert b"Dispose Responsibly" in res4.data
        scan_id = int(redirect_url.split('/')[-1])
        scan_obj = db.session.get(WasteScan, scan_id)
        assert scan_obj is not None
        print(f"  ✓ Classification: {scan_obj.detected_item} | Category: {scan_obj.category} | Confidence: {scan_obj.confidence}%")
        print(f"  ✓ Recommendation: {scan_obj.recommendation}")
        print(f"  ✓ Nearest Bin: {scan_obj.nearest_bin_id} | Credits: +{scan_obj.credits_awarded}")

        # STEP 6: Confirm responsible disposal
        print("\n[STEP 6] Confirming responsible disposal...")
        res6 = client.post(f'/user/waste/confirm/{scan_id}', follow_redirects=True)
        assert res6.status_code == 200
        assert b"Disposal Successfully Confirmed" in res6.data
        print("  ✓ Disposal confirmed successfully.")

        # STEP 7: Verify Green Credits increased
        print("\n[STEP 7] Verifying Green Credits increased in database...")
        user = db.session.get(User, user.id)
        assert user.green_credits == initial_credits + scan_obj.credits_awarded
        assert user.items_recycled == initial_items + 1
        print(f"  ✓ Green credits updated from {initial_credits} to {user.green_credits} (+{scan_obj.credits_awarded})")

        # STEP 8: Verify activity history updated
        print("\n[STEP 8] Verifying activity history updated...")
        res8 = client.get('/user/history')
        assert res8.status_code == 200
        assert b"Lithium Battery" in res8.data
        txn = GreenCreditTransaction.query.filter_by(reference_id=f"SCAN-{scan_id}").first()
        assert txn is not None
        print(f"  ✓ Activity transaction record verified: {txn.description}")

        # STEP 9: Open leaderboard
        print("\n[STEP 9] Opening leaderboard (/user/leaderboard)...")
        res9 = client.get('/user/leaderboard')
        assert res9.status_code == 200
        assert b"Campus Green Champions" in res9.data
        assert b"Rahul Sharma" in res9.data
        print("  ✓ Leaderboard loaded and highlighted current user.")

        # STEP 10: Logout
        print("\n[STEP 10] Logging out user...")
        res10 = client.get('/logout', follow_redirects=True)
        assert res10.status_code == 200
        assert b"logged out" in res10.data
        print("  ✓ User logged out.")

        # STEP 11: Login as admin
        print("\n[STEP 11] Logging in as admin (admin@smartwastex.in)...")
        res11 = client.post('/login', data={
            'email': 'admin@smartwastex.in',
            'password': 'admin@123'
        }, follow_redirects=True)
        assert res11.status_code == 200
        assert b"Campus Sustainability Command Center" in res11.data
        print("  ✓ Admin authenticated successfully.")

        # STEP 12: Open Smart Bins
        print("\n[STEP 12] Opening Smart Bins view (/admin/bins)...")
        res12 = client.get('/admin/bins')
        assert res12.status_code == 200
        assert b"BIN-04" in res12.data
        print("  ✓ Smart Bins view loaded.")

        # STEP 13 & 14 & 15: Select BIN-04, simulate +10%, verify capacity changes
        print("\n[STEP 13, 14, 15] Simulating +10% on BIN-04 and verifying capacity changes...")
        bin4_before = db.session.get(Bin, 'BIN-04')
        fill_before = bin4_before.fill_percentage
        res14 = client.post('/api/bins/BIN-04/simulate', json={'action': 'plus_10'})
        assert res14.status_code == 200
        bin4_after = db.session.get(Bin, 'BIN-04')
        assert bin4_after.fill_percentage == fill_before + 10.0
        print(f"  ✓ BIN-04 fill changed from {fill_before}% to {bin4_after.fill_percentage}%")

        # STEP 16 & 17 & 18: Push bin to 100%, verify overflow alert and collection request
        print("\n[STEP 16, 17, 18] Pushing BIN-04 to 100% capacity, checking overflow alert & collection request...")
        res16 = client.post('/api/bins/BIN-04/simulate', json={'action': 'set_fill', 'fill': 100.0})
        assert res16.status_code == 200
        data16 = res16.get_json()
        assert data16['bin']['status'] == 'OVERFLOW'
        assert data16['alert']['priority'] == 'URGENT'

        urgent_req = CollectionRequest.query.filter_by(bin_id='BIN-04', priority='URGENT').first()
        assert urgent_req is not None
        print(f"  ✓ Bin status: OVERFLOW | Alert: {data16['alert']['message']}")
        print(f"  ✓ Collection ticket created: {urgent_req.request_code} | Priority: {urgent_req.priority} | Status: {urgent_req.status}")

        # STEP 19 & 20 & 21: Open E-Waste, create asset, generate QR code
        print("\n[STEP 19, 20, 21] Opening E-Waste, creating asset, generating QR code...")
        res20 = client.post('/admin/ewaste', data={
            'device_name': 'Apple MacBook Pro M1',
            'category': 'Computing',
            'serial_number': 'SN-APPL-M1-2022',
            'location': 'Design Lab 4',
            'weight_kg': 1.6,
            'recycler': 'EcoRecycle Solutions Hub',
            'notes': 'Battery service required; decommissioned for parts reclamation.'
        }, follow_redirects=True)
        assert res20.status_code == 200
        new_asset = EWasteAsset.query.filter_by(device_name='Apple MacBook Pro M1').first()
        assert new_asset is not None
        assert new_asset.asset_id.startswith('EW-2026-')
        assert new_asset.qr_code_filename is not None
        print(f"  ✓ Asset created: {new_asset.asset_id} ({new_asset.device_name})")
        print(f"  ✓ QR Code generated: {new_asset.qr_code_filename}")

        # STEP 22: Update lifecycle stages: REGISTERED -> DECOMMISSIONED -> COLLECTION_REQUESTED -> COLLECTED -> SENT_TO_RECYCLER -> RECYCLED
        print("\n[STEP 22] Progressing asset through all lifecycle stages...")
        stages_to_test = [
            'DECOMMISSIONED',
            'COLLECTION_REQUESTED',
            'COLLECTED',
            'SENT_TO_RECYCLER',
            'RECYCLED'
        ]
        for st in stages_to_test:
            res_st = client.post(f'/admin/ewaste/{new_asset.asset_id}', data={
                'status': st,
                'notes': f'Verification of stage: {st}'
            }, follow_redirects=True)
            assert res_st.status_code == 200
            refreshed_asset = db.session.get(EWasteAsset, new_asset.id)
            assert refreshed_asset.current_status == st
            print(f"  ✓ Advanced to: {st}")

        # STEP 23 & 24: Open QR/public asset page and verify lifecycle
        print("\n[STEP 23 & 24] Opening public read-only QR asset page and verifying lifecycle...")
        # Access with clean client (no admin session required)
        anon_client = app.test_client()
        res23 = anon_client.get(f'/ewaste/{new_asset.asset_id}')
        assert res23.status_code == 200
        assert b"E-WASTE DIGITAL PASSPORT" in res23.data
        assert new_asset.asset_id.encode() in res23.data
        assert b"Apple MacBook Pro M1" in res23.data
        assert b"RECYCLED" in res23.data
        print(f"  ✓ Public Digital Passport verified for {new_asset.asset_id} (Status: RECYCLED)")

        # STEP 25 & 26: Open Analytics and verify charts and metrics
        print("\n[STEP 25 & 26] Opening Analytics and verifying charts and metrics...")
        res25 = client.get('/admin/analytics')
        assert res25.status_code == 200
        assert b"Campus Spatial & Sustainability Analytics" in res25.data
        assert b"campusMap" in res25.data
        assert b"Campus Segregation Accuracy" in res25.data
        assert b"Landfill Diversion Rate" in res25.data
        print("  ✓ Analytics and GIS Leaflet campus map verified.")

    print("\n" + "=" * 70)
    print("🎉 ALL 26 END-TO-END SCENARIO STEPS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == '__main__':
    run_end_to_end_test()
