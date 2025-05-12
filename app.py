
import streamlit as st
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textwrap import wrap
import time
from PIL import Image

st.set_page_config(page_title="Lease Analyzer", page_icon="📄", layout="centered")

banner = Image.open("banner.png")
st.image(banner, use_container_width=True)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

def email_already_used(email):
    response = requests.get(f"{SHEETDB_URL}/search?Email={email}")
    return response.status_code == 200 and len(response.json()) > 0

def save_email(email):
    data = {"data": [{"Email": email}]}
    try:
        requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to save email.")

def log_sample_click():
    data = {"data": [{"Email": "sample_demo_click"}]}
    try:
        requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to track demo preview.")

def generate_pdf(content, email, role, state):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleStyle", fontSize=16, leading=20, alignment=TA_LEFT, textColor=colors.HexColor("#003366")))
    styles.add(ParagraphStyle(name="SubTitleStyle", fontSize=12, leading=16, alignment=TA_LEFT, textColor=colors.HexColor("#003366"), spaceAfter=12))
    styles.add(ParagraphStyle(name="SectionHeader", fontSize=12, spaceBefore=12, spaceAfter=6, backColor=colors.lightgrey))
    styles.add(ParagraphStyle(name="NormalText", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="WarningText", fontSize=10, backColor=colors.HexColor("#FFF3CD"), textColor=colors.HexColor("#856404")))
    styles.add(ParagraphStyle(name="GoodText", fontSize=10, backColor=colors.HexColor("#D4EDDA"), textColor=colors.HexColor("#155724")))

    elements = []
    elements.append(Paragraph("Lease Analysis Report", styles["TitleStyle"]))
    elements.append(Paragraph(f"State Analyzed: {state}", styles["SubTitleStyle"]))
    elements.append(Paragraph(f"For: {email} ({role})", styles["NormalText"]))
    elements.append(Spacer(1, 12))

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

    # Resources
    resources = {
        "New Jersey": [
            "- NJ Truth-in-Renting Guide: https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf",
            "- NJ Tenant Info Page: https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html"
        ],
        "Pennsylvania": [
            "- PA Tenant Guide: https://www.attorneygeneral.gov/wp-content/uploads/2018/01/Tenant_Rights.pdf",
            "- PA Legal Aid: https://www.palawhelp.org/issues/housing/landlord-and-tenant-law"
        ]
    }

    elements.append(Paragraph("Helpful Resources", styles["SectionHeader"]))
    for link in resources[state]:
        elements.append(Paragraph(link, styles["NormalText"]))
    elements.append(Spacer(1, 12))

    # Disclaimer and Privacy
    elements.append(Paragraph("Disclaimer", styles["SectionHeader"]))
    elements.append(Paragraph(
        "This lease analysis is for educational and informational purposes only and does not constitute legal advice. "
        "Always consult with a qualified attorney regarding your specific situation.",
        styles["NormalText"]
    ))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Privacy Notice", styles["SectionHeader"]))
    elements.append(Paragraph(
        "We do not store or retain any uploaded lease documents or results. "
        "Only your email is recorded temporarily to track free analysis usage.",
        styles["NormalText"]
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer


with st.sidebar:
    st.markdown("📚 **Helpful Resources**")
    state_preview = st.session_state.get("state_select", "New Jersey")
    if state_preview == "New Jersey":
        st.markdown("- [NJ Truth-in-Renting Guide](https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf)")
        st.markdown("- [NJ Landlord-Tenant Info](https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html)")
    else:
        st.markdown("- [PA Tenant Rights Guide](https://www.attorneygeneral.gov/wp-content/uploads/2018/01/Tenant_Rights.pdf)")
        st.markdown("- [PA Legal Aid Housing](https://www.palawhelp.org/issues/housing/landlord-and-tenant-law)")

st.markdown("""
<div style="border: 1px solid #ccc; border-radius: 10px; padding: 20px; background-color: #f9f9f9">
<h4>Step 1: Select Your State and Role</h4>
</div>
""", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    state = st.selectbox("Which state is this lease for?", ["New Jersey", "Pennsylvania"], key="state_select")
with col2:
    role = st.radio("Who are you reviewing this lease as?", ["Tenant", "Landlord"], key="role_radio")

st.markdown("""
<div style="border: 1px solid #ccc; border-radius: 10px; padding: 20px; background-color: #f9f9f9; margin-top: 20px">
<h4>Step 2: Upload Lease and Enter Email</h4>
</div>
""", unsafe_allow_html=True)
col3, col4 = st.columns([3, 2])
with col3:
    uploaded_file = st.file_uploader("Upload Lease (PDF only)", type="pdf", key="lease_upload")
with col4:
    email = st.text_input("Your Email (to receive report):", key="email_input")

st.markdown("""
<div style="border: 1px solid #ccc; border-radius: 10px; padding: 20px; background-color: #f9f9f9; margin-top: 20px">
<h4>Step 3: Try a Sample Analysis (Optional)</h4>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.sample-button button {
    border: 2px double #FFD700;
    background-color: #FFFFE0;
    color: black;
    font-weight: bold;
    width: 100%;
    padding: 0.5em 1em;
    border-radius: 8px;
}
.analyze-button button {
    border: 2px double #006400;
    background-color: #DFFFD6;
    color: black;
    font-weight: bold;
    width: 100%;
    padding: 0.5em 1em;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown("### 🧾 Example: Lease Red Flags Caught in NJ")
    st.markdown("""
#### ⚠️ Potential Issues
- ⚠️ **Late Fee**: Lease allows charging an unspecified late fee — this may violate NJ limits.
- ⚠️ **Entry Notice**: Landlord entry clause lacks notice requirements.
- ⚠️ **Repair Language**: Lease says tenant must fix "all issues," which may be too broad under NJ law.

#### ✅ Compliant Clauses
- ✅ **Security Deposit**: Clearly limited to 1.5 months' rent.
- ✅ **Lead Paint Disclosure**: Clause included for pre-1978 properties.
- ✅ **Termination Clause**: Lease states 30-day notice for ending tenancy.

---
This sample analysis was generated using the same AI rules applied to real leases.
    """)

if uploaded_file and email:
    if "@" in email and "." in email:
        if email_already_used(email):
            st.error("⚠️ This email has already used its free lease analysis.")
        else:
            lease_text = ""
            for page in PyPDF2.PdfReader(uploaded_file).pages:
                lease_text += page.extract_text() or ""
            st.subheader("📄 Extracted Lease Text")
            st.text_area("Lease Text", lease_text, height=300)

            if st.button("Analyze Lease"):
                save_email(email)
                with st.spinner("Analyzing lease..."):
                    rules = {
                        "New Jersey": """...""",
                        "Pennsylvania": """..."""
                    }
                    prompt = f"""
You are a legal assistant trained in {state} tenant law.
The user reviewing this lease is a {role.lower()}.
Your task is to review the lease text and identify whether it complies with the {state} tenant rules below.
Return the output using this format:
- ⚠️ **Potential Issue:** [short description]
- ✅ **Compliant:** [short description]
Only list each item once. Do not include summaries or explanations.

{rules[state]}

LEASE TEXT:
{lease_text}
"""
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.2,
                            max_tokens=800
                        )
                        result = response.choices[0].message.content
                        cleaned_result = "\n".join(dict.fromkeys(result.strip().split("\n")))
                        st.subheader("📊 Analysis Results")
                        st.markdown(cleaned_result)
                        final_text = "Disclaimer: This lease analysis is not legal advice.\n\n" + cleaned_result
                        st.download_button("📥 Download as Text", final_text, "lease_analysis.txt")
                        pdf_data = generate_pdf(cleaned_result, email, role, state)
                        st.download_button("📄 Download as PDF", pdf_data, "lease_analysis.pdf")
                    except RateLimitError:
                        st.error("🚫 Too many requests. Please wait and try again.")

st.markdown("""
<div style="margin-top: 40px; padding: 20px; border-top: 2px solid #ccc;">
  <h4 style="color: #003366;">🔒 Disclaimer</h4>
  <p style="font-size: 14px; line-height: 1.5;">
    This lease analysis is for <strong>educational and informational purposes only</strong> and does <strong>not constitute legal advice</strong>.<br>
    Always consult with a qualified attorney for legal guidance related to your lease or rental situation.
  </p>
  <h4 style="color: #003366; margin-top: 30px;">🔐 Privacy Notice</h4>
  <p style="font-size: 14px; line-height: 1.5;">
    We do not store or retain any uploaded lease documents or analysis results. All document processing happens temporarily during your session.<br>
    Only your email address is saved (to verify free access) — nothing else is collected, tracked, or shared.
  </p>
</div>
""", unsafe_allow_html=True)
