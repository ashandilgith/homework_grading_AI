import streamlit as st
import os
import pandas as pd
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()
import db_utils
import storage_utils
import grader_engine

st.set_page_config(page_title="Iskole 🏫", layout="wide")
st.title("Iskole 🏫")
st.subheader("Automated Homework Grading System")

# --- Helper: PDF Generator ---
def create_pdf_report(feedback_text, student_filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt=f"Grading Report: {student_filename}", ln=1, align="C")
    pdf.ln(10)
    
    # Simple clean up for PDF compatibility
    pdf.set_font("Arial", size=11)
    safe_text = feedback_text.encode('latin-1', 'replace').decode('latin-1')
    
    # Handle line breaks better for the AI's markdown
    for line in safe_text.split('\n'):
        pdf.multi_cell(0, 6, txt=line)
        
    report_filename = f"Report_{student_filename}.pdf"
    pdf.output(report_filename)
    return report_filename

# --- Sidebar ---
with st.sidebar:
    st.header("Grading Settings")
    tutor_name = st.text_input("Tutor Username", value="test_tutor")
    
    # 1. ALWAYS required: Marking Scheme
    uploaded_scheme = st.file_uploader("Upload Marking Scheme (PDF)", type=["pdf"])
    
    # 2. TOGGLE: Choose Style
    st.write("---")
    st.write("**Report Style:**")
    style_choice = st.radio(
        "Choose format source:",
        ("Use Standard AI Format", "Upload Custom Template")
    )
    
    uploaded_template = None
    if style_choice == "Upload Custom Template":
        uploaded_template = st.file_uploader("Upload Report Template (PDF)", type=["pdf"])
    else:
        st.info("Using built-in professional layout.")

# --- Main Area ---
st.write("### Upload Student Papers")
uploaded_files = st.file_uploader("Drag and drop student PDFs here", 
                                  accept_multiple_files=True, 
                                  type=["pdf", "png", "jpg", "jpeg"])

if st.button("Run Batch Grading"):
    # Check requirements based on mode
    ready_to_go = False
    if not uploaded_files or not uploaded_scheme:
         st.error("Missing Student Paper or Marking Scheme.")
    elif style_choice == "Upload Custom Template" and not uploaded_template:
         st.error("You selected 'Custom Template' but didn't upload one!")
    else:
        ready_to_go = True

    if ready_to_go:
        st.info("Starting Grading Process...")
        
        # Save Scheme
        with open("temp_scheme.pdf", "wb") as f:
            f.write(uploaded_scheme.getbuffer())
        
        # Save Template (If exists)
        template_path = None
        if uploaded_template:
            with open("temp_template.pdf", "wb") as f:
                f.write(uploaded_template.getbuffer())
            template_path = "temp_template.pdf"

        progress_bar = st.progress(0)
        
        for i, student_file in enumerate(uploaded_files):
            file_ext = student_file.name.split('.')[-1]
            temp_filename = f"temp_student.{file_ext}"
            with open(temp_filename, "wb") as f:
                f.write(student_file.getbuffer())
            
            try:
                # --- CALL ENGINE ---
                # Pass 'None' if we are using Standard Format
                score, feedback = grader_engine.grade_submission(
                    temp_filename, 
                    "temp_scheme.pdf", 
                    template_path 
                )
                
                # Generate PDF & Upload
                report_pdf = create_pdf_report(feedback, student_file.name)
                student_url = storage_utils.upload_file(student_file, student_file.name)
                
                # Save DB
                db_utils.save_grade(tutor_name, student_file.name, score, feedback, student_url)
                
                # Success
                st.success(f"Graded: {student_file.name} | Score: {score}")
                with open(report_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download Report (PDF)",
                        data=pdf_file,
                        file_name=report_pdf,
                        mime="application/pdf"
                    )
                with st.expander("View Raw Feedback"):
                    st.write(feedback)
                st.markdown("---")
                
            except Exception as e:
                st.error(f"Error grading {student_file.name}: {str(e)}")

            progress_bar.progress((i + 1) / len(uploaded_files))
            
# --- Dashboard ---
st.write("### 📊 Business Logs")
try:
    conn = db_utils.get_db_connection()
    query = f"SELECT * FROM grading_logs WHERE username = '{tutor_name}' ORDER BY timestamp DESC"
    df = pd.read_sql(query, conn)
    st.dataframe(df)
    conn.close()
except:
    pass