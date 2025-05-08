
import streamlit as st
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from io import BytesIO
from PIL import Image

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter

# Config
st.set_page_config(page_title="Lease Analyzer", page_icon="📄", layout="centered")
banner = Image.open("banner.png")
st.image(banner, use_container_width=True)
st.markdown("<div style='margin-top: -10px'></div>", unsafe_allow_html=True)

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
    except Exception as e:
        st.error(f"❌ Sample click error: {e}")

def generate_pdf(content, email, role, state):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleStyle", fontSize=16, leading=20, alignment=TA_LEFT, spaceAfter=8, textColor=colors.HexColor("#003366")))
    styles.add(ParagraphStyle(name="SubTitleStyle", fontSize=12, leading=16, alignment=TA_LEFT, textColor=colors.HexColor("#003366"), spaceAfter=12))
    styles.add(ParagraphStyle(name="SectionHeader", fontSize=12, spaceBefore=12, spaceAfter=6, backColor=colors.lightgrey))
    styles.add(ParagraphStyle(name="NormalText", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="WarningText", fontSize=10, backColor=colors.HexColor("#FFF3CD"), textColor=colors.HexColor("#856404")))
    styles.add(ParagraphStyle(name="GoodText", fontSize=10, backColor=colors.HexColor("#D4EDDA"), textColor=colors.HexColor("#155724")))

    elements = []
    elements.append(Paragraph("Lease Analysis Report", styles["TitleStyle"]))
    elements.append(Paragraph(f"State Analyzed: {state}", styles["SubTitleStyle"]))
    elements.append(Paragraph(f"For: {email} ({role})", styles["NormalText"]))
    elements.append(Spacer(1, 6))

    issues = [line for line in content.split("\n") if line.startswith("- ⚠️")]
    compliant = [line for line in content.split("\n") if line.startswith("- ✅")]

    if issues:
        elements.append(Paragraph("⚠️ Potential Issues", styles["SectionHeader"]))
        for line in issues:
            elements.append(Paragraph(line.replace("- ⚠️", "⚠️"), styles["WarningText"]))

    if compliant:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("✅ Compliant Clauses", styles["SectionHeader"]))
        for line in compliant:
            elements.append(Paragraph(line.replace("- ✅", "✅"), styles["GoodText"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer
# Sidebar
with st.sidebar:
    st.markdown("📚 **Helpful Resources**")
    state_preview = st.session_state.get("state_select", "New Jersey")
    if state_preview == "New Jersey":
        st.markdown("- [NJ Truth-in-Renting Guide](https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf)")
        st.markdown("- [NJ Landlord-Tenant Info](https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html)")
    else:
        st.markdown("- [PA Tenant Rights Guide](https://www.attorneygeneral.gov/wp-content/uploads/2018/01/Tenant_Rights.pdf)")
        st.markdown("- [PA Legal Aid Housing](https://www.palawhelp.org/issues/housing/landlord-and-tenant-law)")

# UI
state = st.selectbox("Which state is this lease for?", ["New Jersey", "Pennsylvania"], key="state_select")
role = st.radio("Who are you reviewing this lease as?", ["Tenant", "Landlord"], key="role_radio")
uploaded_file = st.file_uploader("Upload Lease (PDF only)", type="pdf", key="lease_upload")
email = st.text_input("Your Email (to receive report):", key="email_input")

if uploaded_file and email and "@" in email and "." in email:
    if email_already_used(email):
        st.error("⚠️ This email has already used its free lease analysis.")
    else:
        lease_text = ""
        for page in PyPDF2.PdfReader(uploaded_file).pages:
            lease_text += page.extract_text() or ""
        if st.button("Analyze Lease"):
            save_email(email)
            with st.spinner("Analyzing lease..."):
                prompt = f"""
You are a legal assistant trained in {state} tenant law.
The user reviewing this lease is a {role.lower()}.
Your task is to review the lease text and identify whether it complies with local law.

- ⚠️ **Potential Issue:** [short]
- ✅ **Compliant:** [short]

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
                    st.subheader("📊 Analysis Results")
                    st.markdown(result)
                    pdf_data = generate_pdf(result, email, role, state)
                    st.download_button("📄 Download PDF", pdf_data, "lease_analysis.pdf")
                except RateLimitError:
                    st.error("⚠️ Too many requests. Please wait.")

# Footer
st.markdown("""
---
🔒 **Disclaimer**  
This tool is for **educational and informational purposes only** and does **not constitute legal advice**.  
Always consult with a qualified attorney.

🔐 **Privacy Notice**  
We do not store or retain any uploaded lease documents or results.  
Only your email address is saved to track free usage. Nothing else is collected or shared.
""")
