import json
import os
from pydantic import BaseModel
from openai import OpenAI

# --- Schema ---
class JobAssessment(BaseModel):
    match_score: int  # 0 to 100
    is_suitable: bool
    reasoning: str

def assess_job_suitability(jd_text, master_json_path):
    """
    Evaluates if the candidate is realistically qualified for the job.
    Uses gpt-4o-mini to save costs on high-volume filtering.
    """
    
    # 0. SAFETY CHECK & CLIENT INIT
    if not os.environ.get("OPENAI_API_KEY"):
        # Fail safe: If no key, we can't assess, so we skip (return False)
        print("   ⚠️ No OpenAI Key found. Skipping Assessment.")
        return JobAssessment(match_score=0, is_suitable=False, reasoning="Missing API Key")

    client = OpenAI() # Lazy Load

    with open(master_json_path, 'r') as f:
        resume_data = json.load(f)
        
    # Extract just the skills and latest role for a cheaper token count
    candidate_profile = {
        "skills": resume_data.get("skills", {}),
        "experience_summary": [
            f"{job['position']} at {job['company']}" for job in resume_data.get("experience", [])
        ],
        # Ideally, calculate this dynamically, but hardcoded is fine for now
        "years_experience": "Entry Level / Junior (approx 1-2 years including internships)" 
    }

    print(f"   ⚖️  Assessing suitability (via gpt-4o-mini)...")

    system_prompt = """
    You are a Career Coach. Evaluate if a Candidate is a reasonable match for a Job Description.
    
    CRITERIA FOR "SUITABLE":
    1. EXPERIENCE LEVEL: If the JD asks for "Senior", "Principal", "Staff", "VP", or "5+ years", REJECT it immediately (Score < 40).
    2. TECH STACK: The candidate is a Python/React/Unity developer. 
       - If the JD requires purely different stacks (e.g., "Rust", "Embedded C", "Cobol", "Salesforce Apex"), REJECT it.
       - If it's a "Java" role but asks for "Expert/Architect" level, REJECT it.
       - If it's a "Java" role for a Junior/Intern, ACCEPT it (skills are transferable).
    3. DOMAIN: If the JD requires specialized domain knowledge the candidate lacks (e.g., "Quantitative Trading Algorithms", "Medical Device Firmware"), REJECT it.
    
    Return a score (0-100) and a boolean 'is_suitable'. 
    Set 'is_suitable' to True ONLY if the score is >= 60.
    """

    user_prompt = f"""
    CANDIDATE PROFILE:
    {json.dumps(candidate_profile)}

    JOB DESCRIPTION:
    {jd_text[:3000]}
    """

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=JobAssessment,
        )
        return completion.choices[0].message.parsed
        
    except Exception as e:
        print(f"   ❌ Filter Agent Failed: {e}")
        # Default to False (Safety)
        return JobAssessment(match_score=0, is_suitable=False, reasoning=f"Error: {e}")

if __name__ == "__main__":
    # Test Block
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config_manager import load_config
    
    print("⚙️ Loading default profile for testing...")
    load_config()
    
    # Dummy Test
    dummy_jd = "Senior Python Developer. Requires 7+ years of experience in High Frequency Trading."
    if os.path.exists("master_resume.json"):
        result = assess_job_suitability(dummy_jd, "master_resume.json")
        print(f"Result: Score {result.match_score} | Suitable: {result.is_suitable}")
        print(f"Reason: {result.reasoning}")
    else:
        print("⚠️ master_resume.json missing.")