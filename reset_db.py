import sqlalchemy
import os
from dotenv import load_dotenv

load_dotenv()
from db_utils import init_connection_pool

print("Connecting...")
pool = init_connection_pool()

with pool.connect() as db_conn:
    print("Resetting table...")
    db_conn.execute(sqlalchemy.text("DROP TABLE IF EXISTS grading_logs;"))
    db_conn.commit()
    
    # NEW SCHEMA: Added 'tokens_used' column
    print("Creating new schema with Token Tracking...")
    db_conn.execute(sqlalchemy.text(
        """CREATE TABLE IF NOT EXISTS grading_logs (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50),
            filename VARCHAR(255),
            score INT,
            feedback TEXT,
            file_url TEXT,
            tokens_used INT DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""
    ))
    db_conn.commit()
    print("Done! Database ready for analytics.")