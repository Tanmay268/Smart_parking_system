import re
import time
from datetime import datetime
from pathlib import Path

import cv2
import easyocr

from config import CAPTURES_DIR, CAMERA_WARMUP_FRAMES, PREVIEW_DURATION_MS, SHOW_CAMERA_PREVIEW


class NumberPlateRecognizer:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.reader = easyocr.Reader(["en"], gpu=False)
        self.last_capture_path = None

    def capture_frame(self):
        camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not camera.isOpened():
            camera.release()
            camera = cv2.VideoCapture(self.camera_index)

        success = False
        frame = None
        time.sleep(0.5)
        for _ in range(CAMERA_WARMUP_FRAMES):
            success, frame = camera.read()
            if not success:
                time.sleep(0.1)
        camera.release()
        if not success or frame is None:
            return None
        self.last_capture_path = self.save_capture(frame)
        return frame

    def save_capture(self, frame):
        captures_dir = Path(CAPTURES_DIR)
        captures_dir.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("capture_%Y%m%d_%H%M%S.jpg")
        capture_path = captures_dir / filename
        cv2.imwrite(str(capture_path), frame)
        return str(capture_path)

    def show_preview(self, frame):
        if not SHOW_CAMERA_PREVIEW:
            return
        cv2.imshow("Smart Parking Camera", frame)
        cv2.waitKey(PREVIEW_DURATION_MS)
        cv2.destroyWindow("Smart Parking Camera")

    def preprocess(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(filtered, 30, 200)
        return edged

    def extract_plate_text(self, frame):
        result = self.reader.readtext(frame)
        candidates = []
        for _, text, confidence in result:
            cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())
            if len(cleaned) >= 6:
                candidates.append((cleaned, confidence))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates[0][0]

    def recognize_plate(self):
        frame = self.capture_frame()
        if frame is None:
            return None
        self.show_preview(frame)

        processed = self.preprocess(frame)
        plate = self.extract_plate_text(processed)
        if plate:
            return plate

        return self.extract_plate_text(frame)


if __name__ == "__main__":
    recognizer = NumberPlateRecognizer(camera_index=0)
    plate = recognizer.recognize_plate()
    print("Detected Plate:", plate or "No plate detected")
