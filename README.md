# SmartWasteX
### AI-Powered Campus Waste Segregation & E-Waste Tracking Platform
**Track 4: Sustainable Cities & Communities (UN SDG 11) — Campus & City Waste Segregation & E-Waste Tracker**

---

## 📌 Executive Summary
**SmartWasteX** is an institutional circular economy platform developed for university campuses and municipal complexes. It unifies four critical pillars of waste management into a single, cohesive web application:
1. **AI-Powered Waste Segregation Scanner**: Uses OpenCV computer vision and semantic feature extraction to classify waste items into Biodegradable, Dry Recyclable, and Hazardous/E-Waste streams, guiding users to nearest smart bins.
2. **Institutional E-Waste Lifecycle Tracking**: Issues tamper-evident **Digital Passports** with verifiable QR codes for university electronics (laptops, phones, PCBs), tracking custody from registration through certified R2 recycling.
3. **Simulated Smart-Bin Telemetry Network**: Simulates ultrasonic fill depth, weight load-cells, and temperature probes across virtual campus bins with automatic overflow warnings and high-priority collection ticketing.
4. **Community Incentives (Green Credits)**: Database-backed points ledger rewarding students and faculty for verified disposal actions, linked to real-time campus leaderboards and SDG 11 carbon abatement analytics.

> **Note on IoT Telemetry:** Smart bin sensor data in this MVP is simulated via software (`services/iot_simulator.py`) to allow reproducible demonstrations without physical microcontrollers.

---

## 🎯 Alignment with UN SDG 11
- **SDG Target 11.6**: *"By 2030, reduce the adverse per capita environmental impact of cities and university institutions, including by paying special attention to municipal solid waste management and certified hazardous/e-waste circularity."*
- **Measurable Campus Impact**:
  - Eliminates mixed-waste contamination in campus organic composting.
  - Guarantees 100% chain-of-custody tracking for retired university IT equipment.
  - Dynamically prevents receptacle overflow using predictive collection dispatch.

---

## 🏛️ System Architecture

```text
                               +-----------------------------------+
                               |     Campus Users / Admin Staff    |
                               +-----------------+-----------------+
                                                 |
                                                 v
                               +-----------------+-----------------+
                               |    Flask Web Application (WSGI)   |
                               | (Session Auth, RBAC, Jinja, CSS)  |
                               +-----------------+-----------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   |                             |                             |
                   v                             v                             v
+------------------+---------+ +-----------------+---------+ +-----------------+---------+
|     routes/auth.py         | |     routes/user.py        | |     routes/admin.py       |
|     routes/waste.py        | |     routes/bins.py        | |     routes/ewaste.py      |
+------------------+---------+ +-----------------+---------+ +-----------------+---------+
                   |                             |                             |
                   +-----------------------------+-----------------------------+
                                                 |
                                                 v
                                   Services Business Logic
             +-----------------------------------+-----------------------------------+
             |                                   |                                   |
             v                                   v                                   v
+------------+------------+     +----------------+------------+     +----------------+------------+
|      AI Classifier      |     |        IoT Simulator        |     |      QR Code Service       |
|  (services/classifier)  |     |  (services/iot_simulator)   |     |  (services/qr_service)     |
|   OpenCV Feature /      |     |   Sensor telemetry, load,   |     |   Generates scannable      |
|   Color Space & Edges   |     |   fill level & alerts       |     |   asset passport PNGs      |
+------------+------------+     +----------------+------------+     +----------------+------------+
             |                                   |                                   |
             |      +----------------------------+----------------------------+      |
             |      |                                                         |      |
             v      v                                                         v      v
+------------+------+-----+                                             +-----+------+------------+
|  Recommendation Engine  |                                             |    Impact Analytics    |
| (services/recommendation|                                             | (services/impact_serv) |
| Disposal steps & bins   |                                             | SDG 11 metrics & charts|
+------------+------+-----+                                             +-----+------+------------+
             |      |                                                         |      |
             +------+----------------------------+----------------------------+------+
                                                 |
                                                 v
                               +-----------------+-----------------+
                               |     SQLite Database Storage       |
                               |    (SQLAlchemy ORM Data Models)   |
                               +-----------------+-----------------+
                                                 |
                      +--------------------------+--------------------------+
                      |                                                     |
                      v                                                     v
       +--------------+--------------+                       +--------------+--------------+
       |   User Dashboard & Views    |                       |  Admin Command Center & GIS |
       | - Green Credits Balance     |                       | - Live Sensor Matrix        |
       | - Scan Camera & AI Result   |                       | - IoT Simulation Controls   |
       | - Activity History Ledger   |                       | - Collection Ticket Queue   |
       | - Campus Leaderboard        |                       | - E-Waste Asset Lifecycle   |
       | - Environmental Equivalents |                       | - Leaflet OpenStreetMap GIS |
       +-----------------------------+                       +-----------------------------+
```

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
|---|---|
| **Backend** | Python 3.12, Flask 3.1, Werkzeug (PBKDF2 Password Hashing), Jinja2 |
| **Database** | SQLite, SQLAlchemy 2.0 (Flask-SQLAlchemy 3.1) |
| **Frontend** | HTML5, Vanilla CSS3 (Custom Design System), JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Visual Analytics** | Chart.js 4.4 (Doughnut, Horizontal Bar, Stacked Area, Bar Trends) |
| **Geographic GIS** | Leaflet 1.9 + OpenStreetMap |
| **Computer Vision (AI)**| OpenCV 5.0 (Canny edge detection, HSV color space distribution, perceptual heuristics) |
| **Asset Identity** | Python `qrcode` library, Pillow (PIL) |
| **Test Automation** | Pytest 9.1 |

