# Smart Parking System Architecture

## High-Level Architecture

```text
                        +----------------------+
                        |  Booking Website     |
                        |  Flask Frontend      |
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        | Python Backend       |
                        | - Slot manager       |
                        | - Plate recognition  |
                        | - Serial bridge      |
                        +----+------------+----+
                             |            |
                  Camera USB |            | USB Serial
                             v            v
                    +----------------+   +----------------------+
                    | Camera Module  |   | Arduino Nano        |
                    | Captures plate |   | - IR gate trigger   |
                    +----------------+   | - Servo control     |
                                         | - LCD/LED display   |
                                         +----+-----------+----+
                                              |           |
                                              v           v
                                        +---------+   +--------+
                                        | Servo   |   | IR     |
                                        | Gate    |   | Sensor |
                                        +---------+   +--------+
```

## Functional Blocks

### 1. Website

- User enters:
  - name
  - car number
  - optional phone number
- Website shows:
  - total slots
  - available slots
  - current bookings

### 2. Python Backend

- Stores booking data in JSON
- Assigns first available slot
- Receives vehicle trigger from Arduino over serial
- Reads camera frame
- Recognizes number plate
- Checks:
  - already booked
  - no booking but slot available
  - parking full
- Sends gate command back to Arduino

### 3. Arduino Nano

- Reads IR sensor
- When vehicle is detected, sends `VEHICLE_AT_GATE`
- Waits for Python response:
  - `OPEN:S1`
  - `OPEN:S2`
  - `FULL`
  - `DENY`
- Shows status on LCD/LED display
- Opens servo gate for a few seconds if allowed

## Gate Decision Logic

```text
Vehicle reaches gate
        |
        v
IR sensor detects vehicle
        |
        v
Arduino -> Python: VEHICLE_AT_GATE
        |
        v
Python captures frame from camera
        |
        v
Read number plate
        |
        v
Is plate already booked?
   | yes                    | no
   v                        v
Open gate             Any slot free?
show booked slot        | yes          | no
                        v              v
                  auto-book slot    show FULL
                  open gate         keep gate closed
```

## Suggested Slot Model

- Total slots: 4 or 6 for demo
- Slot labels: `S1`, `S2`, `S3`, `S4`
- Status values:
  - `free`
  - `reserved`
  - `occupied`

For a classroom demo, you can simplify `reserved` and `occupied` into one booked state.

## Recommended Components

- Arduino Nano
- 1 x IR obstacle sensor at entry gate
- SG90 or MG995 servo motor
- 16x2 I2C LCD or compatible LED display
- USB webcam
- 5V regulated supply for sensors/display
- Separate stable power for servo if needed

## Important Constraint

Real-time number plate recognition should run on a laptop/Raspberry Pi, not on the Arduino Nano. The Nano is too limited for OCR and image processing.
