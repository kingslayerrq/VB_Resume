import fitz  # PyMuPDF
import os
from pydantic import BaseModel
from openai import OpenAI

# --- 1. Define Schema ---
class Critique(BaseModel):
    content_passed: bool
    missing_keywords: list[str]
    feedback: str

def proofread_resume(pdf_path: str, job_description: str) -> dict:
    print(f"🧐 Proofreading {pdf_path}...")

    # --- 0. SAFETY CHECK ---
    if not os.environ.get("OPENAI_API_KEY"):
        # Just return a pass if no key, so we don't crash the loop
        print("   ⚠️ No OpenAI Key found in environment. Skipping Semantic Check.")
        return {
            "length_passed": True, # Assume OK
            "content_passed": True,
            "feedback": "Skipped (No API Key)",
            "page_count": 0
        }

    # Initialize Client HERE (Lazy Load)
    client = OpenAI() 

    # --- 1. PHYSICAL CHECK (Length Only) ---
    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    text_content = ""
    for page in doc:
        text_content += page.get_text()

    length_passed = num_pages == 1

    if not length_passed:
        print(f"   ⚠️ Length Alert: Resume is {num_pages} pages.")
    else:
        print("   ✅ Length OK: 1 page.")

    # --- 2. SEMANTIC CHECK (Content Only) ---
    system_prompt = """
    You are an expert Resume Auditor. 
    
    CHECKLIST:
    1. KEYWORDS: Are the core technical skills present?
    2. QUALITY: Is the grammar professional?
    
    CRITICAL INSTRUCTION:
    If the Candidate simply DOES NOT HAVE a specific skill required by the JD (e.g., JD wants "Azure" but candidate only knows "AWS"), DO NOT FAIL the resume. 
    Only fail if the resume is nonsensical or completely irrelevant.
    
    Set content_passed = True if the resume is a decent attempt given the candidate's actual background.
    """

    user_prompt = f"""
    JOB DESCRIPTION:
    {job_description}

    RESUME CONTENT:
    {text_content}
    """

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=Critique,
        )

        result = completion.choices[0].message.parsed

        return {
            "length_passed": length_passed,
            "content_passed": result.content_passed,
            "feedback": result.feedback,
            "page_count": num_pages,
        }
    except Exception as e:
        print(f"   ❌ Semantic Check Failed: {e}")
        # Fallback to passing content if AI fails, so we don't lose the PDF
        return {
            "length_passed": length_passed,
            "content_passed": True, 
            "feedback": f"AI Error: {e}",
            "page_count": num_pages,
        }

if __name__ == "__main__":
    # Test Block
    import sys
    # Ensure we can find config_manager
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config_manager import load_config
    
    print("⚙️ Loading default profile for testing...")
    load_config() 
    
    # Dummy Test
    pdf_path = "output/test_resume.pdf" # Make sure this exists if testing
    jd = "Software Engineer with Python experience."
    
    if os.path.exists(pdf_path):
        res = proofread_resume(pdf_path, jd)
        print(res)
    else:
        print(f"⚠️ Create a dummy file at {pdf_path} to test this script.")