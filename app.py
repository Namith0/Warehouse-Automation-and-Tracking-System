from flask import Flask, render_template, jsonify, request, make_response
import sqlite3
import threading
from time import sleep, time
from datetime import datetime, timedelta, timezone

try:
    from gpiozero import Button, LED, Buzzer
    from mfrc522 import SimpleMFRC522
    HW_AVAILABLE = True
except Exception as _hw_err:
    print(f"[INFO] Running in GPIO/SPI simulation mode ({_hw_err})")
    HW_AVAILABLE = False

    class _DummyPin:
        def __init__(self, pin=None, **kw):
            self.pin = pin
            self.when_held = None
            self.when_released = None
        def blink(self, *a, **kw): pass
        def beep(self, *a, **kw): pass

    Button = LED = Buzzer = _DummyPin

    class SimpleMFRC522:
        def read_no_block(self):
            return None, None

app = Flask(__name__)

DB_PATH = 'warehouse.db'
IST = timezone(timedelta(hours=5, minutes=30))
ZONES = ["Zone A", "Zone B", "Zone C", "Zone D"]

STATUS_IN_STOCK = "IN_STOCK"
STATUS_DISPATCHED = "DISPATCHED"
STATUS_INSPECTION = "INSPECTION"
STATUS_QUARANTINED = "QUARANTINED"
ALL_STATUSES = [STATUS_IN_STOCK, STATUS_DISPATCHED, STATUS_INSPECTION, STATUS_QUARANTINED]

state_lock = threading.RLock()


def get_conn():
    return sqlite3.connect(DB_PATH, timeout=10)


def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            rfid_uid TEXT PRIMARY KEY,
            name TEXT,
            home_zone TEXT,
            current_zone TEXT,
            status TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_uid TEXT,
            action_type TEXT,
            zone TEXT,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


init_db()

b1 = Button(5, pull_up=True, bounce_time=0.1, hold_time=1.5)
b2 = Button(6, pull_up=True, bounce_time=0.1, hold_time=1.5)
b3 = Button(12, pull_up=True, bounce_time=0.1, hold_time=1.5)

green_led = LED(17)
yellow_led = LED(22)
red_led = LED(27)
buzzer = Buzzer(24)

reader = SimpleMFRC522()

current_zone = ZONES[0]
active_mode = "RECEIVE"
latest_alert = "System ready. Tap your tags in RECEIVE mode."
alert_type = "info"
system_running = True

state_seq = 1
scan_seq = 0
last_hw_event = {
    "seq": 1,
    "scan_seq": 0,
    "type": "INIT",
    "mode": "RECEIVE",
    "zone": "Zone A",
    "rfid_uid": None,
    "result": None,
    "ts": time()
}


def record_hw_event(ev_type, rfid_uid=None, result=None):
    global state_seq, scan_seq, last_hw_event
    with state_lock:
        state_seq += 1
        if ev_type == "SCAN":
            scan_seq += 1
        last_hw_event = {
            "seq": state_seq,
            "scan_seq": scan_seq,
            "type": ev_type,
            "mode": active_mode,
            "zone": current_zone,
            "rfid_uid": rfid_uid,
            "result": result,
            "ts": time()
        }


def set_alert(message, kind):
    global latest_alert, alert_type
    with state_lock:
        latest_alert = message
        alert_type = kind


def signal_ok():
    green_led.blink(0.1, 0.1, 1, background=True)
    buzzer.beep(0.1, 0.1, 1, background=True)


def signal_warning():
    yellow_led.blink(0.2, 0.2, 2, background=True)
    buzzer.beep(0.1, 0.1, 2, background=True)


def signal_error():
    red_led.blink(0.2, 0.2, 3, background=True)
    buzzer.beep(0.2, 0.2, 2, background=True)


