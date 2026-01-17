import json
import os
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

async def render_resume(json_path, output_pdf_path, scale=1.0):
    """
    Renders PDF with a specific scaling factor.
    scale=1.0 : Standard (10pt font, 0.5in margin)
    scale=0.9 : Compact (9pt font, 0.45in margin)
    """
    
    # 1. Load Data
    with open(json_path, 'r') as f:
        resume_data = json.load(f)

    # 2. Calculate Dynamic Styles
    # Base values
    base_body = 10.0
    base_header = 24.0
    base_sub = 12.0
    base_margin = 0.5
    base_line_height = 1.4

    # Apply Scale
    css_context = {
        "margin": f"{base_margin * scale:.2f}in",
        "body_font": f"{base_body * scale:.1f}pt",
        "header_font": f"{base_header * scale:.1f}pt",
        "sub_font": f"{base_sub * scale:.1f}pt",
        "line_height": f"{base_line_height * (scale if scale < 1 else 1.0):.2f}" # Shrink spacing too
    }
    
    print(f"   📐 Rendering with Scale {scale} (Font: {css_context['body_font']}, Margin: {css_context['margin']})...")

    # 3. Setup Jinja2
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('resume.html')

    # 4. Render HTML
    html_content = template.render(resume=resume_data, style=css_context)
    
    temp_html_path = os.path.abspath(f"temp_resume_{scale}.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 5. Playwright Rendering
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{temp_html_path}")
        
        await page.pdf(
            path=output_pdf_path, 
            format="Letter", 
            print_background=True, 
            margin={
                "top": css_context["margin"],
                "bottom": css_context["margin"],
                "left": css_context["margin"],
                "right": css_context["margin"]
            }
        )
        await browser.close()

    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)