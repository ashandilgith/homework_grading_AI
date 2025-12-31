import sqlalchemy
import os
from dotenv import load_dotenv  # <--- This was missing!

# 1. Load the secrets from .env
load_dotenv()

from db_utils import init_connection_pool

print("Connecting to database...")
pool = init_connection_pool()

with pool.connect() as db_conn:
    # 2. Drop the old table
    print("Dropping old table...")
    db_conn.execute(sqlalchemy.text("DROP TABLE IF EXISTS grading_logs;"))
    db_conn.commit()
    print("Old table dropped successfully!")
    
    # 3. Create the new table (with the 'filename' column)
    print("Creating new table schema...")
    db_conn.execute(sqlalchemy.text(
        """CREATE TABLE IF NOT EXISTS grading_logs (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50),
            filename VARCHAR(255),
            score INT,
            feedback TEXT,
            file_url TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""
    ))
    db_conn.commit()
    print("New table created successfully!")