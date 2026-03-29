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
        data = json.load(file)
    return normalize_data(data)


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def current_timestamp():
    return datetime.now().isoformat(timespec="seconds")


def normalize_data(data):
    data.setdefault("slots", {slot: None for slot in TOTAL_SLOTS})
    data.setdefault("bookings", {})
    data.setdefault("events", [])

    normalized_slots = {slot: None for slot in TOTAL_SLOTS}
    normalized_bookings = {}

    for plate, booking in data["bookings"].items():
        normalized_plate = normalize_plate(plate)
        slot = str(booking.get("slot", "")).strip().upper()
        if slot not in TOTAL_SLOTS:
            continue

        status = booking.get("status")
        if status not in {"reserved", "parked"}:
            status = "parked" if data["slots"].get(slot) == normalized_plate else "reserved"

        normalized_booking = {
            "owner_name": booking.get("owner_name", ""),
            "phone": booking.get("phone", ""),
            "plate_number": normalized_plate,
            "slot": slot,
            "status": status,
            "created_at": booking.get("created_at") or current_timestamp(),
            "last_gate_entry_at": booking.get("last_gate_entry_at"),
        }
        normalized_bookings[normalized_plate] = normalized_booking
        normalized_slots[slot] = normalized_plate

    data["bookings"] = normalized_bookings
    data["slots"] = normalized_slots
    return data


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


def find_booking_by_slot(data, slot):
    for plate, booking in data["bookings"].items():
        if booking.get("slot") == slot:
            return plate, booking
    return None, None


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
        "status": "reserved",
        "created_at": current_timestamp(),
        "last_gate_entry_at": None,
    }

    data["bookings"][normalized_plate] = booking
    data["slots"][slot] = normalized_plate
    data["events"].append(
        {
            "time": current_timestamp(),
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
    event_time = current_timestamp()

    existing = data["bookings"].get(normalized_plate)
    if existing:
        existing["status"] = "parked"
        existing["last_gate_entry_at"] = event_time
        data["events"].append(
            {
                "time": event_time,
                "type": "vehicle_entered",
                "plate_number": normalized_plate,
                "slot": existing["slot"],
            }
        )
        save_data(data)
        return "existing", existing["slot"]

    occupied_slot = find_slot_by_plate(data, normalized_plate)
    if occupied_slot:
        plate, booking = find_booking_by_slot(data, occupied_slot)
        if booking:
            booking["status"] = "parked"
            booking["last_gate_entry_at"] = event_time
        data["events"].append(
            {
                "time": event_time,
                "type": "vehicle_entered",
                "plate_number": normalized_plate,
                "slot": occupied_slot,
            }
        )
        save_data(data)
        return "existing", occupied_slot

    slot = get_available_slot(data)
    if not slot:
        return "full", None

    booking = {
        "owner_name": "Gate Auto Booking",
        "phone": "",
        "plate_number": normalized_plate,
        "slot": slot,
        "status": "parked",
        "created_at": event_time,
        "last_gate_entry_at": event_time,
    }
    data["bookings"][normalized_plate] = booking
    data["slots"][slot] = normalized_plate
    data["events"].append(
        {
            "time": event_time,
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
            "time": current_timestamp(),
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

    plate, booking = find_booking_by_slot(data, slot)
    if not plate or not booking:
        return False, None

    data["slots"][slot] = None
    data["bookings"].pop(plate, None)
    data["events"].append(
        {
            "time": current_timestamp(),
            "type": "slot_cleared_from_dashboard",
            "plate_number": plate,
            "slot": slot,
        }
    )
    save_data(data)
    return True, plate


def dashboard_data():
    data = load_data()
    reserved = 0
    occupied = 0
    slot_view = {}

    for slot in TOTAL_SLOTS:
        plate, booking = find_booking_by_slot(data, slot)
        if booking:
            status = booking.get("status", "reserved")
            if status == "parked":
                occupied += 1
            else:
                reserved += 1
            slot_view[slot] = {
                "plate_number": plate,
                "status": status,
                "owner_name": booking.get("owner_name", ""),
            }
        else:
            slot_view[slot] = {
                "plate_number": None,
                "status": "free",
                "owner_name": "",
            }

    state_version = str(os.path.getmtime(DATA_FILE)) if os.path.exists(DATA_FILE) else "empty"
    recent_bookings = sorted(
        (
            {
                "plate_number": plate,
                "owner_name": booking.get("owner_name", ""),
                "slot": booking.get("slot", ""),
                "status": booking.get("status", "reserved"),
                "updated_at": booking.get("last_gate_entry_at") or booking.get("created_at", ""),
            }
            for plate, booking in data["bookings"].items()
        ),
        key=lambda booking: booking["updated_at"],
        reverse=True,
    )
    return {
        "slots": slot_view,
        "bookings": data["bookings"],
        "recent_bookings": recent_bookings,
        "events": list(reversed(data["events"][-10:])),
        "total": len(TOTAL_SLOTS),
        "available": len(TOTAL_SLOTS) - reserved - occupied,
        "reserved": reserved,
        "occupied": occupied,
        "state_version": state_version,
    }