---

## 🗄️ Database Schema & Entities

The SQLite database (`instance/smartwastex.db`) is structured into 8 relational tables:
1. **`users`**: User identities, hashed credentials, roles (`user` or `admin`), total green credits, recycled items count, cumulative diverted kg.
2. **`waste_scans`**: Historical camera captures, detected item labels, stream categories, confidence scores, recommendations, assigned bins.
3. **`green_credit_transactions`**: Auditable points ledger recording credit grants, timestamped descriptions, and reference identifiers.
4. **`bins`**: Virtual smart receptacles with telemetry fields (`fill_percentage`, `weight_kg`, `temperature_c`, `battery_level`, `status`, `lat`, `lng`).
5. **`bin_readings`**: Time-series log of sensor updates for historical capacity analysis.
6. **`collection_requests`**: Automated dispatch tickets (`PENDING`, `ASSIGNED`, `COLLECTED`, `COMPLETED`) with dynamic priorities (`MEDIUM`, `HIGH`, `URGENT`).
7. **`ewaste_assets`**: Institutional hardware assets with unique IDs (`EW-2026-XXXX`), serial numbers, location, recycler, and QR code paths.
8. **`ewaste_lifecycle`**: Immutable chain-of-custody audit log tracking status transitions and inspector signatures.

---

## 🚀 Quickstart Installation & Execution

### Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Pip package manager

