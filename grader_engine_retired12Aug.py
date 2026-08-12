#this grader engine is specifically for google cloud. Retired for local version. 
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
    # 1. MODEL SELECTION
    model = genai.GenerativeModel("gemini-2.5-pro")

    # 2. Upload Files
    student_pdf = upload_to_gemini(student_file_path)
    scheme_pdf = upload_to_gemini(scheme_file_path)
    
    files_to_send = [student_pdf, scheme_pdf]
    
    # --- STYLE GUIDE ---
    style_instruction = ""
    if report_template_path:
        template_pdf = upload_to_gemini(report_template_path)
        files_to_send.append(template_pdf)
        style_instruction = "IMPORTANT: Adopt the TONE and STYLE of the provided 'Style Guide' PDF."

    # --- DENOMINATOR LOGIC ---
    if int(max_score_override) > 0:
        max_score_instr = f"The total maximum marks for this paper is EXPLICITLY: {max_score_override}. Use this as the denominator."
    else:
        max_score_instr = "Detect the max marks. If optional questions exist, calculate only what a single student can attempt."

    # 3. REVISED PROMPT
    prompt = f"""
    You are an expert academic examiner and strict Teaching Assistant.

    INPUTS:
    1. Student Submission
    2. Marking Scheme
    3. Style Guide (Optional)

    {max_score_instr}
    {style_instruction}

    GRADING LOGIC (MANDATORY):

    Follow these steps EXACTLY:

    1. Identify the student name.
       - If not found, return "Unknown Student".

    2. Determine the correct total maximum marks:
       - Use explicit value if given.
       - Otherwise infer from marking scheme.
       - If optional questions exist, calculate only what a single student can attempt.
       - Calculate total maximum based on all mandatory questions (or where optional questions exist, the minimal mandatory) not just on questions attempted.

    3. Decompose the paper:
       - Break into ALL questions and sub-questions (e.g., 1a, 1b, 2c).
       - DO NOT skip any.

    4. Grade EACH question independently:
       For every question:
       - Compare strictly with marking scheme
       - Assign:
            score (numeric)
            max (numeric)
            status:
                "CORRECT" = full marks
                "PARTIAL" = some marks
                "INCORRECT" = wrong answer
                "UNATTEMPTED" = no answer - ensure to mark unattempted questions as unattempted.
       - Provide a SHORT justification explaining WHY marks were awarded or lost

    5. Consistency rules:
       - NEVER award marks without justification
       - NEVER exceed max marks
       - Be strict (do not assume correct intent if not shown)
       - If unclear answer → mark PARTIAL or INCORRECT with explanation

    6. After grading all questions:
       - Summarize:
            strengths (i.e. the areas of the subject the student seemed to have mastered in 3 to 5 lines)
            weaknesses (ie. which questions were unanswered, poorly answered or wrong, and any competency deficiency overlap, relevant observations in 3 to 5 lines)
            improvements (actionable)

    OUTPUT FORMAT (STRICT JSON ONLY):

    {{
        "student_name": "string",
        "questions": [
            {{
                "q": "Q1a",
                "score": number,
                "max": number,
                "status": "CORRECT | PARTIAL | INCORRECT | UNATTEMPTED",
                "reason": "short explanation"
            }}
        ],
        "summary": {{
            "strengths": "string",
            "weaknesses": "string",
            "improvements": "string"
        }}
    }}

    IMPORTANT:
    - DO NOT invent marks outside the scheme
    - DO NOT skip questions
    - DO NOT return anything outside JSON (No markdown blocks, no text outside the braces).
    """

    files_to_send.append(prompt)
    
    # 4. Generate
    response = model.generate_content(files_to_send)
    
    # 5. Parsing + Python Markdown Compilation
    try:
        text = response.text.strip()
        
        # Clean up any accidental markdown code blocks from the AI
        text = re.sub(r"^```json\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        
        data = json.loads(text.strip())
        
        # A. MATH CHECK
        calculated_score = sum(q.get('score', 0) for q in data.get('questions', []))
        
        # B. DENOMINATOR CHECK
        if int(max_score_override) > 0:
            final_max = int(max_score_override)
        else:
            final_max = sum(q.get('max', 0) for q in data.get('questions', []))

        # C. PYTHON-GENERATED READABLE REPORT
        student_name = data.get("student_name", "Unknown Student")
        
        # Build the formatted string line by line
        report_lines = [
            f"**Student Name:** {student_name}",
            "\n### Detailed Question Breakdown"
        ]
        
        for q in data.get("questions", []):
            report_lines.append(f"\n**Q{q.get('q', '?')}**")
            report_lines.append(f"Status: {q.get('status', 'N/A')}")
            report_lines.append(f"Score: {q.get('score', 0)} / {q.get('max', 0)}")
            report_lines.append(f"Feedback: {q.get('reason', '')}")
            
        summary = data.get("summary", {})
        report_lines.append("\n### Overall Performance Summary")
        report_lines.append(f"**Strengths:**\n{summary.get('strengths', 'None noted.')}\n")
        report_lines.append(f"**Weaknesses:**\n{summary.get('weaknesses', 'None noted.')}\n")
        report_lines.append(f"**Areas for Improvement:**\n{summary.get('improvements', 'None noted.')}")
        
        # Join it all together
        feedback_report = "\n".join(report_lines)

        # VERIFIED SCORE HEADER
        final_output_text = f"**VERIFIED SCORE:** {int(calculated_score)} / {final_max}\n\n" + feedback_report

        return int(calculated_score), final_output_text, response.usage_metadata.total_token_count

    except Exception as e:
        print(f"JSON Parsing failed: {e}")
        # If it fails, return the raw text so you can see what broke
        return 0, f"**Formatting Error.** Raw output:\n\n{response.text}", 0