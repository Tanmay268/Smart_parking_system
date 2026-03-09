#include <Arduino.h>
#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

static const int ENTRY_IR_SENSOR_PIN = 2;
static const int EXIT_IR_SENSOR_PIN = 3;
static const int SERVO_PIN = 9;
static const int OPEN_ANGLE = 90;
static const int CLOSED_ANGLE = 0;
static const unsigned long DISPLAY_DELAY_MS = 3000;
static const unsigned long DEBOUNCE_DELAY_MS = 200;
static const int TOTAL_SLOTS = 4;

Servo gateServo;
LiquidCrystal_I2C lcd(0x27, 16, 2);

bool entryVehicleReported = false;
bool exitVehicleReported = false;
int availableSlots = TOTAL_SLOTS;

int lastEntrySensorState = HIGH;
int lastExitSensorState = HIGH;
unsigned long lastEntrySensorChange = 0;
unsigned long lastExitSensorChange = 0;

void showMessage(const String &line1, const String &line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);

  Serial.print("[LCD] ");
  Serial.print(line1);
  Serial.print(" | ");
  Serial.println(line2);
}

void showAvailableSlots() {
  showMessage("Smart Parking", "Available: " + String(availableSlots));
}

void openGate(const String &slot) {
  Serial.print("[Arduino] Opening gate for ");
  Serial.println(slot);

  showMessage("Access Granted", slot);
  gateServo.write(OPEN_ANGLE);
  delay(4000);
  gateServo.write(CLOSED_ANGLE);

  Serial.println("[Arduino] Gate closed");

  showMessage("Gate Closed", "Welcome");
  delay(1000);
  showAvailableSlots();
}

void denyAccess(const String &message) {
  Serial.print("[Arduino] Denied: ");
  Serial.println(message);

  showMessage("Access Denied", message);
  delay(DISPLAY_DELAY_MS);
  showAvailableSlots();
}

void setup() {
  pinMode(ENTRY_IR_SENSOR_PIN, INPUT);
  pinMode(EXIT_IR_SENSOR_PIN, INPUT);
  Serial.begin(9600);

  gateServo.attach(SERVO_PIN);
  gateServo.write(CLOSED_ANGLE);

  lcd.init();
  lcd.backlight();

  showMessage("Smart Parking", "Starting...");
  delay(1500);
  showAvailableSlots();

  Serial.println("[Arduino] System ready");
}

void loop() {
  int entrySensorValue = digitalRead(ENTRY_IR_SENSOR_PIN);
  int exitSensorValue = digitalRead(EXIT_IR_SENSOR_PIN);
  unsigned long currentTime = millis();

  if (entrySensorValue != lastEntrySensorState) {
    lastEntrySensorState = entrySensorValue;
    lastEntrySensorChange = currentTime;
  }

  if (exitSensorValue != lastExitSensorState) {
    lastExitSensorState = exitSensorValue;
    lastExitSensorChange = currentTime;
  }

  if (currentTime - lastEntrySensorChange > DEBOUNCE_DELAY_MS) {
    if (entrySensorValue == LOW && !entryVehicleReported) {
      Serial.println("VEHICLE_AT_GATE");
      Serial.println("[Arduino] Entry IR detected vehicle");
      showMessage("Vehicle Found", "Checking...");
      entryVehicleReported = true;
    }

    if (entrySensorValue == HIGH) {
      entryVehicleReported = false;
    }
  }

  if (currentTime - lastExitSensorChange > DEBOUNCE_DELAY_MS) {
    if (exitSensorValue == LOW && !exitVehicleReported) {
      Serial.println("VEHICLE_EXIT");
      Serial.println("[Arduino] Exit IR detected vehicle");
      showMessage("Vehicle Exit", "Checking...");
      exitVehicleReported = true;
    }

    if (exitSensorValue == HIGH) {
      exitVehicleReported = false;
    }
  }

  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.length() == 0) {
      return;
    }

    Serial.print("[Arduino] Received command: ");
    Serial.println(command);

    if (command.startsWith("OPEN:")) {
      String slot = command.substring(5);
      if (slot.length() > 0) {
        openGate("Slot " + slot);
      } else {
        showMessage("Invalid Slot", "Try Again");
        delay(DISPLAY_DELAY_MS);
        showAvailableSlots();
      }
    } else if (command.startsWith("STATUS:")) {
      availableSlots = command.substring(7).toInt();

      if (availableSlots < 0) {
        availableSlots = 0;
      }
      if (availableSlots > TOTAL_SLOTS) {
        availableSlots = TOTAL_SLOTS;
      }

      Serial.print("[Arduino] Updated available slots: ");
      Serial.println(availableSlots);
      showAvailableSlots();
    } else if (command.startsWith("STATUS:")) {
        availableSlots = command.substring(7).toInt();

        if (availableSlots < 0) {
          availableSlots = 0;
        }
        if (availableSlots > TOTAL_SLOTS) {
          availableSlots = TOTAL_SLOTS;
        }

        Serial.print("[Arduino] Updated available slots: ");
        Serial.println(availableSlots);
        showAvailableSlots();
    } else if (command == "FULL") {
      denyAccess("Parking Full");
    } else if (command == "DENY") {
      denyAccess("Plate Error");
    } else {
      showMessage("Unknown Cmd", command);
      delay(DISPLAY_DELAY_MS);
      showAvailableSlots();
    }
  }
}
