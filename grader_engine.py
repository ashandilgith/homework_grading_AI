import google.generativeai as genai
import os
import time
import re

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def upload_to_gemini(path, mime_type="application/pdf"):
    """Uploads file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = genai.get_file(file.name)
    return file

def grade_submission(student_file_path, scheme_file_path, report_template_path=None):
    """
    Grades paper. If report_template_path is None, uses internal Standard Format.
    """
    # Use your working model
    model = genai.GenerativeModel("gemini-3-flash-preview")
    # OR: model = genai.GenerativeModel("gemini-1.5-pro")

    # 1. Upload Mandatory Files
    student_pdf = upload_to_gemini(student_file_path)
    scheme_pdf = upload_to_gemini(scheme_file_path)
    
    # 2. Prepare Inputs
    files_to_send = [student_pdf, scheme_pdf]
    
    if report_template_path:
        # --- OPTION A: CUSTOM TEMPLATE ---
        template_pdf = upload_to_gemini(report_template_path)
        files_to_send.append(template_pdf)
        
        prompt = """
        You are a strict academic grader.
        INPUTS: 1. Student Paper 2. Marking Scheme 3. STYLE GUIDE (PDF)
        
        TASK:
        1. Grade the student paper strictly against the Marking Scheme.
        2. Format your report to visually match the STYLE GUIDE (headers, order).
        3. **CRITICAL:** Do NOT copy text/numbers from the Style Guide. Use YOUR calculated scores and YOUR feedback.
        
        OUTPUT FORMAT:
        Line 1: SCORE: [Integer Total]
        Line 2+: [Your Grading Report]
        """
    else:
        # --- OPTION B: STANDARD AI FORMAT (Clean & Structured) ---
        prompt = """
        You are a strict academic grader.
        INPUTS: 1. Student Paper 2. Marking Scheme
        
        TASK:
        1. Grade the student paper strictly against the Marking Scheme.
        2. Create a clean, professional Grading Report.
        
        **REQUIRED STANDARD FORMAT:**
        
        # Grading Report
        **Student:** [Student Name]
        **Subject:** [Subject Name]
        **Date:** [Current Date]
        
        ## Performance Summary
        [Write a 2-3 sentence summary of overall performance]
        
        ## Question Analysis
        | Question | Score | Status | Feedback |
        | :--- | :--- | :--- | :--- |
        | Q1 | [X]/[Y] | Correct/Partial/Incorrect | [Specific feedback] |
        | Q2 | [X]/[Y] | ... | ... |
        
        ## Recommendations
        * [Bulleted list of study tips based on mistakes]
        
        OUTPUT FORMAT:
        Line 1: SCORE: [Integer Total]
        Line 2+: [The Report in the format above]
        """

    # 3. Generate
    files_to_send.insert(0, prompt) # Put prompt first
    response = model.generate_content(files_to_send)
    full_text = response.text

    # 4. Extract Score
    score_match = re.search(r"SCORE:\s*(\d+)", full_text)
    if score_match:
        score = int(score_match.group(1))
        feedback_report = full_text.replace(score_match.group(0), "").strip()
    else:
        score = 0
        feedback_report = full_text

    return score, feedback_report