"""
SmartWasteX QR Code Generation Service
======================================
Generates QR codes for institutional e-waste assets linked to the
public Digital E-Waste Passport page.
"""

import os
import qrcode
from PIL import Image

class QRService:
    @staticmethod
    def generate_asset_qr(asset_id, base_url=None, output_dir=None):
        """
        Generates a crisp QR code PNG pointing to the public e-waste passport URL.
        Returns the relative filename (e.g., 'qr_codes/EW-2026-0001.png').
        """
        if base_url is None:
            base_url = os.environ.get('RENDER_EXTERNAL_URL', os.environ.get('BASE_URL', 'http://127.0.0.1:5000'))

        if output_dir is None:
            # Default to static/qr_codes directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(os.path.dirname(current_dir), 'static', 'qr_codes')

        os.makedirs(output_dir, exist_ok=True)

        target_url = f"{base_url.rstrip('/')}/ewaste/{asset_id}"

        # Configure QR code with high error correction and nice presentation
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3,
        )
        qr.add_data(target_url)
        qr.make(fit=True)

        # High-contrast eco-styled QR (dark slate foreground on white)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")

        filename = f"{asset_id}.png"
        filepath = os.path.join(output_dir, filename)
        img.save(filepath)

        return f"qr_codes/{filename}"

qr_service = QRService()
