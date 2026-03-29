import threading
import time

import serial

try:
    from .config import BAUD_RATE, CAMERA_INDEX, SERIAL_PORT
    from .plate_recognition import NumberPlateRecognizer
    from .storage import auto_book_if_available, dashboard_data, release_booking_by_plate
except ImportError:
    from config import BAUD_RATE, CAMERA_INDEX, SERIAL_PORT
    from plate_recognition import NumberPlateRecognizer
    from storage import auto_book_if_available, dashboard_data, release_booking_by_plate


class ArduinoBridge:
    def __init__(self, serial_port=SERIAL_PORT, baud_rate=BAUD_RATE, camera_index=CAMERA_INDEX):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.camera_index = camera_index
        self.serial_conn = None
        self.running = False
        self.last_event = "Bridge not started."
        self.last_synced_state_version = None

    def connect(self):
        self.serial_conn = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
        time.sleep(2)
        self.last_event = f"Connected to Arduino on {self.serial_port}"

    def send_command(self, command):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write((command + "\n").encode("utf-8"))
            self.last_event = f"Sent: {command}"

    def send_status(self):
        data = dashboard_data()
        available = data["available"]
        self.send_command(f"STATUS:{available}")
        self.last_synced_state_version = data["state_version"]

    def watch_state_loop(self):
        while self.running:
            try:
                data = dashboard_data()
                if data["state_version"] != self.last_synced_state_version:
                    self.send_status()
                time.sleep(1)
            except Exception as exc:
                self.last_event = f"State sync error: {exc}"
                time.sleep(1)

    def handle_vehicle_at_gate(self):
        recognizer = NumberPlateRecognizer(camera_index=self.camera_index)
        plate = recognizer.recognize_plate()
        capture_path = recognizer.last_capture_path
        print(f"[Gate] Captured image: {capture_path or 'capture failed'}")
        print(f"[Gate] Detected plate: {plate or 'No plate detected'}")
        if not plate:
            print("[Gate] Final action: DENY")
            self.send_command("DENY")
            self.last_event = "No number plate detected. Access denied."
            return

        status, slot = auto_book_if_available(plate)
        if status in ("existing", "new"):
            print(f"[Gate] Final action: OPEN:{slot}")
            self.send_command(f"OPEN:{slot}")
            self.send_status()
            self.last_event = f"Plate {plate} accepted. Slot {slot}."
        else:
            print("[Gate] Final action: FULL")
            self.send_command("FULL")
            self.send_status()
            self.last_event = f"Plate {plate} detected but parking is full."

    def handle_vehicle_exit(self):
        recognizer = NumberPlateRecognizer(camera_index=self.camera_index)
        plate = recognizer.recognize_plate()
        capture_path = recognizer.last_capture_path
        print(f"[Exit] Captured image: {capture_path or 'capture failed'}")
        print(f"[Exit] Detected plate: {plate or 'No plate detected'}")

        if not plate:
            print("[Exit] Final action: NO_PLATE")
            self.last_event = "Exit detected but no number plate was recognized."
            return

        released, slot = release_booking_by_plate(plate)
        if released:
            self.send_command(f"OPEN:{slot}")
            self.send_status()
            print(f"[Exit] Final action: RELEASE:{slot}")
            self.last_event = f"Plate {plate} exited. Freed slot {slot}."
        else:
            self.send_status()
            print("[Exit] Final action: NOT_FOUND")
            self.last_event = f"Plate {plate} exit detected, but no active slot was found."

    def listen_loop(self):
        self.running = True
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                    if line == "VEHICLE_AT_GATE":
                        self.handle_vehicle_at_gate()
                    elif line == "VEHICLE_EXIT":
                        self.handle_vehicle_exit()
                    elif line:
                        self.last_event = f"Arduino: {line}"
                time.sleep(0.1)
            except Exception as exc:
                self.last_event = f"Serial error: {exc}"
                time.sleep(1)

    def start(self):
        self.connect()
        self.running = True
        self.send_status()
        listener_thread = threading.Thread(target=self.listen_loop, daemon=True)
        sync_thread = threading.Thread(target=self.watch_state_loop, daemon=True)
        listener_thread.start()
        sync_thread.start()
        return listener_thread


bridge = ArduinoBridge()
