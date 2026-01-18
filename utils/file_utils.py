# --- HELPER FUNCTION ---
def get_clean_filename(company, title):
    company_clean = "".join(c for c in str(company) if c.isalnum())
    role_clean = "".join(c for c in str(title) if c.isalnum())[:15]
    return f"Resume_{company_clean}_{role_clean}.pdf"
