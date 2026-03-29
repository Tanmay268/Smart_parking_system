import os


BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "data", "parking_data.json")
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")

SERIAL_PORT = os.getenv("SERIAL_PORT", "COM5")
BAUD_RATE = int(os.getenv("BAUD_RATE", "9600"))
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
SHOW_CAMERA_PREVIEW = True
PREVIEW_DURATION_MS = 2000
CAMERA_WARMUP_FRAMES = 10

CLOUD_API_BASE_URL = os.getenv("CLOUD_API_BASE_URL", "").rstrip("/")
BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY", "")
BLOB_DATA_PATH = os.getenv("BLOB_DATA_PATH", "smart-parking/parking_data.json")

TOTAL_SLOTS = ["S1", "S2", "S3", "S4"]
