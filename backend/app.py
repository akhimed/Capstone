from flask import Flask, jsonify, send_from_directory, request, session, redirect, url_for
import database
import scheduler
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import random
import os
from dotenv import load_dotenv  # ✅ New import
from flask_mail import Mail, Message  # ✅ New import
from datetime import datetime
import traceback
load_dotenv()  # ✅ Load .env variables


logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)
app.secret_key = os.getenv("OPENAI_API_KEY")

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'WorkSyncLMS@gmail.com'
app.config['MAIL_PASSWORD'] = 'zazv cypz bmza lczg'
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']


mail = Mail(app)
@app.route("/", methods=["GET"])
def home():
    if "username" in session:
        return redirect("/calendar.html")
    return redirect("/login.html")


@app.route("/fetch_availabilities", methods=["GET"])
def fetch_availabilities():
    availabilities = database.get_availabilities()
    if not availabilities:
        return jsonify({"error": "No availabilities found"}), 404
    return jsonify({"message": "Existing employee availabilities!", "schedule": availabilities})

@app.route("/generate_optimized_schedule", methods=["GET"])
def generate_optimized_schedule():
    availabilities = database.get_availabilities()
    print("🟢 Availabilities going into GPT:", availabilities)  # ← ADD THIS LINE

    if not availabilities:
        return jsonify({"error": "No availabilities found"}), 400

    try:
        ai_response = scheduler.generate_ai_schedule(availabilities)
        logging.info(f"📦 Raw AI response: {ai_response}")

        if not ai_response:
            logging.error("❌ AI response is empty or None")
            return jsonify({"error": "AI response was empty"}), 500

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
            logging.error(f"❌ Unexpected AI response format: {ai_response}")
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
        logging.error(f"❌ Exception in generate_optimized_schedule: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate AI schedule"}), 500

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password_raw = data.get("password")
    role = data.get("role")
    email = data.get("email")
    owner_key = data.get("ownerKey")  # 🛡️ optional field

    # 🔐 Owner key stored safely — consider loading from environment in production
    OWNER_SECRET_KEY = "SuperSecret123"

    # ✅ Basic validation
    if not username or not password_raw or not role or not email:
        return jsonify({"error": "Missing fields"}), 400

    # 🔐 Extra validation for owner role
    if role == "owner":
        if not owner_key or owner_key != OWNER_SECRET_KEY:
            return jsonify({"error": "Invalid or missing owner key"}), 403

    # 🔑 Default is_approved = True for owners, False for employees
    is_approved = True if role == "owner" else False

    password = generate_password_hash(password_raw)

    success = database.add_user(username, password, role, email, is_approved)
    
    if success:
        return jsonify({"message": "Registered!"})
    else:
        return jsonify({"error": "Username or email already in use"}), 400


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = database.get_user_by_username(data.get("username"))

    if user and check_password_hash(user["password"], data.get("password")):
        # 🛡️ Approval check
        if not user.get("is_approved", True):  # Defaults to True for backwards compatibility
            return jsonify({"error": "Account not approved by an owner yet."}), 403

        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({
            "message": "Login successful!",
            "role": user["role"],
            "username": user["username"]
        })

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

    # Clear existing schedule
    database.clear_posted_schedule()

    for entry in data:
        name = entry.get("name")
        availability = entry.get("availability")
        date = entry.get("date")

        # 🛠️ Normalize and validate the date
        try:
            date = datetime.strptime(str(date), "%Y-%m-%d").date().isoformat()
        except ValueError:
            logging.warning(f"Skipping invalid date for {name}: {date}")
            continue

        logging.info(f"Saving entry: {name}, {availability}, {date}")
        if name and availability and date:
            database.save_posted_schedule(name, availability, date)

    # 📬 Email logic
    all_users = database.get_all_user_emails()
    if not all_users:
        logging.warning("No user emails found. Is your database populated?")
    else:
        logging.info(f"Attempting to send emails to: {all_users}")

    for emp in all_users:
        email = emp.get("email")
        emp_name = emp.get("username") or "Employee"

        if not email:
            logging.warning(f"No email found for user: {emp_name}")
            continue

        msg = Message(
            subject="📅 New Work Schedule Posted!",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = (
            f"Hi {emp_name},\n\n"
            "A new work schedule has been posted. Please log into WorkSync to view your shifts.\n\n"
            "Best,\nWorkSync Team"
        )

        try:
            mail.send(msg)
            logging.info(f"✅ Email successfully sent to {email}")
        except Exception as e:
            logging.error(f"❌ Failed to send email to {email}: {e}")

    return jsonify({"message": "Schedule posted and emails sent!"})



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
    date = data.get("date")
    availability = data.get("availability")  # e.g., "9 AM - 5 PM"

    if name and date and availability:
        try:
            success = database.add_availability(name, date, availability)
            if success:
                return jsonify({"message": "Availability submitted!"})
            else:
                return jsonify({"error": "Failed to add availability"}), 500
        except Exception as e:
            app.logger.error(f"Error adding availability: {e}")
            return jsonify({"error": "Server error"}), 500

    return jsonify({"error": "Missing name, date, or availability"}), 400


@app.route("/all_availabilities", methods=["GET"])
def all_availabilities():
    if "role" not in session or session["role"] != "owner":
        return jsonify({"error": "Unauthorized"}), 403
    
    availabilities = database.get_availabilities()
    print("📦 DEBUG: Returning availabilities from DB:", availabilities)  # ← Add this line
    return jsonify({"availabilities": availabilities})

@app.route("/delete_availability", methods=["POST"])
def delete_availability():
    if "role" not in session or session["role"] != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    name = data.get("name")
    availability = data.get("availability")
    date = data.get("date")  # ✅ Include date

    if not name or not availability or not date:
        return jsonify({"error": "Missing data"}), 400

    success = database.delete_availability(name, availability, date)
    return jsonify({"success": success})




@app.route("/request_swap", methods=["POST"])
def request_swap():
    data = request.get_json()
    from_user = data.get("from_user")
    to_user = data.get("to_user")
    availability = data.get("availability")
    date = data.get("date")  # 🧠 From frontend, expected as string: 'YYYY-MM-DD'

    if not from_user or not to_user or not availability or not date:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # ✅ Convert string to actual date object
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()

        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🚫 Check for duplicate pending request
        cursor.execute("""
            SELECT * FROM swap_requests
            WHERE from_user = %s AND to_user = %s AND availability = %s AND date = %s AND status = 'pending'
        """, (from_user, to_user, availability, parsed_date))

        if cursor.fetchone():
            return jsonify({"error": "Swap request already sent."}), 400

        # ✅ Insert the new swap request
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO swap_requests (from_user, to_user, availability, date)
            VALUES (%s, %s, %s, %s)
        """, (from_user, to_user, availability, parsed_date))

        conn.commit()
        return jsonify({"message": "Swap request sent!"})

    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    except Exception as e:
        print(f"❌ Error requesting swap: {e}")
        return jsonify({"error": "Failed to request swap"}), 500

    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()






@app.route("/respond_swap", methods=["POST"])
def respond_swap():
    data = request.get_json()
    request_id = data.get("id")
    decision = data.get("decision")  # 'accepted' or 'rejected'

    if not request_id or decision not in ["accepted", "rejected"]:
        return jsonify({"error": "Invalid request data"}), 400

    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔍 Fetch original request
        cursor.execute("SELECT * FROM swap_requests WHERE id = %s", (request_id,))
        swap = cursor.fetchone()

        if not swap:
            return jsonify({"error": "Swap request not found"}), 404

        if decision == "accepted":
            from_user = swap["from_user"]
            to_user = swap["to_user"]
            availability = swap["availability"]
            date = swap["date"]

            print("📦 SWAP DEBUG:")
            print(f"From: {from_user}, To: {to_user}")
            print(f"Availability: {availability}")
            print(f"Date: {date} ({type(date)})")

            # 🧠 Overlap check
            cursor.execute("""
                SELECT availability FROM posted_schedule
                WHERE name = %s AND date = %s
            """, (to_user, date))
            existing_shifts = cursor.fetchall()

            def shifts_overlap(existing_shift, new_shift):
                def parse_range(time_range):
                    start_str, end_str = time_range.split(" - ")
                    return datetime.strptime(start_str.strip(), "%I %p").time(), datetime.strptime(end_str.strip(), "%I %p").time()

                existing_start, existing_end = parse_range(existing_shift)
                new_start, new_end = parse_range(new_shift)
                return max(existing_start, new_start) < min(existing_end, new_end)

            for shift in existing_shifts:
                if shifts_overlap(shift["availability"], availability):
                    return jsonify({
                        "error": f"{to_user} already has a conflicting shift on {date}."
                    }), 400

            # 🔁 Update availabilities
            database.delete_availability(from_user, availability, date)
            database.add_availability(to_user, availability, date)

            # ✅ Update posted_schedule
            cursor.execute("""
                UPDATE posted_schedule
                SET name = %s, is_swapped = TRUE
                WHERE name = %s AND availability = %s AND date = %s
            """, (to_user, from_user, availability, date))

            # ✅ Email both parties
            from_user_email = database.get_user_by_username(from_user)["email"]
            to_user_email = database.get_user_by_username(to_user)["email"]

            msg = Message("Shift Swap Accepted",
                          recipients=[from_user_email, to_user_email])
            msg.body = f"""
Your shift swap has been accepted!

Shift Details:
📅 Date: {date}
⏰ Time: {availability}
🔁 New Owner: {to_user}

- Work Sync LMS
"""
            mail.send(msg)

        # ✅ Update request status
        cursor.execute("UPDATE swap_requests SET status = %s WHERE id = %s", (decision, request_id))
        conn.commit()

        return jsonify({"message": f"Swap request {decision}!"})

    except Exception as e:
        print("❌ Error responding to swap request:")
        traceback.print_exc()
        return jsonify({"error": "Failed to respond to swap request"}), 500

    finally:
        cursor.close()
        conn.close()





@app.route("/get_swap_requests")
def get_swap_requests():
    to_user = request.args.get("username")
    from_user = request.args.get("from_user")

    try:
        conn = database.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if to_user:
            cursor.execute("""
                SELECT * FROM swap_requests
                WHERE to_user = %s AND status = 'pending'
            """, (to_user,))
        elif from_user:
            cursor.execute("""
                SELECT * FROM swap_requests
                WHERE from_user = %s AND status = 'pending'
            """, (from_user,))
        else:
            return jsonify({"error": "Missing parameters"}), 400

        results = cursor.fetchall()
        return jsonify(results)
    except Exception as e:
        print(f"Error fetching swap requests: {e}")
        return jsonify({"error": "Failed to fetch swap requests"}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/all_usernames")
def all_usernames():
    users = database.get_all_usernames()
    return jsonify({"usernames": users})

@app.route("/debug_schedule", methods=["GET"])
def debug_schedule():
    return jsonify(database.get_posted_schedule())

@app.route("/pending_users")
def pending_users():
    if session.get("role") != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    conn = database.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT username, email FROM users 
            WHERE is_approved = FALSE AND role = 'employee'
        """)
        users = cursor.fetchall()
        return jsonify({"users": users})
    finally:
        cursor.close()
        conn.close()



@app.route("/approve_user/<username>", methods=["POST"])
def approve_user(username):
    if session.get("role") != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    conn = database.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE users SET is_approved = TRUE WHERE username = %s", (username,))
        conn.commit()
        return jsonify({"message": f"User {username} approved!"})
    finally:
        cursor.close()
        conn.close()

@app.route("/reject_user/<username>", methods=["POST"])
def reject_user(username):
    if session.get("role") != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()

        # 🛡️ Only reject if the user is unapproved & an employee
        cursor.execute("""
            DELETE FROM users 
            WHERE username = %s AND is_approved = FALSE AND role = 'employee'
        """, (username,))
        
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "User not found or already approved"}), 404

        return jsonify({"message": f"User {username} rejected and removed."})
    except Exception as e:
        print(f"❌ Error rejecting user {username}: {e}")
        return jsonify({"error": "Failed to reject user"}), 500
    finally:
        cursor.close()
        conn.close()




if __name__ == "__main__":
    database.create_tables()
    app.run(debug=True)
