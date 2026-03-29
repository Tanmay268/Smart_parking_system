#include <Arduino.h>
#include <Servo.h>
#include <Wire.h>
// #include <LiquidCrystal_I2C.h>

static const int ENTRY_IR_SENSOR_PIN = 2;
static const int EXIT_IR_SENSOR_PIN = 3;
static const int SERVO_PIN = 9;
static const int OPEN_ANGLE = 90;
static const int CLOSED_ANGLE = 0;
static const unsigned long DISPLAY_DELAY_MS = 3000;
static const unsigned long DEBOUNCE_DELAY_MS = 200;
static const int TOTAL_SLOTS = 4;

Servo gateServo;
// LiquidCrystal_I2C lcd(0x27, 16, 2);

bool entryVehicleReported = false;
bool exitVehicleReported = false;
int availableSlots = TOTAL_SLOTS;

int lastEntryReading = HIGH;
int lastExitReading = HIGH;
int stableEntryState = HIGH;
int stableExitState = HIGH;
unsigned long lastEntryChangeMs = 0;
unsigned long lastExitChangeMs = 0;

void showMessage(const String &line1, const String &line2) {
  // LCD disabled for now. Keep the strings visible in serial logs.
  Serial.print("[LCD] ");
  Serial.print(line1);
  Serial.print(" | ");
  Serial.println(line2);
  (void)line1;
  (void)line2;
}

void showAvailableSlots() { showMessage("Smart Parking", "Available: " + String(availableSlots)); }

void openGate(const String &slot) {
  showMessage("Access Granted", slot);
  gateServo.write(OPEN_ANGLE);
  delay(4000);
  gateServo.write(CLOSED_ANGLE);
  showMessage("Gate Closed", "Welcome");
  delay(1000);
  showAvailableSlots();
}

void denyAccess(const String &message) {
  showMessage("Access Denied", message);
  delay(DISPLAY_DELAY_MS);
  showAvailableSlots();
}

void setup() {
  pinMode(ENTRY_IR_SENSOR_PIN, INPUT_PULLUP);
  pinMode(EXIT_IR_SENSOR_PIN, INPUT_PULLUP);
  Serial.begin(9600);

  gateServo.attach(SERVO_PIN);
  gateServo.write(CLOSED_ANGLE);

  // lcd.init();
  // lcd.backlight();
  showMessage("Smart Parking", "Starting...");
  delay(1500);
  showAvailableSlots();

  Serial.println("[Arduino] System ready");
}

void loop() {
  int entrySensorValue = digitalRead(ENTRY_IR_SENSOR_PIN);
  int exitSensorValue = digitalRead(EXIT_IR_SENSOR_PIN);
  unsigned long currentTime = millis();

  if (entrySensorValue != lastEntryReading) {
    lastEntryReading = entrySensorValue;
    lastEntryChangeMs = currentTime;
  }

  if (exitSensorValue != lastExitReading) {
    lastExitReading = exitSensorValue;
    lastExitChangeMs = currentTime;
  }

  if ((currentTime - lastEntryChangeMs) > DEBOUNCE_DELAY_MS && entrySensorValue != stableEntryState) {
    stableEntryState = entrySensorValue;
    Serial.print("[Arduino] Entry sensor stable state: ");
    Serial.println(stableEntryState == LOW ? "LOW" : "HIGH");

    if (stableEntryState == LOW && !entryVehicleReported) {
      Serial.println("VEHICLE_AT_GATE");
      showMessage("Vehicle Found", "Checking...");
      entryVehicleReported = true;
    }

    if (stableEntryState == HIGH) {
      entryVehicleReported = false;
    }
  }

  if ((currentTime - lastExitChangeMs) > DEBOUNCE_DELAY_MS && exitSensorValue != stableExitState) {
    stableExitState = exitSensorValue;
    Serial.print("[Arduino] Exit sensor stable state: ");
    Serial.println(stableExitState == LOW ? "LOW" : "HIGH");

    if (stableExitState == LOW && !exitVehicleReported) {
      Serial.println("VEHICLE_EXIT");
      showMessage("Vehicle Exit", "Checking...");
      exitVehicleReported = true;
    }

    if (stableExitState == HIGH) {
      exitVehicleReported = false;
    }
  }

  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.startsWith("OPEN:")) {
      String slot = command.substring(5);
      openGate("Slot " + slot);
    } else if (command.startsWith("STATUS:")) {
      availableSlots = command.substring(7).toInt();
      showAvailableSlots();
    } else if (command == "FULL") {
      denyAccess("Parking Full");
    } else if (command == "DENY") {
      denyAccess("Plate Error");
    } else if (command.length() > 0) {
      showMessage("Unknown Cmd", command);
      delay(DISPLAY_DELAY_MS);
      showAvailableSlots();
    }
  }
}
