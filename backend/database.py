import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# Use absolute path to ensure database and files are in backend directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "elixir_healthcare.db")
FILES_DIR = os.path.join(BASE_DIR, "uploaded_files")

# Ensure files directory exists
os.makedirs(FILES_DIR, exist_ok=True)

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with all tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Period tracker table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            date DATE NOT NULL,
            flow_level TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    """)
    
    # Medications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    """)
    
    # Reports table (Blood tests, X-rays, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            report_type TEXT NOT NULL,
            report_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    """)
    
    # Health status table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            overall_health TEXT,
            last_checkup DATE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email),
            UNIQUE(user_email)
        )
    """)
    
    # Portfolio form data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            initials TEXT,
            age TEXT,
            gender TEXT,
            insurance TEXT,
            living TEXT,
            drug_allergies TEXT,
            env_allergies TEXT,
            adr TEXT,
            chief_complaint TEXT,
            history_illness TEXT,
            past_medical TEXT,
            family_history TEXT,
            tobacco INTEGER DEFAULT 0,
            tobacco_details TEXT,
            alcohol INTEGER DEFAULT 0,
            alcohol_details TEXT,
            caffeine INTEGER DEFAULT 0,
            caffeine_details TEXT,
            recreation INTEGER DEFAULT 0,
            recreation_details TEXT,
            immunization_comments TEXT,
            medications TEXT,
            antibiotics TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email),
            UNIQUE(user_email)
        )
    """)
    
    # Portfolio documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    """)
    
    # File summaries table - create if not exists (don't drop to preserve data)
    # Each upload will create a new row even if the same file name is used
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            file_name TEXT NOT NULL,
            file_summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if user_email column allows NULL (schema migration check)
    cursor.execute("PRAGMA table_info(file_summaries)")
    columns = {col[1]: col for col in cursor.fetchall()}
    
    # If user_email doesn't exist or doesn't allow NULL, we need to handle it
    # But since we're using CREATE TABLE IF NOT EXISTS, we can't modify schema easily
    # So we'll ensure the table structure is correct by checking
    
    conn.commit()
    
    # Create default users
    default_users = [
        ("person1@gmail.com", "123"),
        ("person2@gmail.com", "123"),
        ("person3@gmail.com", "123"),
        ("person4@gmail.com", "123"),
    ]
    
    for email, password in default_users:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (email, password) VALUES (?, ?)",
                (email, password)
            )
        except:
            pass
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Initialize database on import
init_db()