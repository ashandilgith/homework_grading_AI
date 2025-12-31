import streamlit as st
import os
import pandas as pd
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()
import db_utils
import storage_utils
import grader_engine

st.set_page_config(page_title="Iskole", layout="wide")

# --- CUSTOM CSS FOR AESTHETICS ---
st.markdown("""
<style>
    /* 1. Force the whole app to have a dark background (fixes theme glitches) */
    .stApp {
        background-color: #0e1117;
    }

    /* 2. Fix the Tabs: Make them look like text links, not big buttons */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
        padding-bottom: 10px;
        border-bottom: 1px solid #262730; /* Subtle line under the whole menu */
    }

    .stTabs [data-baseweb="tab"] {
        height: auto;
        white-space: pre-wrap;
        background-color: transparent !important; /* Remove the white block */
        border-radius: 0px;
        border: none;
        color: #808495; /* Gray text for inactive tabs */
        font-size: 16px;
        font-weight: 600;
        padding: 10px 0px; /* Remove side padding to look like text */
    }

    /* 3. Active Tab Style: Bright White with Underline */
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #FFFFFF !important; /* Bright white when selected */
        border-bottom: 2px solid #FF4B4B; /* Red underline for active state */
    }
    
    /* 4. Hover Effect */
    .stTabs [data-baseweb="tab"]:hover {
        color: #FFFFFF; /* Brighten on hover */
    }
</style>
""", unsafe_allow_html=True)

st.title("Iskole Admin Portal")

# --- HELPER: IMPROVED PDF ---
class CleanReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Grading Report', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf_report(feedback_text, student_filename):
    pdf = CleanReport()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Sanitize text
    safe_text = feedback_text.encode('latin-1', 'replace').decode('latin-1')
    
    # Write text with nice spacing
    pdf.multi_cell(0, 7, txt=safe_text)
    
    report_filename = f"Report_{student_filename}.pdf"
    pdf.output(report_filename)
    return report_filename

# --- TABS LAYOUT ---
tab1, tab2, tab3 = st.tabs(["Grading Desk", "Tutor History", "Developer Dashboard"])

# ==========================
# TAB 1: GRADING DESK
# ==========================
# ==========================
# TAB 1: GRADING DESK
# ==========================
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Configuration")
        tutor_name = st.text_input("Tutor Username", value="test_tutor")
        uploaded_scheme = st.file_uploader("1. Marking Scheme (PDF)", type=["pdf"])
        
        # --- NEW: MAX SCORE INPUT ---
        st.write("**Exam Settings:**")
        max_score_input = st.number_input(
            "Total Marks (0 = Auto-detect)", 
            min_value=0, 
            value=120, 
            help="Set this to 120 for Section B only, or leave 0 to let AI guess."
        )
        # -----------------------------

        st.markdown("---")
        use_custom = st.checkbox("Use Custom Template?")
        uploaded_template = None
        if use_custom:
            uploaded_template = st.file_uploader("2. Report Template (PDF)", type=["pdf"])
    
    with col2:
        st.subheader("Student Uploads")
        uploaded_files = st.file_uploader("Drop student PDFs here", accept_multiple_files=True, type=["pdf"])

        if st.button("Run Batch Grading", type="primary"):
            if not uploaded_files or not uploaded_scheme:
                st.error("Please upload the Marking Scheme and Student Papers.")
            else:
                st.info("Processing... please wait.")
                
                # Save Temps
                with open("temp_scheme.pdf", "wb") as f:
                    f.write(uploaded_scheme.getbuffer())
                
                template_path = None
                if uploaded_template:
                    with open("temp_template.pdf", "wb") as f:
                        f.write(uploaded_template.getbuffer())
                    template_path = "temp_template.pdf"
                
                progress_bar = st.progress(0)
                
                for i, student_file in enumerate(uploaded_files):
                    # Save temp
                    with open("temp_student.pdf", "wb") as f:
                        f.write(student_file.getbuffer())
                    
                    # try:
                        # CALL ENGINE (Now returns 3 items)
                        #score, feedback, tokens = grader_engine.grade_submission(
                            #"temp_student.pdf", 
                            #"temp_scheme.pdf", 
                            #template_path
                        #)
                    
                    try:
                        # CALL ENGINE with MAX SCORE
                        score, feedback, tokens = grader_engine.grade_submission(
                            "temp_student.pdf", 
                            "temp_scheme.pdf", 
                            template_path,
                            max_score_override=max_score_input  # <--- PASS IT HERE
                        )
                        
                        # Generate PDF
                        pdf_path = create_pdf_report(feedback, student_file.name)
                        student_url = storage_utils.upload_file(student_file, student_file.name)
                        
                        # Save to DB (Now with tokens!)
                        # We need to update db_utils to accept tokens, 
                        # but for now we'll just save the basic info to avoid breaking db_utils
                        # (Ideally, update db_utils.save_grade to take 'tokens' arg)
                        
                        # QUICK HACK: We will execute the raw SQL here to support the new column
                        # until we update db_utils.py properly.
                        # Save to DB (Clean and Simple)
                        db_utils.save_grade(tutor_name, student_file.name, score, feedback, student_url, tokens)
                        
                        st.success(f"✅ {student_file.name} | Score: {score} | Tokens: {tokens}")
                        
                        with open(pdf_path, "rb") as pdf_file:
                            st.download_button(f"Download Report ({student_file.name})", pdf_file, file_name=pdf_path)
                            
                    except Exception as e:
                        st.error(f"Failed {student_file.name}: {e}")
                    
                    progress_bar.progress((i+1)/len(uploaded_files))

