import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

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
                availability TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
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
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()
            print("Tables ensured")
        except Error as e:
            print(f"Error creating table: {e}")
        finally:
            cursor.close()
            conn.close()

def add_availability(name, availability):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()

            # Avoid duplicate availability entries
            cursor.execute("SELECT * FROM availabilities WHERE name = %s AND availability = %s", (name, availability))
            if cursor.fetchone():
                print("Duplicate availability detected. Skipping insert.")
                return False

            cursor.execute("INSERT INTO availabilities (name, availability) VALUES (%s, %s)", (name, availability))
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
            return result
        except Error as e:
            print(f"Error fetching availabilities: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []

def add_user(username, password, role):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            conn.commit()
            return True
        except Error as e:
            print(f"Error adding user: {e}")
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
            cursor.execute("SELECT name, availability, date FROM posted_schedule")
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



if __name__ == "__main__":
    create_tables()
