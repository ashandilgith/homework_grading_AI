import google.generativeai as genai
import os
import time
import re
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def upload_to_gemini(path, mime_type="application/pdf"):
    """Uploads the given file to Gemini and waits for processing."""
    file = genai.upload_file(path, mime_type=mime_type)
    
    while file.state.name == "PROCESSING":
        time.sleep(1)
        file = genai.get_file(file.name)
        
    if file.state.name == "FAILED":
        raise ValueError(f"File {file.name} failed to process.")
        
    return file

def grade_submission(student_file_path, scheme_file_path, report_template_path=None, max_score_override=0):
    # 1. MODEL SELECTION: Using the latest Gemini 3 Flash Preview
    model = genai.GenerativeModel("gemini-3-flash-preview")

    # 2. Upload Files
    student_pdf = upload_to_gemini(student_file_path)
    scheme_pdf = upload_to_gemini(scheme_file_path)
    
    files_to_send = [student_pdf, scheme_pdf]
    
    # --- HANDLING THE STYLE GUIDE ---
    style_instruction = ""
    if report_template_path:
        template_pdf = upload_to_gemini(report_template_path)
        files_to_send.append(template_pdf)
        style_instruction = "IMPORTANT: Adopt the TONE and STYLE of the provided 'Style Guide' PDF (e.g. be encouraging, strict, or detailed as shown)."

    # --- DENOMINATOR LOGIC ---
    if int(max_score_override) > 0:
        max_score_instr = f"The total maximum marks for this paper is EXPLICITLY: {max_score_override}. Use this as the denominator."
    else:
        max_score_instr = "Detect the max marks. If there are optional sections, calculate the max for a single student (don't sum the whole paper)."

    # 3. The Hybrid Prompt
    prompt = f"""
    You are an expert academic examiner.
    
    INPUTS:
    1. Student Submission
    2. Marking Scheme
    3. Style Guide (Optional)
    
    {max_score_instr}
    {style_instruction}
    
    TASK:
    1. Grade strictly against the Marking Scheme.
    2. Write a detailed, rich feedback report.
    
    OUTPUT FORMAT:
    Return a pure JSON object.
    {{
        "student_name": "Name",
        "questions": [
            {{ "q": "Q1", "score": <float>, "max": <float> }},
            {{ "q": "Q2", "score": <float>, "max": <float> }}
        ],
        "rich_markdown_report": "# Grading Report\\n... (Put the entire human-readable report here, using Bold, Lists, and the requested Tone) ..."
    }}
    """

    files_to_send.append(prompt)
    
    # 4. Generate
    response = model.generate_content(files_to_send)
    
    # 5. Python Math Safety Net + Rich Text Extraction
    try:
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        
        data = json.loads(text.strip())
        
        # A. MATH CHECK (Python does the summing)
        calculated_score = sum(q['score'] for q in data.get('questions', []))
        
        # B. DENOMINATOR CHECK
        if int(max_score_override) > 0:
            final_max = int(max_score_override)
        else:
            final_max = sum(q['max'] for q in data.get('questions', []))

        # C. FEEDBACK EXTRACTION
        feedback_report = data.get("rich_markdown_report", "")
        
        if not feedback_report:
            feedback_report = f"# Grading Report\n**Score:** {calculated_score}/{final_max}\n\n## Feedback\n(Detailed feedback was not generated in the correct format.)"

        # Inject the VERIFIED SCORE header
        final_output_text = f"**VERIFIED SCORE:** {int(calculated_score)} / {final_max}\n\n" + feedback_report

        return int(calculated_score), final_output_text, response.usage_metadata.total_token_count

    except Exception as e:
        print(f"JSON Parsing failed: {e}")
        return 0, response.text, response.usage_metadata.total_token_count