# Smart Parking System

This project is a minimal end-to-end smart parking system for an embedded systems project using:

- Arduino Nano
- IR sensors for gate trigger / vehicle detection at the gate
- Servo motor for gate control
- LCD/LED display for slot messages
- Python backend for booking and gate decisions
- Camera + number plate recognition in Python
- Simple website for slot booking

## Project Structure

- `architecture.md` - architecture and flow diagram
- `arduino/gate_controller.ino` - Arduino Nano code
- `backend/app.py` - Flask website + API
- `backend/plate_recognition.py` - number plate recognition pipeline
- `backend/serial_bridge.py` - Python to Arduino serial communication
- `backend/storage.py` - booking and slot management
- `backend/templates/` - website HTML
- `backend/static/styles.css` - basic styling
- `requirements.txt` - Python dependencies

## Main Flow

1. User books a slot on the website with car number.
2. On arrival, the gate IR sensor detects a vehicle.
3. Arduino sends a serial event to Python.
4. Python captures a camera frame and reads the number plate.
5. If the plate already has a booking, Python sends `OPEN:<slot>` to Arduino.
6. If there is no booking but a slot is empty, Python auto-assigns a slot and sends `OPEN:<slot>`.
7. If parking is full, Python sends `FULL`.
8. Arduino opens the servo gate and shows the slot or full message on the display.

## Hardware Note

For demonstration, the camera and number plate detection run on the computer, not on Arduino Nano. The Nano only handles sensors, servo, and display.

## Run

1. Connect Arduino Nano and upload `arduino/gate_controller.ino`.
2. Edit the serial port and camera index in `backend/config.py`.
3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Start the backend:

```bash
python backend/app.py
```

5. Open `http://127.0.0.1:5000`

## Demo Mode

If number plate OCR is not stable during presentation, you can:

- keep the same pipeline but use a fixed test image
- tune the regex for your local plate format
- manually enter plates in the website and use the live gate logic for the demo
