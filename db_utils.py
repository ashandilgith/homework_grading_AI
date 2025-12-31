import os
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pg8000

# Global pool variable to reuse connections
pool = None

def init_connection_pool():
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
                ip_type=IPTypes.PUBLIC
            )
            return conn

        pool = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )
    return pool

def get_db_connection():
    if pool is None:
        init_connection_pool()
    return pool.connect()

# --- UPDATED FUNCTION ---
def save_grade(tutor_name, filename, score, feedback, file_url, tokens_used=0):
    """Saves the grading result AND the token usage."""
    if pool is None:
        init_connection_pool()
    
    with pool.connect() as db_conn:
        # We assume the table already exists (created by reset_db.py)
        
        # Insert data with Tokens
        stmt = sqlalchemy.text(
            """INSERT INTO grading_logs 
               (username, filename, score, feedback, file_url, tokens_used) 
               VALUES (:u, :f, :s, :fb, :url, :tok)"""
        )
        db_conn.execute(stmt, parameters={
            "u": tutor_name, 
            "f": filename, 
            "s": score, 
            "fb": feedback, 
            "url": file_url,
            "tok": tokens_used
        })
        db_conn.commit()

def get_tutor_usage(username):
    """Returns the total tokens used by a specific tutor."""
    if pool is None:
        init_connection_pool()
        
    with pool.connect() as db_conn:
        # Sum the 'tokens_used' column for this user
        result = db_conn.execute(sqlalchemy.text(
            "SELECT SUM(tokens_used) FROM grading_logs WHERE username = :u"
        ), {"u": username}).fetchone()
        
        # If they haven't graded anything yet, result is None -> return 0
        total_used = result[0] if result and result[0] else 0
        return int(total_used)