# ==========================
# TAB 2: TUTOR HISTORY
# ==========================
with tab2:
    st.subheader(f"Grading History: {tutor_name}")
    try:
        conn = db_utils.get_db_connection()
        # Show specific columns for cleanliness
        df = pd.read_sql(f"SELECT filename, score, tokens_used, timestamp, file_url FROM grading_logs WHERE username='{tutor_name}' ORDER BY timestamp DESC", conn)
        st.dataframe(df, use_container_width=True)
    except:
        st.warning("No data found.")

# ==========================
# TAB 3: DEVELOPER DASHBOARD (LOCKED)
# ==========================
with tab3:
    st.subheader("🛠️ System Health & Billing")
    
    # 1. THE GATEKEEPER
    # We check if the user knows the secret password from .env
    admin_password = st.text_input("Enter Admin Password", type="password")
    
    if admin_password == os.environ.get("ADMIN_PASS"):
        st.success("Access Granted")
        
        try:
            conn = db_utils.get_db_connection()
            # Analytics Queries
            total_papers = pd.read_sql("SELECT COUNT(*) FROM grading_logs", conn).iloc[0,0]
            total_tokens = pd.read_sql("SELECT SUM(tokens_used) FROM grading_logs", conn).iloc[0,0]
            
            # Fetch recent logs
            recent_logs = pd.read_sql("SELECT id, username, filename, tokens_used, timestamp FROM grading_logs ORDER BY timestamp DESC LIMIT 10", conn)
            
            if total_tokens is None: total_tokens = 0
            
            # Calculate Cost ($0.50 per 1M tokens approx for Flash)
            est_cost = (total_tokens / 1_000_000) * 0.50 
            
            # Display Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Papers Graded", total_papers)
            m2.metric("Total Tokens Used", f"{total_tokens:,}")
            m3.metric("Est. Cloud Cost", f"${est_cost:.4f}")
            
            st.write("### Global Recent Activity")
            st.dataframe(recent_logs, use_container_width=True)
            
        except Exception as e:
            st.error(f"Database Error: {e}")
            
    elif admin_password:
        st.error("Incorrect Password")
    else:
        st.info("Please enter the admin password to view sensitive metrics.")