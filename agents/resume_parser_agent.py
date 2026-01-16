import fitz  # PyMuPDF
from openai import OpenAI
import json

# Blank Schema
SCHEMA_TEMPLATE = {
    "basics": {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "github": ""
    },
    "education": [
        {
            "institution": "",
            "area": "",
            "studyType": "",
            "startDate": "",
            "endDate": "",
            "courses": []
        }
    ],
    "experience": [
        {
            "company": "",
            "position": "",
            "startDate": "",
            "endDate": "",
            "location": "",
            "bullets": []
        }
    ],
    "projects": [
        {
            "name": "",
            "technologies": [],
            "bullets": []
        }
    ],
    "skills": {
        "languages": [],
        "frameworks": [],
        "tools": []
    }
}

def extract_text_from_pdf(file_stream):
    """Extracts raw text from a PDF file stream."""
    try:
        doc = fitz.open(stream=file_stream.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def parse_resume_to_json(file_stream, openai_api_key):
    if not openai_api_key:
        raise ValueError("OpenAI API Key is missing.")

    # 1. Get Text
    raw_text = extract_text_from_pdf(file_stream)
    
    if not raw_text or len(raw_text) < 50:
        raise ValueError("Could not extract text from PDF. It might be an image scan.")

    # 2. Prepare Client
    client = OpenAI(api_key=openai_api_key)
    
    # 3. Construct Prompt (UPDATED TO PREVENT SUMMARIZATION)
    system_prompt = f"""
    You are an expert Data Extraction Agent.
    Your goal is to extract information from the Candidate's Resume text EXACTLY AS IT APPEARS.
    
    CRITICAL RULES:
    1. **DO NOT SUMMARIZE.** Copy the bullet points exactly as they are in the text.
    2. **DO NOT SIMPLIFY.** If a bullet point is long, keep it long.
    3. **DO NOT OMIT DETAILS.** Include metrics, numbers, and technical keywords exactly as written.
    4. Fix only broken newlines (e.g., if a sentence is split across two lines in the PDF, join it).
    5. If a field is missing (e.g., GitHub), leave it as an empty string "" or [].
    6. Format dates as "MMM YYYY" (e.g., "Sep 2023").
    
    TARGET JSON STRUCTURE:
    {json.dumps(SCHEMA_TEMPLATE, indent=2)}
    """

    # 4. Call LLM
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the resume text:\n\n{raw_text}"}
        ],
        response_format={"type": "json_object"}
    )

    # 5. Parse Response
    try:
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        raise Exception(f"Failed to parse LLM response: {e}")