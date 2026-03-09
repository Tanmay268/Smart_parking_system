import os


BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "data", "parking_data.json")
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")

SERIAL_PORT = "COM5"
BAUD_RATE = 9600
CAMERA_INDEX = 0
SHOW_CAMERA_PREVIEW = True
PREVIEW_DURATION_MS = 2000
CAMERA_WARMUP_FRAMES = 10

TOTAL_SLOTS = ["S1", "S2", "S3", "S4"]
