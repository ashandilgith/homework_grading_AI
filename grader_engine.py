import google.generativeai as genai
import os
import time

# Configure the API
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

def upload_to_gemini(path, mime_type="application/pdf"):
    """Uploads the file to Gemini's file storage."""
    file = genai.upload_file(path, mime_type=mime_type)
    # Wait for the file to be processed (usually instant for small files)
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = genai.get_file(file.name)
    return file

def grade_submission(student_file_path, scheme_file_path, report_template_path):
    """
    Sends the Student Paper, Marking Scheme, and Report Template 
    (all PDFs) to Gemini for grading.
    """
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    # 1. Upload the files to Gemini
    student_pdf = upload_to_gemini(student_file_path, mime_type="application/pdf")
    scheme_pdf = upload_to_gemini(scheme_file_path, mime_type="application/pdf")
    
    # Handle report template (it might be text or PDF, let's assume PDF for now)
    template_pdf = upload_to_gemini(report_template_path, mime_type="application/pdf")

    # 2. Create the Prompt
    prompt = """
    You are an expert academic grader. 
    I have provided three documents:
    1. The Student's Submission (Handwritten or Digital).
    2. The Marking Scheme / Answer Key.
    3. The Report Template (Style Guide).

    YOUR TASK:
    - Grade the student's submission STRICTLY according to the Marking Scheme.
    - Check for every single question. If the student skipped it, mark it as 0.
    - Output the final feedback report following the structure and tone of the Report Template exactly.
    - The final output must be ONLY the report text. Do not add "Here is the report:"
    """

    # 3. Generate Content (Pass all 3 files + prompt)
    response = model.generate_content([prompt, student_pdf, scheme_pdf, template_pdf])
    
    return response.text