### 1. Clone or Open Project Directory
```bash
cd SmartWasteX
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Automated Tests
```bash
pytest -v
```
*(Runs 16 unit and integration test suites verifying auth, AI classification, smart bins, e-waste, and role-based access control).*

### 4. Run the 26-Step End-To-End Verification
```bash
python verify_e2e_scenario.py
```

### 5. Launch the Web Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Demo Accounts & Evaluation Credentials

For frictionless evaluation, 1-click credential prefill buttons are provided directly on the `/login` screen:

| Role | Username / Email | Password | Primary Landing Page |
|---|---|---|---|
| **Demo User** | `user1@smartwastex.in` | `user1@123` | `/user/dashboard` |
| **Demo Admin** | `admin@smartwastex.in` | `admin@123` | `/admin/dashboard` |

> *Passwords are securely hashed using Werkzeug PBKDF2:SHA256 with random salts and are never stored in plaintext.*

---

## 🧠 Core Feature Deep Dives

### 1. AI Waste Classifier (`services/classifier.py`)
- **Pipeline Architecture**:
  1. Inspects image resolution and loads image tensor using OpenCV.
  2. Analyzes HSV color distribution (e.g. green/brown tones indicate organic material; cyan/blue indicates transparent plastics; dark high-contrast indicates electronics).
  3. Computes edge density using Canny algorithms (complex electronic circuitry features high gradient densities >0.12).
  4. Matches against semantic item vocabularies with realistic confidence metrics (88% - 97%).
  5. Fallback heuristic cleanly surfaces explanation and routes to correct bin.
- **Supported Streams**:
  - **Biodegradable** (+5 Credits): Banana peel, apple core, organic food waste, garden leaves.
  - **Dry Recyclable** (+10 Credits): PET plastic bottles, aluminum cans, newspapers, cardboards.
  - **Hazardous / E-Waste** (+25 Credits): Lithium-ion batteries, smartphones, circuit boards, laptops.

### 2. Software-Simulated Smart Bin Telemetry (`services/iot_simulator.py`)
- Tracks 4 virtual campus receptacles:
  - `BIN-01`: Main Building (Dry Recyclable)
  - `BIN-02`: Cafeteria (Biodegradable)
  - `BIN-03`: Library (Dry Recyclable)
  - `BIN-04`: Engineering Block (Hazardous / E-Waste)
- **Status Threshold Rules**:
  - `fill < 70%`: **NORMAL**
  - `70% <= fill < 85%`: **WARNING**
  - `85% <= fill < 100%`: **HIGH** (Automated "Collection Recommended" notification)
  - `fill >= 100%`: **OVERFLOW** (Triggers 🚨 **URGENT OVERFLOW ALERT** and generates a high-priority collection ticket in the database).
- **Controls**: Interactive buttons (`[+10%]`, `[-10%]`, `[Random Reading]`, `[Empty Bin]`, `[Push to 100%]`).
- **Predictive Estimation**: Formula: `hours_remaining = (100 - fill_percentage) / fill_rate_per_hour`.

### 3. E-Waste Digital Passport & Public QR Verification (`routes/ewaste.py`)
- Every institutional asset receives a unique sequential identifier (e.g., `EW-2026-0001`) and a scannable QR code linking to:
  ```
  http://127.0.0.1:5000/ewaste/<asset_id>
  ```
- **Lifecycle Progression**:
  `REGISTERED` ➔ `DECOMMISSIONED` ➔ `COLLECTION_REQUESTED` ➔ `COLLECTED` ➔ `SENT_TO_RECYCLER` ➔ `RECYCLED`
- **Public Passport Page**: Accessible without authentication, displaying an interactive circular progress stepper and custody ledger.

### 4. Green Credit Rewards & Leaderboard (`routes/user.py`)
- Every verified disposal action credits the user's account in real-time.
- Transparent transaction ledger displaying date, action type, points earned, and audit reference.
- Live campus leaderboard with rank medals (🥇, 🥈, 🥉) and personalized user highlighting.

---

## ⏱️ Recommended 3-Minute Demo Sequence for Judges

1. **Step 1 (0:00 - 0:45) — User Onboarding & AI Scan**:
   - Go to `http://127.0.0.1:5000/login`, click **Demo Campus User**, click **Access Platform**.
   - Review the User Dashboard (Green Credits, Recycled Items, Diverted Mass).
   - Click **Scan New Waste**. Click the **Lithium Battery** demo sample.
   - Review AI classification: item detected as *Lithium Battery*, category *Hazardous / E-Waste*, confidence *96%*, and nearest bin *BIN-04*.
   - Click **Dispose Responsibly & Claim +25 Credits**. Verify instant balance update.
2. **Step 2 (0:45 - 1:45) — Admin Command Center & IoT Simulation**:
   - Log out, click **Demo Admin / Officer**, log in.
   - Show the 6 KPI cards, stream distribution doughnut chart, and waste trend graph.
   - Navigate to **Smart Bins** (`/admin/bins`).
   - Select **BIN-04** (Engineering Block). Click **Push to 100%** (or `+10%`).
   - Observe the live capacity bar turn red, status change to **OVERFLOW**, and the critical alert trigger.
   - Navigate to **Collections** (`/admin/collections`). See the automated high-priority ticket created. Click **Complete & Empty** to resolve it.
3. **Step 3 (1:45 - 3:00) — E-Waste Digital Passport & GIS Analytics**:
   - Navigate to **E-Waste** (`/admin/ewaste`). Click **Register New Asset** (e.g. Dell Monitor, CS Lab).
   - Inspect the generated asset and its QR code. Advance lifecycle stage to `COLLECTED` and `RECYCLED`.
   - Click the public passport button to view the read-only public certificate view.
   - Navigate to **Analytics** (`/admin/analytics`). Demonstrate the interactive Leaflet campus GIS map with color-coded bin markers.

---

## 🔮 Future Scope
- Integration with edge microcontrollers (ESP32 / Raspberry Pi) using MQTT/LoRaWAN telemetry protocols.
- Fine-tuned MobileNetV3 deep vision model trained directly on the institutional TACO / TrashNet datasets.
- Single Sign-On (SSO) integration with university campus directory services (SAML 2.0 / OAuth2).
- Automated municipal dispatch API webhooks for smart city municipal hauling partners.

---

## 👥 Contributors & Hackathon Credits
- **Team**: SmartWasteX Core Engineering
- **Track**: Track 4 — Sustainable Cities & Communities (SDG 11)
- **License**: MIT Open Source License
