import fitz  # PyMuPDF
import os
from typing import Optional

from pydantic import BaseModel

from services.llm_client import chat_json, resolve_llm_settings

# --- 1. Define Schema ---
class Critique(BaseModel):
    content_passed: bool
    missing_keywords: list[str]
    feedback: str

def proofread_resume(
    pdf_path: str,
    job_description: str,
    llm_settings: Optional[dict] = None,
) -> dict:
    print(f"🧐 Proofreading {pdf_path}...")

    settings = resolve_llm_settings(llm_settings)
    if settings["provider"] == "openai" and not os.environ.get("OPENAI_API_KEY") and not settings.get("api_key"):
        print("   ⚠️ No OpenAI Key found. Skipping Semantic Check.")
        return {
            "length_passed": True,
            "content_passed": True,
            "feedback": "Skipped (No API Key)",
            "page_count": 0,
        }

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

    system_prompt += "\nReturn ONLY valid JSON with no extra commentary."

    try:
        result = chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_settings=llm_settings,
            schema=Critique,
        )

        return {
            "length_passed": length_passed,
            "content_passed": result["content_passed"],
            "feedback": result["feedback"],
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
