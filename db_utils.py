import os
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pg8000

# Global pool variable to reuse connections
pool = None

def init_connection_pool():
    """Initializes the connection pool (The Engine)."""
    global pool
    if pool is None:
        instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]
        db_user = os.environ["DB_USER"]
        db_pass = os.environ["DB_PASS"]
        db_name = os.environ["DB_NAME"]

        connector = Connector()

        def getconn():
            conn = connector.connect(
                instance_connection_name,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name,
                ip_type=IPTypes.PUBLIC  # Crucial for Codespaces
            )
            return conn

        # Create the SQLAlchemy engine
        pool = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )
    return pool

def get_db_connection():
    """
    REQUIRED FUNCTION: Returns a raw connection for Pandas to use.
    This fixes the 'AttributeError' you were seeing.
    """
    if pool is None:
        init_connection_pool()
    return pool.connect()

def save_grade(tutor_name, filename, score, feedback, file_url):
    """Saves the grading result to Cloud SQL."""
    if pool is None:
        init_connection_pool()
    
    with pool.connect() as db_conn:
        # Create table if it doesn't exist
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

        # Insert data
        stmt = sqlalchemy.text(
            "INSERT INTO grading_logs (username, filename, score, feedback, file_url) VALUES (:u, :f, :s, :fb, :url)"
        )
        db_conn.execute(stmt, parameters={
            "u": tutor_name, 
            "f": filename, 
            "s": score, 
            "fb": feedback, 
            "url": file_url
        })
        db_conn.commit()