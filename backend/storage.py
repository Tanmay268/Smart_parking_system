import json
import os
from datetime import datetime

from config import DATA_FILE, TOTAL_SLOTS


def _ensure_data_file():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        save_data(
            {
                "slots": {slot: None for slot in TOTAL_SLOTS},
                "bookings": {},
                "events": [],
            }
        )


def load_data():
    _ensure_data_file()
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def normalize_plate(plate):
    return "".join(ch for ch in plate.upper() if ch.isalnum())


def get_available_slot(data):
    for slot, plate in data["slots"].items():
        if plate is None:
            return slot
    return None


def find_slot_by_plate(data, plate_number):
    for slot, plate in data["slots"].items():
        if plate == plate_number:
            return slot
    return None


def create_booking(owner_name, plate_number, phone=""):
    data = load_data()
    normalized_plate = normalize_plate(plate_number)

    if normalized_plate in data["bookings"]:
        return False, "This vehicle already has a booking.", data["bookings"][normalized_plate]["slot"]

    occupied_slot = find_slot_by_plate(data, normalized_plate)
    if occupied_slot:
        return False, "This vehicle is already parked in the system.", occupied_slot

    slot = get_available_slot(data)
    if not slot:
        return False, "Parking full.", None

    booking = {
        "owner_name": owner_name,
        "phone": phone,
        "plate_number": normalized_plate,
        "slot": slot,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    data["bookings"][normalized_plate] = booking
    data["slots"][slot] = normalized_plate
    data["events"].append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "type": "booking_created",
            "plate_number": normalized_plate,
            "slot": slot,
        }
    )
    save_data(data)
    return True, "Booking created.", slot


def get_booking_by_plate(plate_number):
    data = load_data()
    return data["bookings"].get(normalize_plate(plate_number))


def auto_book_if_available(plate_number):
    data = load_data()
    normalized_plate = normalize_plate(plate_number)

    existing = data["bookings"].get(normalized_plate)
    if existing:
        return "existing", existing["slot"]

    occupied_slot = find_slot_by_plate(data, normalized_plate)
    if occupied_slot:
        return "existing", occupied_slot

    slot = get_available_slot(data)
    if not slot:
        return "full", None

    booking = {
        "owner_name": "Gate Auto Booking",
        "phone": "",
        "plate_number": normalized_plate,
        "slot": slot,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    data["bookings"][normalized_plate] = booking
    data["slots"][slot] = normalized_plate
    data["events"].append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "type": "auto_booked_at_gate",
            "plate_number": normalized_plate,
            "slot": slot,
        }
    )
    save_data(data)
    return "new", slot


def release_booking_by_plate(plate_number):
    data = load_data()
    normalized_plate = normalize_plate(plate_number)

    slot = find_slot_by_plate(data, normalized_plate)
    booking = data["bookings"].pop(normalized_plate, None)

    if not slot and not booking:
        return False, None

    if not slot and booking:
        slot = booking["slot"]

    if slot in data["slots"]:
        data["slots"][slot] = None

    data["events"].append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "type": "vehicle_exited",
            "plate_number": normalized_plate,
            "slot": slot,
        }
    )
    save_data(data)
    return True, slot


def release_booking_by_slot(slot):
    data = load_data()
    slot = slot.strip().upper()

    if slot not in data["slots"]:
        return False, None

    plate = data["slots"].get(slot)
    if not plate:
        return False, None

    data["slots"][slot] = None
    data["bookings"].pop(plate, None)
    data["events"].append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "type": "slot_cleared_from_dashboard",
            "plate_number": plate,
            "slot": slot,
        }
    )
    save_data(data)
    return True, plate


def dashboard_data():
    data = load_data()
    used = sum(1 for plate in data["slots"].values() if plate is not None)
    state_version = str(os.path.getmtime(DATA_FILE)) if os.path.exists(DATA_FILE) else "empty"
    return {
        "slots": data["slots"],
        "bookings": data["bookings"],
        "events": list(reversed(data["events"][-10:])),
        "total": len(data["slots"]),
        "available": len(data["slots"]) - used,
        "occupied": used,
        "state_version": state_version,
    }
