import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables (Make sure you have a .env file)
load_dotenv()

# AWS RDS MySQL Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "moodle-db.cpcq6082ccyg.us-east-1.rds.amazonaws.com"),  # AWS RDS Endpoint
    "user": os.getenv("DB_USER", "admin"),  # MySQL username
    "password": os.getenv("DB_PASSWORD", "your-password"),  # MySQL password
    "database": os.getenv("DB_NAME", "schedule_db")  # The new database we created
}

# Function to establish a database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

# Function to create tables if they don't exist
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
            conn.commit()
            print("✅ Table 'availabilities' ensured")
        except Error as e:
            print(f"❌ Error creating table: {e}")
        finally:
            cursor.close()
            conn.close()

# Function to add availability
def add_availability(name, availability):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            sql = "INSERT INTO availabilities (name, availability) VALUES (%s, %s)"
            cursor.execute(sql, (name, availability))
            conn.commit()
            return True
        except Error as e:
            print(f"❌ Error inserting availability: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

# Function to get all availabilities
def get_availabilities():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM availabilities")
            result = cursor.fetchall()
            return result
        except Error as e:
            print(f"❌ Error fetching availabilities: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []

# Run table creation when the file is executed
if __name__ == "__main__":
    create_tables()
    
    # Test inserting data
    success = add_availability("John Doe", "Monday 9 AM - 5 PM")
    if success:
        print("✅ Successfully added availability!")
    
    # Test fetching data
    records = get_availabilities()
    print("📋 Availabilities in DB:", records)
