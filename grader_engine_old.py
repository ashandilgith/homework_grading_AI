import google.generativeai as genai
import os
import time
import re

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def upload_to_gemini(path, mime_type="application/pdf"):
    file = genai.upload_file(path, mime_type=mime_type)
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = genai.get_file(file.name)
    return file

def grade_submission(student_file_path, scheme_file_path, report_template_path=None, max_score_override=0):
    # Use Gemini 3 Flash (or Pro if you prefer)
    model = genai.GenerativeModel("gemini-3-flash-preview")
    #model = genai.GenerativeModel("gemini-2.0-flash-exp")
    #model = genai.GenerativeModel("gemini-1.5-pro")
    #model = genai.GenerativeModel("gemini-3-pro-preview")
    #model = genai.GenerativeModel("gemini-pro-latest")

    student_pdf = upload_to_gemini(student_file_path)
    scheme_pdf = upload_to_gemini(scheme_file_path)
    
    files_to_send = [student_pdf, scheme_pdf]
    
    # --- SMART DENOMINATOR LOGIC ---
    if max_score_override > 0:
        # Case A: User gave us the number (e.g. 120)
        max_score_text = f"The user has specified the Total Marks for this paper is: {max_score_override}."
    else:
        # Case B: Auto-detect (The Fix)
        max_score_text = """
        TASK: Determine the 'Total Marks' for this exam paper.
        
        ⚠️ CRITICAL WARNING: The Marking Scheme likely contains MORE questions than a student is required to answer (e.g., Optional Sections).
        
        RULES FOR TOTAL SCORE:
        1. Look for exam instructions like "Answer Section A and TWO questions from Section B".
        2. Do NOT simply sum every number in the document (which would result in 200+).
        3. Calculate the valid maximum score for a SINGLE student based on the required question count (typically 100 or 120).
        4. Use this valid maximum as the denominator.
        """

    base_prompt = f"""
    You are a strict academic grader.
    INPUTS: 1. Student Paper 2. Marking Scheme
    
    CONTEXT: {max_score_text}
    
    TASK:
    1. Grade strictly against the Marking Scheme.
    2. List the questions the student attempted.
    3. **CRITICAL FOR UNATTEMPTED QUESTIONS:**
       - Only list unattempted questions IF they were COMPULSORY or necessary to make up the full paper total.
       - If the student skipped an *optional* question that they didn't need to answer, do not penalize them or list it as "Unattempted".
       - If they simply skipped a required question, mark it "Status: UNATTEMPTED" and briefly explain the missing content.
    
    OUTPUT FORMAT (Strict Markdown List):
    
    # Grading Report
    **Student:** [Name]
    **Date:** [Today's Date]
    **Score:** [Your Calculated Total] / [The Valid Max Score] ([Percentage]%)
    
    ## Performance Summary
    [2-3 sentences summary]
    
    ## Detailed Question Analysis
    
    **Q1**
    * **Score:** [X]/[Y]
    * **Status:** [Correct/Partial/Incorrect/Unattempted]
    * **Feedback:** [Specific feedback]
    
    (Repeat for other questions)
    
    ## Recommendations
    * [Bulleted advice]
    
    --------------------------------------------------
    INTERNAL DATA:
    SCORE: [Insert Total Integer Score]
    """

    if report_template_path:
        files_to_send.append(upload_to_gemini(report_template_path))
        base_prompt += "\nNOTE: Follow the TONE of the provided Style Guide, but use the structure above."

    files_to_send.insert(0, base_prompt)
    
    response = model.generate_content(files_to_send)
    full_text = response.text
    
    tokens = response.usage_metadata.total_token_count

    # Extract Score
    score_match = re.search(r"SCORE:\s*(\d+)", full_text)
    if score_match:
        score = int(score_match.group(1))
        feedback_report = full_text.replace(score_match.group(0), "").strip()
        feedback_report = feedback_report.replace("INTERNAL DATA:", "").strip()
    else:
        score = 0
        feedback_report = full_text

    return score, feedback_report, tokens