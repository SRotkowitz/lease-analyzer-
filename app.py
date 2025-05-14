import streamlit as st
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from PIL import Image
import time

st.set_page_config(page_title="Lease Analyzer", page_icon="📄", layout="centered")

banner = Image.open("banner.png")
st.image(banner, use_container_width=True)

st.markdown("""
<div style="background-color: #e6f2ff; padding: 16px; border-radius: 10px; border: 1px solid #99c2ff; margin-top: 10px;">
  <strong>✅ Created by NJ & PA-Trained Legal Professionals</strong><br>
  Trusted by over <strong>1,200+ landlords and tenants</strong> to flag risky or illegal lease clauses.<br><br>
  Fast. Confidential. No documents stored.
</div>
""", unsafe_allow_html=True)

if "scroll_to_form" not in st.session_state:
    st.session_state.scroll_to_form = False

st.markdown("""
<div style="background-color:#FFF8DC; padding: 20px; border-radius: 10px; border: 1px solid #eee; text-align: center; margin-top: 20px;">
  <h4 style="margin-bottom: 10px;">📄 Upload Your Lease Now</h4>
  <p style="font-size: 16px; margin-top: 0;">We’ll scan it for red flags based on NJ/PA law.<br>No signup required.</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Start Lease Check"):
        st.session_state.scroll_to_form = True

SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def save_email(email):
    data = {"data": [{"Email": email}]}
    try:
        requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to save email.")

def log_user_action(email, action):
    data = {"data": [{"Email": email, "Action": action, "Time": time.strftime("%Y-%m-%d %H:%M:%S")}]}
    try:
        requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to log user action.")

def generate_pdf(content, email, role, state):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleStyle", fontSize=16, leading=20, alignment=TA_LEFT, textColor=colors.HexColor("#003366")))
    styles.add(ParagraphStyle(name="SubTitleStyle", fontSize=12, leading=16, alignment=TA_LEFT, textColor=colors.HexColor("#003366"), spaceAfter=12))
    styles.add(ParagraphStyle(name="SectionHeader", fontSize=12, spaceBefore=12, spaceAfter=6, backColor=colors.lightgrey))
    styles.add(ParagraphStyle(name="NormalText", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="WarningText", fontSize=10, backColor=colors.HexColor("#FFF3CD"), textColor=colors.HexColor("#856404")))
    styles.add(ParagraphStyle(name="GoodText", fontSize=10, backColor=colors.HexColor("#D4EDDA"), textColor=colors.HexColor("#155724")))

    elements = [
        Paragraph("Lease Analysis Report", styles["TitleStyle"]),
        Paragraph(f"State Analyzed: {state}", styles["SubTitleStyle"]),
        Paragraph(f"For: {email} ({role})", styles["NormalText"]),
        Spacer(1, 12)
    ]

    issues = [line for line in content.strip().split("\n") if line.startswith("- ⚠️")]
    compliant = [line for line in content.strip().split("\n") if line.startswith("- ✅")]

    if issues:
        elements.append(Paragraph("⚠️ Potential Issues", styles["SectionHeader"]))
        for line in issues:
            elements.append(Paragraph(line.replace("- ⚠️", "⚠️"), styles["WarningText"]))
        elements.append(Spacer(1, 12))

    if compliant:
        elements.append(Paragraph("✅ Compliant Clauses", styles["SectionHeader"]))
        for line in compliant:
            elements.append(Paragraph(line.replace("- ✅", "✅"), styles["GoodText"]))
        elements.append(Spacer(1, 12))

    doc.build(elements)
    buffer.seek(0)
    return buffer

if st.session_state.scroll_to_form:
    st.markdown("### Step 1: Upload Your Lease")
    with st.form("lease_form"):
        col1, col2 = st.columns(2)
        with col1:
            state = st.selectbox("Which state?", ["New Jersey", "Pennsylvania"])
        with col2:
            role = st.radio("You are a:", ["Tenant", "Landlord"])

        uploaded_file = st.file_uploader("Upload Lease (PDF only)", type="pdf")
        submitted = st.form_submit_button("🔍 Analyze Lease")

    if uploaded_file and submitted:
        lease_text = ""
        for page in PyPDF2.PdfReader(uploaded_file).pages:
            lease_text += page.extract_text() or ""
        log_user_action("anonymous", "Uploaded Lease")

        rules = {
            "New Jersey": "...",
            "Pennsylvania": "..."
        }

        prompt = f"""
You are a legal assistant trained in {state} tenant law.
The user reviewing this lease is a {role.lower()}.
Your task is to review the lease text and identify whether it complies with the {state} tenant rules below.
Return the output using this format:
- ⚠️ Potential Issue: [short description]
- ✅ Compliant: [short description]
Only list each item once. Do not include summaries or explanations.

{rules[state]}

LEASE TEXT:
{lease_text}
"""

        with st.spinner("Analyzing lease..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=800
                )
                result = response.choices[0].message.content
                cleaned_result = "\n".join(dict.fromkeys(result.strip().split("\n")))

                st.markdown("""
<div style="border: 1px solid #28a745; border-radius: 10px; padding: 20px; background-color: #f6fff6; margin-top: 30px;">
  <h4 style="color:#155724;">📊 Step 2: Lease Analysis Results</h4>
  <p>Below are the key issues and compliant clauses we found in your lease:</p>
</div>
""", unsafe_allow_html=True)

                st.markdown(cleaned_result)

                st.markdown("""
<div style="font-size: 13px; color: #555; margin-top: 10px;">
ℹ️ This analysis is for informational purposes only and does not constitute legal advice.
</div>
""", unsafe_allow_html=True)

                email = st.text_input("🔓 Enter your email to download this report as a PDF:")
                if email and "@" in email and "." in email:
                    save_email(email)
                    log_user_action(email, "Downloaded PDF Report")
                    pdf_data = generate_pdf(cleaned_result, email, role, state)
                    st.download_button("📄 Download Lease Analysis as PDF", pdf_data, "lease_analysis.pdf")
            except RateLimitError:
                st.error("🚫 Too many requests. Please wait and try again.")

st.markdown("""
**Disclaimer:** This lease analysis is for informational purposes only and does not constitute legal advice.  
**Privacy:** We do not store your documents or results. Only your email is recorded temporarily for usage tracking.
""")
