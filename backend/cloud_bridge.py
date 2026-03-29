import json
import threading
import time
import urllib.error
import urllib.request

import serial

try:
    from .config import BAUD_RATE, BRIDGE_API_KEY, CAMERA_INDEX, CLOUD_API_BASE_URL, SERIAL_PORT
    from .plate_recognition import NumberPlateRecognizer
except ImportError:
    from config import BAUD_RATE, BRIDGE_API_KEY, CAMERA_INDEX, CLOUD_API_BASE_URL, SERIAL_PORT
    from plate_recognition import NumberPlateRecognizer


class CloudArduinoBridge:
    def __init__(self, cloud_api_base_url=CLOUD_API_BASE_URL, serial_port=SERIAL_PORT, baud_rate=BAUD_RATE, camera_index=CAMERA_INDEX):
        self.cloud_api_base_url = cloud_api_base_url.rstrip("/")
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.camera_index = camera_index
        self.serial_conn = None
        self.running = False
        self.last_event = "Cloud bridge not started."
        self.last_synced_state_version = None

    def connect(self):
        if not self.cloud_api_base_url:
            raise RuntimeError("CLOUD_API_BASE_URL is not configured.")
        self.serial_conn = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
        time.sleep(2)
        self.last_event = f"Connected to Arduino on {self.serial_port}"

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if BRIDGE_API_KEY:
            headers["X-Bridge-Key"] = BRIDGE_API_KEY
        return headers

    def send_command(self, command):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write((command + "\n").encode("utf-8"))
            self.last_event = f"Sent to Arduino: {command}"

    def _request_json(self, path, payload=None):
        data = None
        method = "GET"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            method = "POST"

        request = urllib.request.Request(
            f"{self.cloud_api_base_url}{path}",
            data=data,
            headers=self._headers(),
            method=method,
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def send_status(self):
        data = self._request_json("/state")
        self.send_command(f"STATUS:{data['available']}")
        self.last_synced_state_version = data["state_version"]

    def watch_state_loop(self):
        while self.running:
            try:
                data = self._request_json("/state")
                if data["state_version"] != self.last_synced_state_version:
                    self.send_command(f"STATUS:{data['available']}")
                    self.last_synced_state_version = data["state_version"]
                    self.last_event = f"Cloud sync updated. Available slots: {data['available']}"
                time.sleep(1)
            except Exception as exc:
                self.last_event = f"Cloud sync error: {exc}"
                time.sleep(2)

    def _send_gate_request(self, path, plate):
        return self._request_json(path, {"plate_number": plate})

    def _process_gate_response(self, prefix, response):
        action = response.get("action")
        slot = response.get("slot")
        plate = response.get("plate_number")

        if action == "OPEN" and slot:
            self.send_command(f"OPEN:{slot}")
            self.send_status()
            self.last_event = f"{prefix}: Plate {plate} accepted for slot {slot}."
        elif action in {"FULL", "DENY"}:
            self.send_command(action)
            self.send_status()
            self.last_event = f"{prefix}: {response.get('message', action)}"
        elif action == "NO_PLATE":
            self.last_event = f"{prefix}: No number plate detected."
        else:
            self.last_event = f"{prefix}: {response.get('message', 'Unknown cloud response.')}"

    def handle_vehicle_at_gate(self):
        recognizer = NumberPlateRecognizer(camera_index=self.camera_index)
        plate = recognizer.recognize_plate()
        if not plate:
            self.send_command("DENY")
            self.last_event = "Gate: No number plate detected."
            return

        response = self._send_gate_request("/api/gate/entry", plate)
        self._process_gate_response("Gate", response)

    def handle_vehicle_exit(self):
        recognizer = NumberPlateRecognizer(camera_index=self.camera_index)
        plate = recognizer.recognize_plate()
        if not plate:
            self.last_event = "Exit: No number plate detected."
            return

        response = self._send_gate_request("/api/gate/exit", plate)
        self._process_gate_response("Exit", response)

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
            except urllib.error.HTTPError as exc:
                self.last_event = f"Cloud API error: {exc.code}"
                time.sleep(2)
            except Exception as exc:
                self.last_event = f"Serial error: {exc}"
                time.sleep(2)

    def start(self):
        self.connect()
        self.running = True
        self.send_status()
        listener_thread = threading.Thread(target=self.listen_loop, daemon=True)
        sync_thread = threading.Thread(target=self.watch_state_loop, daemon=True)
        listener_thread.start()
        sync_thread.start()
        return listener_thread


if __name__ == "__main__":
    bridge = CloudArduinoBridge()
    bridge.start()
    while True:
        time.sleep(1)
