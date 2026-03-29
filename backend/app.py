import os

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

try:
    from .config import BRIDGE_API_KEY
    from .storage import auto_book_if_available, create_booking, dashboard_data, release_booking_by_plate, release_booking_by_slot
except ImportError:
    from config import BRIDGE_API_KEY
    from storage import auto_book_if_available, create_booking, dashboard_data, release_booking_by_plate, release_booking_by_slot


class NullBridge:
    last_event = "Cloud mode active. Run backend/cloud_bridge.py near Arduino and LCD."

    def send_status(self):
        return None

    def start(self):
        return None

    def handle_vehicle_at_gate(self):
        return None


if os.getenv("VERCEL"):
    bridge = NullBridge()
else:
    try:
        from .serial_bridge import bridge
    except ImportError:
        from serial_bridge import bridge


app = Flask(__name__)


def static_css_url():
    if os.getenv("VERCEL"):
        return "/styles.css"
    return url_for("static", filename="styles.css")


def require_bridge_key():
    if not BRIDGE_API_KEY:
        return
    provided_key = request.headers.get("X-Bridge-Key", "")
    if provided_key != BRIDGE_API_KEY:
        abort(401)


@app.route("/", methods=["GET"])
def home():
    return render_template(
        "index.html",
        data=dashboard_data(),
        bridge_status=bridge.last_event,
        static_css_url=static_css_url(),
    )


@app.route("/state", methods=["GET"])
def state():
    data = dashboard_data()
    return jsonify(
        {
            "slots": data["slots"],
            "recent_bookings": data["recent_bookings"],
            "total": data["total"],
            "available": data["available"],
            "reserved": data["reserved"],
            "occupied": data["occupied"],
            "bridge_status": bridge.last_event,
            "state_version": data["state_version"],
        }
    )


@app.route("/api/gate/entry", methods=["POST"])
def gate_entry():
    require_bridge_key()
    payload = request.get_json(silent=True) or request.form
    plate_number = (payload.get("plate_number", "") or "").strip()
    if not plate_number:
        return jsonify({"action": "DENY", "message": "Plate number is required."}), 400

    status, slot = auto_book_if_available(plate_number)
    if status in {"existing", "new"}:
        return jsonify(
            {
                "action": "OPEN",
                "slot": slot,
                "plate_number": plate_number,
                "message": f"Gate opened for slot {slot}.",
            }
        )

    return jsonify(
        {
            "action": "FULL",
            "slot": None,
            "plate_number": plate_number,
            "message": "Parking is full.",
        }
    )


@app.route("/api/gate/exit", methods=["POST"])
def gate_exit():
    require_bridge_key()
    payload = request.get_json(silent=True) or request.form
    plate_number = (payload.get("plate_number", "") or "").strip()
    if not plate_number:
        return jsonify({"action": "NO_PLATE", "message": "Plate number is required."}), 400

    released, slot = release_booking_by_plate(plate_number)
    if released:
        return jsonify(
            {
                "action": "OPEN",
                "slot": slot,
                "plate_number": plate_number,
                "message": f"Exit cleared for slot {slot}.",
            }
        )

    return jsonify(
        {
            "action": "NOT_FOUND",
            "slot": None,
            "plate_number": plate_number,
            "message": "No active slot found for this plate.",
        }
    )


@app.route("/book", methods=["POST"])
def book_slot():
    owner_name = request.form.get("owner_name", "").strip()
    phone = request.form.get("phone", "").strip()
    plate_number = request.form.get("plate_number", "").strip()

    if not owner_name or not plate_number:
        return render_template(
            "index.html",
            data=dashboard_data(),
            bridge_status=bridge.last_event,
            static_css_url=static_css_url(),
            message="Name and car number are required.",
            success=False,
        )

    success, message, slot = create_booking(owner_name, plate_number, phone)
    if success:
        message = f"{message} Assigned slot: {slot}"
    bridge.send_status()

    return render_template(
        "index.html",
        data=dashboard_data(),
        bridge_status=bridge.last_event,
        static_css_url=static_css_url(),
        message=message,
        success=success,
    )


@app.route("/release-slot", methods=["POST"])
def release_slot():
    slot = request.form.get("slot", "").strip().upper()
    released, plate = release_booking_by_slot(slot)
    bridge.send_status()

    if released:
        message = f"Released {slot} for vehicle {plate}."
        success = True
    else:
        message = f"Could not release {slot}."
        success = False

    return render_template(
        "index.html",
        data=dashboard_data(),
        bridge_status=bridge.last_event,
        static_css_url=static_css_url(),
        message=message,
        success=success,
    )


@app.route("/simulate-gate", methods=["POST"])
def simulate_gate():
    bridge.handle_vehicle_at_gate()
    return redirect(url_for("home"))


# @app.route("/manual-command", methods=["POST"])
# def manual_command():
#     command = request.form.get("command", "").strip().upper()
#
#     if command.startswith("OPEN:"):
#         bridge.send_command(command)
#         bridge.last_event = f"Manual test sent: {command}"
#     elif command in {"FULL", "DENY"}:
#         bridge.send_command(command)
#         bridge.last_event = f"Manual test sent: {command}"
#     elif command == "STATUS":
#         bridge.send_status()
#         bridge.last_event = "Manual test sent: STATUS update"
#     else:
#         bridge.last_event = f"Manual test rejected: {command or 'empty command'}"
#
#     return redirect(url_for("home"))


if __name__ == "__main__":
    try:
        bridge.start()
    except Exception as exc:
        bridge.last_event = f"Bridge not started: {exc}"

    app.run(debug=True, host="127.0.0.1", port=5000)
