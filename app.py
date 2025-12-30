import streamlit as st
import os
import pandas as pd  # <--- FIXED: This was missing before!
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

import db_utils
import storage_utils
import grader_engine

# --- Page Config ---
st.set_page_config(page_title="Iskole", layout="wide")

st.title("Iskole")
st.subheader("Automated Homework Grading System")

# --- Sidebar ---
with st.sidebar:
    st.header("Grading Settings")
    tutor_name = st.text_input("Tutor Username", value="test_tutor")
    
    # 1. NEW: Upload Marking Scheme (PDF)
    uploaded_scheme = st.file_uploader("Upload Marking Scheme (PDF)", type=["pdf"])
    
    # 2. NEW: Upload Report Template (PDF)
    uploaded_template = st.file_uploader("Upload Report Template (PDF)", type=["pdf"])

# --- Main Area ---
st.write("### Upload Student Papers")
# 3. NEW: Allow PDF for students too
uploaded_files = st.file_uploader("Drag and drop student PDFs here", 
                                  accept_multiple_files=True, 
                                  type=["pdf", "png", "jpg", "jpeg"])

if st.button("Run Batch Grading"):
    if not uploaded_files:
        st.warning("Please upload student papers.")
    elif not uploaded_scheme:
        st.error("Please upload a Marking Scheme (PDF) in the sidebar.")
    elif not uploaded_template:
        st.error("Please upload a Report Template (PDF) in the sidebar.")
    else:
        st.info("Starting Grading Process... This may take a moment per file.")
        
        # Save Sidebar files temporarily
        with open("temp_scheme.pdf", "wb") as f:
            f.write(uploaded_scheme.getbuffer())
        with open("temp_template.pdf", "wb") as f:
            f.write(uploaded_template.getbuffer())

        progress_bar = st.progress(0)
        
        for i, student_file in enumerate(uploaded_files):
            # Save student file temporarily
            file_ext = student_file.name.split('.')[-1]
            temp_filename = f"temp_student.{file_ext}"
            
            with open(temp_filename, "wb") as f:
                f.write(student_file.getbuffer())
            
            # --- 1. Send to AI (Pass file paths) ---
            try:
                feedback = grader_engine.grade_submission(
                    temp_filename, 
                    "temp_scheme.pdf", 
                    "temp_template.pdf"
                )
                
                # --- 2. Save to Cloud ---
                # Upload PDF to Storage Bucket
                public_url = storage_utils.upload_file(student_file, student_file.name)
                
                # Save Result to DB
                db_utils.save_grade(tutor_name, student_file.name, 99, feedback, public_url)
                
                st.success(f"Graded: {student_file.name}")
                st.write(feedback)
                st.markdown("---")
                
            except Exception as e:
                st.error(f"Error grading {student_file.name}: {str(e)}")

            progress_bar.progress((i + 1) / len(uploaded_files))

# --- Dashboard View (The Table) ---
st.write("### 📊 Business Logs (Live Database)")
try:
    # Get connection
    conn = db_utils.get_db_connection()
    
    # Fetch Data
    query = f"SELECT * FROM grading_logs WHERE username = '{tutor_name}' ORDER BY timestamp DESC"
    df = pd.read_sql(query, conn)  # This will work now because we imported pd!
    
    st.dataframe(df)
    conn.close()
    
except Exception as e:
    st.error(f"Database Error: {e}")