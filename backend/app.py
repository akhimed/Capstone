from flask import Flask, jsonify, send_from_directory, request, session
import database
import scheduler
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import random
import os
from dotenv import load_dotenv  # ✅ New import

load_dotenv()  # ✅ Load .env variables


logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

@app.route("/", methods=["GET"])
def home():
    return send_from_directory("../frontend", "index.html")

@app.route("/fetch_availabilities", methods=["GET"])
def fetch_availabilities():
    availabilities = database.get_availabilities()
    if not availabilities:
        return jsonify({"error": "No availabilities found"}), 404
    return jsonify({"message": "Existing employee availabilities!", "schedule": availabilities})

@app.route("/generate_optimized_schedule", methods=["GET"])
def generate_optimized_schedule():
    availabilities = database.get_availabilities()
    if not availabilities:
        return jsonify({"error": "No availabilities found"}), 400

    try:
        ai_response = scheduler.generate_ai_schedule(availabilities)
        logging.info(f"Raw AI-generated schedule: {ai_response}")

        if "schedule" in ai_response:
            ai_schedule = ai_response["schedule"]
        elif "weekly_schedule" in ai_response:
            ai_schedule = []
            for day, shifts in ai_response["weekly_schedule"].items():
                for shift in shifts:
                    ai_schedule.append({
                        "name": shift.get("employee_name", "Unknown"),
                        "availability": shift.get("shift", "N/A"),
                        "date": f"2025-03-{random.randint(1, 28)}"
                    })
        else:
            logging.error(f"Unexpected AI response format: {ai_response}")
            return jsonify({"error": "Invalid AI response format"}), 500

        structured_schedule = []
        seen_entries = set()
        for entry in ai_schedule:
            name = entry.get("name")
            availability = entry.get("availability")
            date = entry.get("date")
            key = (name, availability, date)
            if not all([name, availability, date]) or key in seen_entries:
                continue
            structured_schedule.append({
                "name": name,
                "availability": availability,
                "date": date
            })
            seen_entries.add(key)

        if not structured_schedule:
            return jsonify({"error": "AI schedule was generated, but no valid entries were found."}), 500

        return jsonify({"message": "AI-generated schedule!", "schedule": structured_schedule})

    except Exception as e:
        logging.error(f"Error generating AI schedule: {e}")
        return jsonify({"error": "Failed to generate AI schedule"}), 500

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = generate_password_hash(data.get("password"))
    role = data.get("role")

    if not username or not password or not role:
        return jsonify({"error": "Missing fields"}), 400

    success = database.add_user(username, password, role)
    return jsonify({"message": "Registered!"}) if success else (jsonify({"error": "Username taken"}), 400)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = database.get_user_by_username(data.get("username"))
    if user and check_password_hash(user["password"], data.get("password")):
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({"message": "Login successful!", "role": user["role"]})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/post_schedule", methods=["POST"])
def post_schedule():
    if "role" not in session or session["role"] != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json.get("schedule")
    if not data:
        return jsonify({"error": "No schedule data received"}), 400

    logging.info("Received schedule to save: %s", data)

    # ✅ Clear existing schedule BEFORE saving new one
    database.clear_posted_schedule()

    for entry in data:
        name = entry.get("name")
        availability = entry.get("availability")
        date = entry.get("date")

        logging.info(f"Saving entry: {name}, {availability}, {date}")
        if name and availability and date:
            database.save_posted_schedule(name, availability, date)

    logging.info("Saved schedule: %s", data)
    return jsonify({"message": "Schedule posted!"})


@app.route("/view_schedule", methods=["GET"])
def view_schedule():
    logging.info("Retrieving posted schedule from DB")
    schedule = database.get_posted_schedule()
    logging.info("Retrieved schedule: %s", schedule)
    return jsonify({"schedule": schedule})

@app.route("/add_availability", methods=["POST"])
def add_availability():
    data = request.json
    name = data.get("name")
    availability = data.get("availability")
    if name and availability:
        success = database.add_availability(name, availability)
        if success:
            return jsonify({"message": "Availability submitted!"})
    return jsonify({"error": "Missing name or availability"}), 400

if __name__ == "__main__":
    database.create_tables()
    app.run(debug=True)
