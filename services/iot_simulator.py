"""
SmartWasteX IoT Telemetry Simulator
===================================
Simulates real-time edge telemetry for smart campus waste receptacles.
Calculates fill level, load weight, temperature, and battery levels,
and triggers automatic overflow alerts and collection requests.
"""

import random
from datetime import datetime, timezone
from models import db
from models.models import Bin, BinReading, CollectionRequest

class IoTSimulator:
    """Simulates smart-bin hardware sensors and handles telemetry transitions."""

    @staticmethod
    def get_max_weight_for_bin(waste_type):
        """Returns realistic maximum bin capacity weight in kg."""
        if 'E-Waste' in waste_type or 'Hazardous' in waste_type:
            return 35.0
        elif 'Biodegradable' in waste_type:
            return 28.0
        else:
            return 20.0

    @classmethod
    def update_bin_telemetry(cls, bin_obj, new_fill_pct):
        """
        Updates bin fill level, recalculates weight, temperature, battery,
        and manages alert/collection request triggers.
        """
        new_fill_pct = max(0.0, round(new_fill_pct, 1))
        bin_obj.fill_percentage = new_fill_pct

        # Recalculate estimated weight based on fill percentage
        max_wt = cls.get_max_weight_for_bin(bin_obj.waste_type)
        bin_obj.weight_kg = round((new_fill_pct / 100.0) * max_wt + random.uniform(-0.4, 0.4), 1)
        bin_obj.weight_kg = max(0.0, bin_obj.weight_kg)

        # Realistic simulated ambient temperature (26 - 33 C)
        bin_obj.temperature_c = round(27.0 + (new_fill_pct / 100.0) * 5.0 + random.uniform(-1.0, 1.0), 1)

        # Battery fluctuation (drains very slowly or simulated 70-98%)
        if not bin_obj.battery_level or bin_obj.battery_level <= 10:
            bin_obj.battery_level = 95.0
        else:
            bin_obj.battery_level = max(15.0, round(bin_obj.battery_level - random.uniform(0.0, 0.2), 1))

        # Status rules:
        # fill < 70: NORMAL
        # 70 <= fill < 85: WARNING
        # 85 <= fill < 100: HIGH
        # fill >= 100: OVERFLOW
        bin_obj.status = bin_obj.calculate_status()
        bin_obj.last_updated = datetime.now(timezone.utc)

        # Record sensor reading in historical table
        reading = BinReading(
            bin_id=bin_obj.id,
            fill_percentage=bin_obj.fill_percentage,
            weight_kg=bin_obj.weight_kg,
            temperature_c=bin_obj.temperature_c,
            battery_level=bin_obj.battery_level,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(reading)

        # Check collection request triggers
        alert_info = cls._check_collection_alerts(bin_obj)

        db.session.commit()
        return bin_obj, alert_info

    @classmethod
    def _check_collection_alerts(cls, bin_obj):
        """
        Generates collection requests and alert payloads when fill thresholds are crossed.
        """
        alert_info = None

        if bin_obj.fill_percentage >= 85:
            is_overflow = bin_obj.fill_percentage >= 100
            priority = 'URGENT' if is_overflow else 'HIGH'
            alert_type = 'OVERFLOW' if is_overflow else 'HIGH_FILL'
            alert_msg = (
                f"🚨 URGENT OVERFLOW ALERT: {bin_obj.id} ({bin_obj.name}) is at {bin_obj.fill_percentage}% capacity!"
                if is_overflow else
                f"⚠️ High Fill Warning: {bin_obj.id} ({bin_obj.name}) is at {bin_obj.fill_percentage}%. Collection recommended."
            )

            # Check if there is an active pending or assigned collection request already
            existing_request = CollectionRequest.query.filter(
                CollectionRequest.bin_id == bin_obj.id,
                CollectionRequest.status.in_(['PENDING', 'ASSIGNED'])
            ).first()

            if not existing_request:
                # Create a new automated collection request
                req_code = f"CR-{bin_obj.id[-2:]}-{datetime.now().strftime('%H%M%S')}"
                col_req = CollectionRequest(
                    request_code=req_code,
                    bin_id=bin_obj.id,
                    waste_type=bin_obj.waste_type,
                    location=bin_obj.location,
                    fill_level=bin_obj.fill_percentage,
                    priority=priority,
                    status='PENDING',
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(col_req)
            elif is_overflow and existing_request.priority != 'URGENT':
                existing_request.priority = 'URGENT'
                existing_request.fill_level = bin_obj.fill_percentage

            alert_info = {
                'triggered': True,
                'alert_type': alert_type,
                'message': alert_msg,
                'priority': priority
            }

        return alert_info

    @classmethod
    def simulate_delta(cls, bin_id, delta_pct):
        """Applies a positive or negative percentage delta to bin fill level."""
        bin_obj = db.session.get(Bin, bin_id)
        if not bin_obj:
            return None, None
        new_fill = bin_obj.fill_percentage + delta_pct
        return cls.update_bin_telemetry(bin_obj, new_fill)

    @classmethod
    def simulate_random(cls, bin_id):
        """Generates random realistic telemetry for a bin."""
        bin_obj = db.session.get(Bin, bin_id)
        if not bin_obj:
            return None, None
        # Generate random fill level between 25% and 100%
        random_fill = random.uniform(30.0, 100.0)
        return cls.update_bin_telemetry(bin_obj, random_fill)

    @classmethod
    def empty_bin(cls, bin_id):
        """Empties the bin (fill = 0%), marks pending collection requests completed."""
        bin_obj = db.session.get(Bin, bin_id)
        if not bin_obj:
            return None, None

        # Resolve open collection requests for this bin
        open_requests = CollectionRequest.query.filter(
            CollectionRequest.bin_id == bin_id,
            CollectionRequest.status.in_(['PENDING', 'ASSIGNED'])
        ).all()
        for req in open_requests:
            req.status = 'COMPLETED'
            req.resolved_at = datetime.now(timezone.utc)

        bin_obj, alert_info = cls.update_bin_telemetry(bin_obj, 0.0)
        return bin_obj, alert_info
