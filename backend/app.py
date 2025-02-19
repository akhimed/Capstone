from flask import Flask, request, jsonify, send_from_directory
import database  # Import your database functions
from flask_cors import CORS  # Add this
import logging

logging.basicConfig(level=logging.INFO)  # Logs info in the console


app = Flask(__name__)
CORS(app)  # Allow requests from frontend

#hi

@app.route("/", methods=["GET"])
def home():
    return send_from_directory("../frontend", "index.html")

@app.route("/add_availability", methods=["POST"])
def add_availability():
    data = request.json
    name = data.get("name")
    availability = data.get("availability")

    if name and availability:
        success = database.add_availability(name, availability)
        if success:
            return jsonify({"message": "Availability added!"}), 201
        else:
            return jsonify({"error": "Failed to add availability"}), 500
    return jsonify({"error": "Missing name or availability"}), 400

@app.route("/generate_schedule", methods=["GET"])
def generate_schedule():
    availabilities = database.get_availabilities()
    return jsonify({"message": "AI-generated schedule!", "schedule": availabilities})

if __name__ == "__main__":
    database.create_tables()  # Ensure tables exist before running
    app.run(debug=True)

