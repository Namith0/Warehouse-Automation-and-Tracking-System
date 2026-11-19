# Warehouse-Automation-and-Tracking-System
Automated warehouse inventory tracking and logistics system using RC522 RFID, weigh-line conveyors, and autonomous robots

An end-to-end intelligent warehouse logistics and inventory management system running on **Raspberry Pi**, integrating **RFID identification**, **automated weigh-line quality checks**, **autonomous mobile robots (AMRs)**, and a real-time web control dashboard for zone auditing, reslotting, and dispatch workflows.

## Key Features
- **RFID Item Identification:** Real-time tag scanning and logging using RC522 RFID modules.
- **Automated Weigh-Line Conveyor:** Load-cell integrated conveyor belt that verifies package weights in transit and flags anomalies before storage.
- **Autonomous Warehouse Robotics:** Automated transport units handling bin movement, dynamic reslotting, and periodic zone inventory audits.
- **Interactive Web Dashboard:** Real-time monitoring and control interface built with Python and HTML/CSS/JS for tracking inventory, zone status, and dispatch workflows.

## Tech Stack & Hardware
- **Compute & Hardware:** Raspberry Pi, RC522 RFID Readers, Load Cells (HX711), Conveyor & AMR Drive Motors
- **Backend & Frontend:** Python (Flask), HTML5, CSS3, JavaScript
- **Concepts:** Embedded Systems, IoT Telemetry, Warehouse Management Systems (WMS), Autonomous Logistics

## Repository Structure
```text
├── app.py                 # Main Raspberry Pi backend server, hardware/simulation logic, and API routes
├── templates/
│   └── index.html         # Real-time warehouse monitoring and control web dashboard
├── requirements.txt       # Python dependencies
├── .gitignore             # Excludes __pycache__ and local environment files
└── README.md              # Project documentation
