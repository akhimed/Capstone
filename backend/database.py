import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "moodle-db.cpcq6082ccyg.us-east-1.rds.amazonaws.com"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "your-password"),
    "database": os.getenv("DB_NAME", "schedule_db")
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def create_tables():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS availabilities (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    date DATE NOT NULL,
                    availability TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (name) REFERENCES users(username) ON DELETE CASCADE
                )
            """)



            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role ENUM('owner', 'employee') NOT NULL
            )
            """)


            cursor.execute("""
            CREATE TABLE IF NOT EXISTS posted_schedule (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                availability TEXT NOT NULL,
                date DATE NOT NULL,
                is_swapped BOOLEAN DEFAULT FALSE,  -- ✅ ADD THIS LINE
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)


            cursor.execute("""
            CREATE TABLE IF NOT EXISTS swap_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                from_user VARCHAR(255),
                to_user VARCHAR(255),
                availability VARCHAR(255),
                date DATE,  -- ✅ Add this line
                status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)


            conn.commit()
            print("Tables ensured")
        except Error as e:
            print(f"Error creating table: {e}")
        finally:
            cursor.close()
            conn.close()

def add_availability(name, date, availability):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM availabilities
                WHERE name = %s AND date = %s AND availability = %s
            """, (name, date, availability))
            if cursor.fetchone():
                print("Duplicate availability detected. Skipping insert.")
                return False

            cursor.execute("""
                INSERT INTO availabilities (name, date, availability)
                VALUES (%s, %s, %s)
            """, (name, date, availability))
            conn.commit()
            return True
        except Error as e:
            print(f"Error saving availability: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False


def get_availabilities():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM availabilities")
            result = cursor.fetchall()

            # 🧼 Normalize date to ISO format for frontend (prevents "Invalid date" in JS)
            for a in result:
                if isinstance(a["date"], datetime.date):
                    a["date"] = a["date"].isoformat()

            print("📦 DEBUG: Returning availabilities from DB:", result)
            return result
        except Error as e:
            print(f"Error fetching availabilities: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []


def add_user(username, password, role, email, is_approved):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password, role, email, is_approved)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, password, role, email, is_approved))
            conn.commit()
            return True
        except Error as e:
            print(f"❌ Error adding user: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False




def get_user_by_username(username):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            return user
        except Error as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    return None

def save_schedule_entry(name, availability, date):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO posted_schedule (name, availability, date) VALUES (%s, %s, %s)", (name, availability, date))
            conn.commit()
            return True
        except Error as e:
            print(f"Error saving schedule: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False


def get_posted_schedule():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT name, availability, date, is_swapped FROM posted_schedule")
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching posted schedule: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []

def clear_posted_schedule():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM posted_schedule")  # <== this is the correct table!
            conn.commit()
        except Error as e:
            print(f"Error clearing posted schedule: {e}")
        finally:
            cursor.close()
            conn.close()



def save_posted_schedule(name, availability, date):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posted_schedule (name, availability, date)
                VALUES (%s, %s, %s)
            """, (name, availability, date))
            conn.commit()
            return True
        except Error as e:
            print(f"Error saving posted schedule: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

def delete_availability(name, availability, date):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM availabilities WHERE name = %s AND availability = %s AND date = %s",
                (name, availability, date)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"Error deleting availability: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False


def get_all_employee_emails():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, email FROM users WHERE role = 'employee'")
            result = cursor.fetchall()
            print("👀 Retrieved employee emails:", result)  # 👈 Add this for testing
            return result
        except Error as e:
            print(f"Error fetching employee emails: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []

def get_all_user_emails():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, email FROM users")
            result = cursor.fetchall()
            print("📧 All users (including owner):", result)  # 👀 DEBUG PRINT
            return result
        except Error as e:
            print(f"Error fetching all user emails: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []

def get_all_usernames():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users")
            return [row[0] for row in cursor.fetchall()]
        except Error as e:
            print(f"Error fetching usernames: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []


if __name__ == "__main__":
    create_tables()
