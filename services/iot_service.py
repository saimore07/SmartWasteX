"""
SmartWasteX IoT Hardware Telemetry & Monitoring Service
======================================================
Production sensor telemetry service for smart institutional waste bins.
Ingests real physical sensor readings, validates payloads against physical tolerances,
updates bin state, appends to immutable time-series reading ledger, and manages
collection ticket creation and urgent overflow escalations according to institutional rules.
"""

from datetime import datetime, timezone
from models import db
from models.models import Bin, BinReading, CollectionRequest


class IoTService:
    """Service handling real-world hardware IoT sensor ingestion and telemetry processing."""

    # Physical sensor tolerance limits
    MIN_FILL_PCT = 0.0
    MAX_FILL_PCT = 100.0
    MIN_WEIGHT_KG = 0.0
    MAX_WEIGHT_KG = 500.0
    MIN_TEMP_C = -40.0
    MAX_TEMP_C = 85.0
    MIN_BATTERY_PCT = 0.0
    MAX_BATTERY_PCT = 100.0

    @classmethod
    def resolve_bin(cls, raw_bin_id):
        """
        Resolves raw bin ID to a Bin instance.
        Handles numeric IDs (1 -> BIN-01), padded strings (BIN-002 -> BIN-02),
        and direct string matches (BIN-01).
        """
        if raw_bin_id is None:
            return None

        str_id = str(raw_bin_id).strip().upper()
        if not str_id:
            return None

        # 1. Exact match (e.g. 'BIN-01')
        bin_obj = db.session.get(Bin, str_id)
        if bin_obj:
            return bin_obj

        # 2. Integer or digit string to 'BIN-XX' (e.g. 1 or '1' -> 'BIN-01')
        try:
            num = int(str_id)
            padded_id = f"BIN-{num:02d}"
            bin_obj = db.session.get(Bin, padded_id)
            if bin_obj:
                return bin_obj
        except ValueError:
            pass

        # 3. 'BIN-<num>' normalization (e.g. 'BIN-1', 'BIN-001' -> 'BIN-01')
        if str_id.startswith('BIN-'):
            suffix = str_id.split('-', 1)[1]
            try:
                num = int(suffix)
                padded_id = f"BIN-{num:02d}"
                bin_obj = db.session.get(Bin, padded_id)
                if bin_obj:
                    return bin_obj
            except ValueError:
                pass

        return None

    @classmethod
    def validate_payload(cls, data):
        """
        Validates incoming sensor payload against schemas and physical tolerances.
        Returns: (is_valid: bool, error_message: str or None, parsed_values: dict or None)
        """
        if not data or not isinstance(data, dict):
            return False, "JSON payload required", None

        # 1. Validate bin_id presence
        raw_bin_id = data.get('bin_id')
        if raw_bin_id is None or str(raw_bin_id).strip() == '':
            return False, "bin_id is required", None

        # Handle hardware tare/empty request
        if data.get('action') == 'empty':
            return True, None, {'action': 'empty', 'raw_bin_id': raw_bin_id}

        # 2. Validate fill percentage (supports fill_percentage, fill_level, or fill)
        fill_val = data.get('fill_percentage')
        if fill_val is None:
            fill_val = data.get('fill_level', data.get('fill'))

        if fill_val is None:
            return False, "fill_percentage is required", None

        try:
            fill_pct = float(fill_val)
        except (ValueError, TypeError):
            return False, "fill_percentage must be a numeric value", None

        if fill_pct < cls.MIN_FILL_PCT or fill_pct > cls.MAX_FILL_PCT:
            return False, f"fill_percentage must be between {cls.MIN_FILL_PCT} and {cls.MAX_FILL_PCT}", None

        parsed = {
            'action': 'reading',
            'raw_bin_id': raw_bin_id,
            'fill_percentage': round(fill_pct, 1),
            'weight_kg': None,
            'temperature_c': None,
            'battery_level': None
        }

        # 3. Validate weight (optional)
        weight_val = data.get('weight')
        if weight_val is None:
            weight_val = data.get('weight_kg')
        if weight_val is not None:
            try:
                wt = float(weight_val)
            except (ValueError, TypeError):
                return False, "weight must be a numeric value", None
            if wt < cls.MIN_WEIGHT_KG or wt > cls.MAX_WEIGHT_KG:
                return False, f"weight must be between {cls.MIN_WEIGHT_KG} and {cls.MAX_WEIGHT_KG} kg", None
            parsed['weight_kg'] = round(wt, 2)

        # 4. Validate temperature (optional)
        temp_val = data.get('temperature')
        if temp_val is None:
            temp_val = data.get('temperature_c')
        if temp_val is not None:
            try:
                temp = float(temp_val)
            except (ValueError, TypeError):
                return False, "temperature must be a numeric value", None
            if temp < cls.MIN_TEMP_C or temp > cls.MAX_TEMP_C:
                return False, f"temperature must be between {cls.MIN_TEMP_C} and {cls.MAX_TEMP_C} C", None
            parsed['temperature_c'] = round(temp, 1)

        # 5. Validate battery_level (optional)
        batt_val = data.get('battery_level')
        if batt_val is None:
            batt_val = data.get('battery')
        if batt_val is not None:
            try:
                batt = float(batt_val)
            except (ValueError, TypeError):
                return False, "battery_level must be a numeric value", None
            if batt < cls.MIN_BATTERY_PCT or batt > cls.MAX_BATTERY_PCT:
                return False, f"battery_level must be between {cls.MIN_BATTERY_PCT} and {cls.MAX_BATTERY_PCT}%", None
            parsed['battery_level'] = round(batt, 1)

        return True, None, parsed

    @classmethod
    def record_sensor_reading(cls, bin_obj, fill_percentage, weight_kg=None, temperature_c=None, battery_level=None):
        """
        Updates bin record with physical sensor telemetry, appends a BinReading
        audit record, recalculates bin status, and evaluates collection alerts.
        """
        bin_obj.fill_percentage = round(float(fill_percentage), 1)

        if weight_kg is not None:
            bin_obj.weight_kg = round(float(weight_kg), 2)
        if temperature_c is not None:
            bin_obj.temperature_c = round(float(temperature_c), 1)
        if battery_level is not None:
            bin_obj.battery_level = round(float(battery_level), 1)

        bin_obj.status = bin_obj.calculate_status()
        bin_obj.last_updated = datetime.now(timezone.utc)

        # Append to historical time-series ledger
        reading = BinReading(
            bin_id=bin_obj.id,
            fill_percentage=bin_obj.fill_percentage,
            weight_kg=bin_obj.weight_kg,
            temperature_c=bin_obj.temperature_c,
            battery_level=bin_obj.battery_level,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(reading)

        # Evaluate threshold alerts & automated collection requests
        alert_info = cls._check_collection_alerts(bin_obj)

        db.session.commit()
        return bin_obj, alert_info

    @classmethod
    def empty_bin(cls, bin_id):
        """
        Marks bin as serviced/emptied, records reading at 0.0%, and marks active
        collection requests as COMPLETED.
        """
        bin_obj = db.session.get(Bin, bin_id)
        if not bin_obj:
            return None, None

        # Resolve open collection requests for this bin
        open_requests = CollectionRequest.query.filter(
            CollectionRequest.bin_id == bin_id,
            CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED', 'COLLECTED'])
        ).all()
        for req in open_requests:
            req.status = 'COMPLETED'
            req.resolved_at = datetime.now(timezone.utc)

        bin_obj.fill_percentage = 0.0
        bin_obj.weight_kg = 0.0
        bin_obj.status = 'NORMAL'
        bin_obj.last_updated = datetime.now(timezone.utc)

        # Record historical reading
        reading = BinReading(
            bin_id=bin_obj.id,
            fill_percentage=0.0,
            weight_kg=0.0,
            temperature_c=bin_obj.temperature_c,
            battery_level=bin_obj.battery_level,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(reading)

        db.session.commit()
        return bin_obj, None

    @classmethod
    def _check_collection_alerts(cls, bin_obj):
        """
        Evaluates collection alert rules when fill level crosses 85% (HIGH) or 100% (URGENT OVERFLOW).
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

            # Check if there is an active pending, scheduled, assigned, or collected request already
            existing_request = CollectionRequest.query.filter(
                CollectionRequest.bin_id == bin_obj.id,
                CollectionRequest.status.in_(['PENDING', 'SCHEDULED', 'ASSIGNED', 'COLLECTED'])
            ).first()

            is_new = False
            if not existing_request:
                now_utc = datetime.now(timezone.utc)
                timestamp_str = now_utc.strftime('%H%M%S')
                req_code = f"CR-{bin_obj.id[-2:]}-{timestamp_str}-{now_utc.microsecond // 1000:03d}"
                col_req = CollectionRequest(
                    request_code=req_code,
                    bin_id=bin_obj.id,
                    waste_type=bin_obj.waste_type,
                    location=bin_obj.location,
                    fill_level=bin_obj.fill_percentage,
                    priority=priority,
                    status='PENDING',
                    created_at=now_utc
                )
                db.session.add(col_req)
                is_new = True
            elif is_overflow and existing_request.priority != 'URGENT':
                existing_request.priority = 'URGENT'
                existing_request.fill_level = bin_obj.fill_percentage
                is_new = True

            alert_info = {
                'triggered': True,
                'is_new': is_new,
                'alert_type': alert_type,
                'message': alert_msg,
                'priority': priority,
                'bin_id': bin_obj.id,
                'location': bin_obj.location,
                'waste_type': bin_obj.waste_type,
                'fill_level': bin_obj.fill_percentage,
                'status': 'FULL' if is_overflow else bin_obj.status
            }

        return alert_info
