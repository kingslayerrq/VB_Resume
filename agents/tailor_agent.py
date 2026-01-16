import json
import os
import datetime
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

# --- 1. Define Schema ---
class Education(BaseModel):
    institution: str
    area: str
    studyType: str
    startDate: str
    endDate: str
    score: Optional[str] = None
    courses: List[str]

class WorkExperience(BaseModel):
    company: str
    position: str
    startDate: str
    endDate: str
    location: Optional[str] = "New York, NY"
    bullets: List[str]

class Project(BaseModel):
    name: str
    technologies: List[str]
    description: str
    bullets: List[str]

class Skills(BaseModel):
    languages: List[str]
    frameworks: List[str]
    tools: List[str]

class Basics(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    website: str
    linkedin: str
    github: str

class Resume(BaseModel):
    basics: Basics
    education: List[Education]
    skills: Skills
    experience: List[WorkExperience]
    projects: List[Project]

# --- Helper: Format Date ---
def format_date(date_str):
    """Converts YYYY-MM to Sep 2024 format"""
    if not date_str or date_str.lower() == "present":
        return "Present"
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m")
        return dt.strftime("%b %Y")
    except ValueError:
        return date_str # Return original if parse fails

# --- 2. The Tailor Agent ---
def tailor_resume(master_json_path: str, job_description: str, feedback: str = "") -> dict:
    
    # Initialize Client HERE to ensure it uses the key set by config_manager
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OpenAI API Key is missing. Please check your Dashboard settings.")
        
    client = OpenAI() # Automatically looks for os.environ["OPENAI_API_KEY"]

    with open(master_json_path, 'r') as f:
        master_resume_data = json.load(f)

    print(f"🧵 Tailoring resume (Strict Bullet Count Enforcement)...")

    # --- UPDATED SYSTEM PROMPT ---
    system_prompt = """
    You are an expert Resume Editor.
    
    CRITICAL RULES:
    1. PRESERVE METRICS: You must NEVER remove specific numbers, percentages, or dollar amounts (e.g., "5,000+ visitors", "30% increase").
    
    2. BULLET POINT COUNT (STRICT): 
       - Compare the output to the Master Resume.
       - If a Project or Job has N bullet points in the Master Resume, the output MUST have AT LEAST N bullet points.
       - NEVER reduce the number of bullet points. You may add more or split complex ones, but NEVER merge or delete to have fewer.
       
    3. TONE: Use strong action verbs (Engineered, Architected, Spearheaded).
    4. EXPERIENCE: Include ALL Work Experience entries if we have less than 3, otherwise select at least 3 most relevant experiences.
    5. PROJECTS: Select at least 3 most relevant projects.
    6. DATE FORMAT: Keep dates in YYYY-MM format in the JSON (we will format them later).
    
    Check the Master Resume specifically for the "Ekings Multimedia" job. It contains metrics about "5,000+ visitors" and "30% engagement". You MUST include these in the output.
    """
    
    feedback_instruction = ""
    if feedback:
        feedback_instruction = f"PREVIOUS ATTEMPT REJECTED. FEEDBACK: {feedback}. YOU MUST FIX THIS."

    user_prompt = f"""
    TARGET JOB: {job_description}
    MASTER RESUME: {json.dumps(master_resume_data)}
    
    {feedback_instruction}
    """

    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=Resume,
    )

    tailored_resume = completion.choices[0].message.parsed
    tailored_dict = tailored_resume.model_dump()

    # --- Post-Processing: Fix Dates ---
    print("📅 Formatting dates...")
    for job in tailored_dict['experience']:
        job['startDate'] = format_date(job['startDate'])
        job['endDate'] = format_date(job['endDate'])
    
    for edu in tailored_dict['education']:
        edu['startDate'] = format_date(edu['startDate'])
        edu['endDate'] = format_date(edu['endDate'])

    return tailored_dict

if __name__ == "__main__":
    # --- TEST BLOCK (Updates to support Config Manager) ---
    import sys
    # Ensure we can find config_manager
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config_manager import load_config
    
    # Load the default profile to set the API Key in os.environ
    print("⚙️ Loading default profile for testing...")
    load_config() 
    
    sample_jd = "Software Engineer. Requirements: React, Node.js, C#, Unity."
    
    try:
        if not os.path.exists("master_resume.json"):
            print("⚠️ 'master_resume.json' not found. Create one to test.")
        else:
            new_resume = tailor_resume("master_resume.json", sample_jd)
            with open("tailored_resume.json", "w") as f:
                json.dump(new_resume, f, indent=4)
            print("✅ Success! Created tailored_resume.json")
    except Exception as e:
        print(f"❌ Error: {e}")