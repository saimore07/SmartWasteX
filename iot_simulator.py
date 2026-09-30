#!/usr/bin/env python3
"""
==============================================================================
SmartWasteX — IoT Edge Hardware Sensor Simulator
==============================================================================
Simulates physical campus waste receptacles streaming live edge telemetry:
- Ultrasonic depth sensors (fill capacity percentage)
- Load-cell strain gauges (weight in kg)
- Ambient thermal probes (temperature in °C)
- Node lithium battery voltage monitoring

Used during hackathon judge presentations to demonstrate real-time telemetry
and automated facilities collection triggers without physical sensors.

Usage:
    python iot_simulator.py

Environment Variables:
    SMARTWASTEX_API_URL: Target URL (default: http://127.0.0.1:5000)
    IOT_UPDATE_INTERVAL: Seconds between simulation ticks (default: 4)
==============================================================================
"""

import os
import sys
import time
import json
import random
from datetime import datetime
import urllib.request
import urllib.error

# Ensure clean UTF-8 terminal printing
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
API_BASE = os.environ.get('SMARTWASTEX_API_URL', 'http://127.0.0.1:5000').rstrip('/')
UPDATE_INTERVAL = float(os.environ.get('IOT_UPDATE_INTERVAL', 4.0))

# Simulated Campus Smart Bins (mapping to existing SmartWasteX institutional bins)
SIMULATED_BINS = [
    {
        'id': 'BIN-01',
        'name': 'Main Building Recyclable',
        'waste_type': 'Dry Recyclable',
        'fill': 42.0,
        'rate_min': 3,
        'rate_max': 7
    },
    {
        'id': 'BIN-02',
        'name': 'Cafeteria Compost Hub',
        'waste_type': 'Biodegradable',
        'fill': 61.0,
        'rate_min': 4,
        'rate_max': 8
    },
    {
        'id': 'BIN-03',
        'name': 'Library Paper & Plastic',
        'waste_type': 'Dry Recyclable',
        'fill': 78.0,
        'rate_min': 3,
        'rate_max': 6
    },
    {
        'id': 'BIN-04',
        'name': 'Engineering E-Waste Depot',
        'waste_type': 'Hazardous / E-Waste',
        'fill': 94.0,
        'rate_min': 2,
        'rate_max': 5
    }
]

def print_banner():
    print("\n" + "=" * 70)
    print(" 📡 SMARTWASTEX — IOT EDGE TELEMETRY SIMULATOR")
    print("=" * 70)
    print(f" Target API       : {API_BASE}")
    print(f" Update Interval  : {UPDATE_INTERVAL}s")
    print(f" Monitored Bins   : {len(SIMULATED_BINS)} nodes ({', '.join(b['id'] for b in SIMULATED_BINS)})")
    print(f" Status Hierarchy : <70% NORMAL | 70-84% WARNING | 85-99% HIGH | 100% OVERFLOW")
    print("=" * 70)
    print(" Connecting to SmartWasteX platform...")

def send_request(endpoint, data=None):
    """Sends JSON HTTP/HTTPS request to the SmartWasteX backend."""
    url = f"{API_BASE}{endpoint}"
    headers = {
        'User-Agent': 'SmartWasteX-IoTSimulator/1.0',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    req_data = json.dumps(data).encode('utf-8') if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers)

    with urllib.request.urlopen(req, timeout=10) as response:
        resp_body = response.read().decode('utf-8')
        return json.loads(resp_body)

def sync_initial_state():
    """Initializes local bin fill levels from existing server state if available."""
    try:
        health_resp = send_request('/health')
        if health_resp.get('status') == 'ok':
            print(" [Connected] Server health check: OK.")
    except Exception as e:
        print(f" [Warning] Could not reach /health ({e}). Waiting for server...")

    try:
        bins_data = send_request('/api/bins')
        if isinstance(bins_data, list):
            db_fills = {b['id']: b['fill_percentage'] for b in bins_data}
            for sim_b in SIMULATED_BINS:
                if sim_b['id'] in db_fills:
                    sim_b['fill'] = float(db_fills[sim_b['id']])
            print(" [Synced] Initial bin states synchronized from live database.")
    except Exception as e:
        print(f" [Notice] Initial /api/bins sync skipped ({e}). Using default seed fills.")

    print("\n Streaming live sensor telemetry (Press Ctrl+C to stop)...")
    print("-" * 70)

def run_simulation_loop():
    print_banner()
    sync_initial_state()

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            now_str = datetime.now().strftime("%H:%M:%S")

            for b in SIMULATED_BINS:
                bin_id = b['id']
                bin_name = b['name']

                # Check if this bin was at overflow and needs to simulate collection reset
                if b['fill'] >= 100.0:
                    try:
                        resp = send_request('/api/iot/bin-update', {
                            'bin_id': bin_id,
                            'action': 'empty'
                        })
                        b['fill'] = 0.0
                        print(f" [{now_str}] 🚛 {bin_id} ({bin_name})")
                        print(f"          ↳ Simulated Facilities Collection Executed: Emptied to 0.0% [NORMAL]")
                        time.sleep(0.4)
                        continue
                    except Exception as err:
                        print(f" [{now_str}] ⚠️ {bin_id} -> Collection reset failed: {err}")

                # Calculate realistic randomized telemetry increment
                increment = random.randint(b['rate_min'], b['rate_max'])
                new_fill = min(100.0, round(b['fill'] + increment, 1))
                b['fill'] = new_fill

                # Determine expected visual status
                if new_fill >= 100.0:
                    status_label = "OVERFLOW 🚨"
                elif new_fill >= 85.0:
                    status_label = "HIGH ⚠️"
                elif new_fill >= 70.0:
                    status_label = "WARNING"
                else:
                    status_label = "NORMAL"

                # Send payload to backend
                try:
                    payload = {
                        'bin_id': bin_id,
                        'fill_level': new_fill
                    }
                    resp = send_request('/api/iot/bin-update', payload)

                    if resp.get('success'):
                        wt = resp.get('weight_kg', 0.0)
                        temp = resp.get('temperature_c', 0.0)
                        batt = resp.get('battery_level', 100.0)
                        server_status = resp.get('status', status_label)

                        # Output formatted telemetry row
                        alert_info = resp.get('alert')
                        alert_tag = ""
                        if alert_info and alert_info.get('triggered'):
                            alert_tag = f" -> 🚨 TICKET CREATED: {alert_info.get('priority')}"

                        print(f" [{now_str}] {bin_id} ({b['waste_type'][:12]}) -> {new_fill:5.1f}% [{server_status:<8}] "
                              f"| {wt:4.1f}kg | {temp:4.1f}°C | Batt: {batt:4.1f}%{alert_tag}")
                    else:
                        print(f" [{now_str}] {bin_id} -> Server error: {resp.get('error')}")

                except urllib.error.URLError as url_err:
                    print(f" [{now_str}] {bin_id} -> Connection error to {API_BASE}: {url_err.reason}")
                except Exception as ex:
                    print(f" [{now_str}] {bin_id} -> Telemetry transmission failed: {ex}")

                # Stagger sensors slightly for natural edge arrival
                time.sleep(0.5)

            # Sleep until next simulation cycle
            time.sleep(max(1.0, UPDATE_INTERVAL - 2.0))

    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print(" [Shutdown] IoT Sensor Telemetry Simulator halted safely by user.")
        print(" SmartWasteX server remains live and unaffected.")
        print("=" * 70 + "\n")

if __name__ == '__main__':
    run_simulation_loop()
