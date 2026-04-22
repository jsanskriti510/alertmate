import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from twilio.rest import Client

app = Flask(__name__, template_folder='WEB_A_M')
CORS(app)

devices = {}

# -----------------------------
# Medicine Schedule
# -----------------------------
medicine_schedule = {
    "device123": {
        "hour": 15,
        "minute": 21
    }
}

already_sent = {}

# -----------------------------
# Twilio Config
# -----------------------------
ACCOUNT_SID = "AC8ef5e8f73ecb7a4ed96ff3582372d362"
AUTH_TOKEN = "55e7d8beefd258563674edf467963c87"
TWILIO_NUMBER = "+12605688024"
YOUR_NUMBER = "+919205823980"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_alert(device_id, msg):
    print("📡 Sending SMS...")
    try:
        message = client.messages.create(
            body=f"🔔 Alert!\nDevice: {device_id}\nMessage: {msg}",
            from_=TWILIO_NUMBER,
            to=YOUR_NUMBER
        )
        print("✅ SMS sent:", message.sid)
    except Exception as e:
        print("❌ Twilio Error:", str(e))


# -----------------------------
# Web Routes — FIXED filenames
# -----------------------------

@app.route("/")
def home():
    return render_template("login.html")

@app.route('/why_choose_us')
def features():
    return render_template('why_choose_us.html')   # was: '/why_choose_us'

@app.route('/demo')
def demo():
    return render_template('demo.html')             # was: '/demo'

@app.route('/contact')
def contact():
    return render_template('contact.html')          # was: '/contact'

@app.route('/howitworks')
def how_it_works():
    return render_template('howitworks.html')       # was: '/howitworks'

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboardpage.html')

@app.route('/falls')
def falls_page():
    return render_template('index.html')

@app.route('/help')
def help_page():
    return render_template('helppage.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy_policy.html')

@app.route('/aboutus')                              # was: missing entirely
def about_us():
    return render_template('aboutus.html')


# -----------------------------
# API Routes
# -----------------------------

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"error": "Device ID required"}), 400

    if device_id not in devices:
        devices[device_id] = {"falls": [], "medicines": []}

    return jsonify({"message": "Login successful", "device_id": device_id})


@app.route('/miss_medicine', methods=['POST'])
def miss_medicine():
    data = request.get_json()
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    if device_id not in devices:
        devices[device_id] = {"falls": [], "medicines": []}

    devices[device_id]["medicines"].append({
        "time": datetime.now().strftime("%H:%M:%S")
    })

    return jsonify({"message": "logged"})


@app.route('/set_medicine', methods=['POST'])
def set_medicine():
    data = request.get_json()
    device_id = data.get("device_id")
    hour = data.get("hour")
    minute = data.get("minute")

    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    if hour is None or minute is None:
        return jsonify({"error": "hour and minute required"}), 400

    if not (0 <= int(hour) <= 23) or not (0 <= int(minute) <= 59):
        return jsonify({"error": "Invalid hour or minute"}), 400

    medicine_schedule[device_id] = {
        "hour": int(hour),
        "minute": int(minute)
    }

    already_sent[device_id] = False

    print(f"✅ Alarm set for {device_id}: {hour}:{int(minute):02d}")
    return jsonify({"message": "Medicine alarm set"})


last_alarm_triggered = {}

@app.route('/check_alarm/<device_id>')
def check_alarm(device_id):
    now = datetime.now()

    if device_id in medicine_schedule:
        sched = medicine_schedule[device_id]

        if now.hour == sched["hour"] and now.minute == sched["minute"]:
            if not last_alarm_triggered.get(device_id):
                last_alarm_triggered[device_id] = True
                return jsonify({"ring": True})

    last_alarm_triggered[device_id] = False
    return jsonify({"ring": False})


@app.route('/sos', methods=['POST'])
def handle_sos():
    data = request.get_json()
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    print("🆘 SOS RECEIVED:", device_id)
    send_alert(device_id, "🚨 EMERGENCY SOS BUTTON PRESSED!")
    return jsonify({"message": "SOS sent"})


@app.route('/fall', methods=['POST'])
def handle_fall():
    data = request.get_json()
    device_id = data.get("device_id")
    acc = data.get("acc")

    if not device_id or acc is None:
        return jsonify({"error": "device_id and acc required"}), 400

    print("🔥 FALL RECEIVED:", data)

    if device_id not in devices:
        devices[device_id] = {"falls": [], "medicines": []}

    devices[device_id]["falls"].append({
        "acc": acc,
        "time": datetime.now().strftime("%H:%M:%S")
    })

    send_alert(device_id, f"Fall detected! Acceleration: {acc}g")
    return jsonify({"message": "Fall stored"})


@app.route('/api/dashboard/<device_id>')
def get_dashboard(device_id):
    if device_id not in devices:
        devices[device_id] = {"falls": [], "medicines": []}

    return jsonify({
        "total_falls": len(devices[device_id]["falls"]),
        "total_medicines": len(devices[device_id]["medicines"]),
        "falls": devices[device_id]["falls"],
        "medicines": devices[device_id]["medicines"]
    })


# -----------------------------
# Medicine Checker Thread
# -----------------------------
def medicine_checker():
    while True:
        now = datetime.now()
        print(f"⏰ Checking: {now.hour}:{now.minute}:{now.second}")

        for device_id, sched in list(medicine_schedule.items()):
            if now.hour == sched["hour"] and now.minute == sched["minute"]:
                if not already_sent.get(device_id):
                    send_alert(device_id, "Medicine Time")
                    already_sent[device_id] = True
            else:
                already_sent[device_id] = False

        time.sleep(2)


# -----------------------------
# Start Everything
# -----------------------------
if __name__ == '__main__':
    t = threading.Thread(target=medicine_checker)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
