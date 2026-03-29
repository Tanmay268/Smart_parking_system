from flask import Flask, jsonify, redirect, render_template, request, url_for

from serial_bridge import bridge
from storage import create_booking, dashboard_data, release_booking_by_slot


app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", data=dashboard_data(), bridge_status=bridge.last_event)


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
