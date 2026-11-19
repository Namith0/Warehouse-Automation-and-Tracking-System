# Autonomous Warehouse Automation & Tracking System (prj_424)

An end-to-end intelligent warehouse logistics and inventory management system running on **Raspberry Pi**, integrating **RC522 RFID identification**, **automated weigh-line quality checks**, **autonomous mobile robots (AMRs)**, and a real-time web control dashboard for zone auditing, reslotting, and dispatch workflows.

## Key Features
- **RFID Item Identification:** Real-time tag scanning and logging using RC522 RFID modules.
- **Automated Weigh-Line Conveyor:** Load-cell integrated conveyor belt that verifies package weights in transit and flags anomalies before storage[cite: 10].
- **Autonomous Warehouse Robotics:** Automated transport units handling bin movement, dynamic reslotting, and periodic zone inventory audits[cite: 10].
- **Interactive Web Dashboard:** Real-time monitoring and control interface built with Python and HTML/CSS/JS for tracking inventory, zone status, and dispatch workflows[cite: 10].

## Tech Stack & Hardware
- **Compute & Hardware:** Raspberry Pi, RC522 RFID Readers, Load Cells (HX711), Conveyor & AMR Drive Motors[cite: 10]
- **Backend & Database:** Python (Flask), SQLite[cite: 7, 10]
- **Frontend:** HTML5, CSS3, JavaScript[cite: 10]
- **Concepts:** Embedded Systems, IoT Telemetry, Warehouse Management Systems (WMS), Autonomous Logistics[cite: 10]

## Repository Structure
```text
├── app.py                              # Main Raspberry Pi Flask server, hardware logic, and API routes
├── templates/
│   └── index.html                      # Real-time warehouse monitoring and control web dashboard
├── docs/
│   └── PRJ424_Research_Paper.docx      # Full 8-page system architecture and methodology paper
├── requirements.txt                    # Python dependencies
├── .gitignore                          # Excludes __pycache__ and local environment files
└── README.md                           # Project documentation
```

## Research & Documentation
- **System Research Paper:** [PRJ424_Research_Paper.docx](docs/PRJ424_Research_Paper.docx)[cite: 9]

## Getting Started
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Namith0/Warehouse-Automation-and-Tracking-System.git](https://github.com/Namith0/Warehouse-Automation-and-Tracking-System.git)
   cd Warehouse-Automation-and-Tracking-System
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application:**
   ```bash
   python app.py
   ```
   Open your browser and go to `http://localhost:5000` (or `http://<raspberry-pi-ip>:5000`).