MODE_SIGNALS = {
    "AUDIT":     lambda: (green_led.blink(0.15, 0.15, 2, background=True),
                          buzzer.beep(0.1, 0.1, 2, background=True)),
    "RECEIVE":   lambda: (green_led.blink(0.6, 0.1, 1, background=True),
                          buzzer.beep(0.1, 0.1, 1, background=True)),
    "DISPATCH":  lambda: (green_led.blink(0.08, 0.08, 3, background=True),
                          buzzer.beep(0.05, 0.05, 3, background=True)),
    "RETURN":    lambda: (yellow_led.blink(0.15, 0.15, 2, background=True),
                          buzzer.beep(0.1, 0.1, 2, background=True)),
    "DEFECTIVE": lambda: (red_led.blink(0.15, 0.15, 2, background=True),
                          buzzer.beep(0.6, 0.1, 1, background=True)),
}

MODE_LABELS = {
    "AUDIT": "Inventory Audit",
    "RECEIVE": "Receiving",
    "DISPATCH": "Dispatch",
    "RETURN": "Returns / Inspection",
    "DEFECTIVE": "Defective / Quarantine",
}


def process_scan(rfid_uid):
    with state_lock:
        zone = current_zone
        mode = active_mode
        short_id = rfid_uid[-4:]

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT home_zone, status FROM items WHERE rfid_uid = ?", (rfid_uid,))
        row = cursor.fetchone()

        if not row:
            cursor.execute("SELECT COUNT(*) FROM items")
            count = cursor.fetchone()[0]
            home_zone = ZONES[min(count // 3, len(ZONES) - 1)]
            item_name = f"Asset-{short_id}"
            cursor.execute(
                "INSERT INTO items (rfid_uid, name, home_zone, current_zone, status) VALUES (?, ?, ?, ?, ?)",
                (rfid_uid, item_name, home_zone, zone, STATUS_IN_STOCK))
            status = STATUS_IN_STOCK
        else:
            home_zone, status = row

        result = "NORMAL"

        if mode == "AUDIT":
            if status == STATUS_DISPATCHED:
                result = "UNEXPECTED"
                signal_error()
                set_alert(f"AUDIT ALERT! Asset {short_id} is marked DISPATCHED but was found in {zone}!", "danger")
            elif zone == home_zone:
                result = "MATCH"
                green_led.blink(0.1, 0.1, 2, background=True)
                buzzer.beep(0.1, 0.1, 1, background=True)
                set_alert(f"MATCH: Asset {short_id} verified correctly in {zone}.", "success")
            else:
                result = "MISMATCH"
                signal_error()
                set_alert(f"MISMATCH ALERT! Asset {short_id} belongs to {home_zone}, but scanned in {zone}!", "danger")
            cursor.execute("UPDATE items SET last_updated = CURRENT_TIMESTAMP WHERE rfid_uid = ?", (rfid_uid,))

        elif mode == "RECEIVE":
            result = "RECEIVED"
            cursor.execute(
                "UPDATE items SET current_zone = ?, status = ?, last_updated = CURRENT_TIMESTAMP WHERE rfid_uid = ?",
                (zone, STATUS_IN_STOCK, rfid_uid))
            signal_ok()
            set_alert(f"RECEIVED: Asset {short_id} stocked in {zone}.", "success")

        elif mode == "DISPATCH":
            if status in (STATUS_DISPATCHED, STATUS_QUARANTINED):
                result = "BLOCKED"
                signal_error()
                set_alert(f"DISPATCH BLOCKED! Asset {short_id} is already {status}.", "danger")
            else:
                result = "DISPATCHED"
                cursor.execute(
                    "UPDATE items SET current_zone = ?, status = ?, last_updated = CURRENT_TIMESTAMP WHERE rfid_uid = ?",
                    (zone, STATUS_DISPATCHED, rfid_uid))
                signal_ok()
                set_alert(f"DISPATCHED: Asset {short_id} shipped out from {zone}.", "success")

        elif mode == "RETURN":
            result = "INSPECTION"
            cursor.execute(
                "UPDATE items SET current_zone = ?, status = ?, last_updated = CURRENT_TIMESTAMP WHERE rfid_uid = ?",
                (zone, STATUS_INSPECTION, rfid_uid))
            signal_warning()
            set_alert(f"RETURN: Asset {short_id} received back in {zone} and held for inspection.", "warning")

        elif mode == "DEFECTIVE":
            result = "QUARANTINED"
            cursor.execute(
                "UPDATE items SET current_zone = ?, status = ?, last_updated = CURRENT_TIMESTAMP WHERE rfid_uid = ?",
                (zone, STATUS_QUARANTINED, rfid_uid))
            red_led.blink(0.3, 0.2, 3, background=True)
            buzzer.beep(1.0, 0.1, 1, background=True)
            set_alert(f"QUARANTINED: Asset {short_id} flagged defective in {zone}.", "danger")

        cursor.execute(
            "INSERT INTO stock_movements (rfid_uid, action_type, zone, result) VALUES (?, ?, ?, ?)",
            (rfid_uid, mode, zone, result))
        conn.commit()
        conn.close()

        record_hw_event("SCAN", rfid_uid=rfid_uid, result=result)
        print(f"[SCAN RESULT] {rfid_uid} | {mode} | {zone} | {result}")


def set_zone(target_zone=None):
    global current_zone
    with state_lock:
        if target_zone and target_zone in ZONES:
            current_zone = target_zone
        else:
            idx = ZONES.index(current_zone) if current_zone in ZONES else -1
            current_zone = ZONES[(idx + 1) % len(ZONES)]
        zone = current_zone
    print(f"[ZONE CHANGED] Active Zone: {zone}")
    yellow_led.blink(0.1, 0.1, 3, background=True)
    buzzer.beep(0.1, 0.1, 1, background=True)
    set_alert(f"Switched Active Zone to {zone}", "warning")
    record_hw_event("ZONE")


def set_mode(mode):
    global active_mode
    if mode not in MODE_LABELS:
        return
    with state_lock:
        active_mode = mode
    print(f"[MODE SET] {mode}")
    MODE_SIGNALS[mode]()
    set_alert(f"Hardware Mode changed to: {MODE_LABELS[mode]} ({mode})", "info")
    record_hw_event("MODE")


def bind_button(button, short_action, hold_action):
    state = {"held": False}

    def on_held():
        state["held"] = True
        hold_action()

    def on_released():
        if state["held"]:
            state["held"] = False
        else:
            short_action()

    button.when_held = on_held
    button.when_released = on_released


bind_button(b1, lambda: set_mode("AUDIT"),    set_zone)
bind_button(b2, lambda: set_mode("RECEIVE"),  lambda: set_mode("RETURN"))
bind_button(b3, lambda: set_mode("DISPATCH"), lambda: set_mode("DEFECTIVE"))


def hardware_loop():
    print("[HARDWARE] RFID and Button loop active...")
    while system_running:
        try:
            tag_id, text = reader.read_no_block()
            if tag_id:
                uid_str = str(tag_id).strip()
                print(f"[RFID SCAN] ID: {uid_str} | Mode: {active_mode} | Zone: {current_zone}")
                process_scan(uid_str)
                sleep(1.5)
        except Exception as e:
            print(f"[RFID ERROR] {e}")
        sleep(0.2)


hw_thread = threading.Thread(target=hardware_loop, daemon=True)
hw_thread.start()


@app.template_filter('ist')
def to_ist(value):
    if not value:
        return "-"
    try:
        dt = datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return value
    return dt.astimezone(IST).strftime("%d %b, %I:%M:%S %p")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/state', methods=['GET', 'OPTIONS'])
def api_state():
    if request.method == 'OPTIONS':
        return make_response('', 204)
    with state_lock:
        return jsonify({
            "zone": current_zone,
            "mode": active_mode,
            "alert": latest_alert,
            "alert_type": alert_type,
            "last_event": dict(last_hw_event)
        })


@app.route('/api/command', methods=['POST', 'OPTIONS'])
def api_command():
    if request.method == 'OPTIONS':
        return make_response('', 204)
    data = request.get_json(silent=True) or {}
    cmd = data.get("command", "")
    if cmd == "set_mode":
        set_mode(data.get("mode", "RECEIVE").upper())
    elif cmd == "set_zone":
        set_zone(data.get("zone"))
    elif cmd == "scan":
        uid = str(data.get("rfid_uid", "")).strip()
        if uid:
            process_scan(uid)
    return jsonify({"ok": True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
