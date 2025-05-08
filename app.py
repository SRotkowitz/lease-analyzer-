
import streamlit as st
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textwrap import wrap
from PIL import Image

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch

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

def generate_redesigned_pdf(content, email, role, state):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleStyle", fontSize=16, leading=20, spaceAfter=12, alignment=TA_LEFT, textColor=colors.HexColor("#003366")))
    styles.add(ParagraphStyle(name="SectionHeader", fontSize=13, leading=18, spaceBefore=12, textColor=colors.HexColor("#222222"), backColor=colors.lightgrey, spaceAfter=6, leftIndent=0))
    styles.add(ParagraphStyle(name="NormalText", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="HighlightIssue", fontSize=10, leading=14, backColor=colors.HexColor("#FFF3CD"), textColor=colors.HexColor("#856404")))
    styles.add(ParagraphStyle(name="HighlightCompliant", fontSize=10, leading=14, backColor=colors.HexColor("#D4EDDA"), textColor=colors.HexColor("#155724")))

    elements = []

    logo_path = "banner.png"
    elements.append(RLImage(logo_path, width=6.5 * inch, height=1 * inch))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"{state} Lease Compliance Report", styles["TitleStyle"]))
    elements.append(Paragraph(f"For: <b>{email}</b> ({role})", styles["NormalText"]))
    elements.append(Spacer(1, 6))

    disclaimer = "This lease analysis is for educational and informational purposes only and does not constitute legal advice. Always consult with a qualified attorney."
    elements.append(Paragraph(disclaimer, styles["NormalText"]))
    elements.append(Spacer(1, 12))

    lines = content.strip().split("\n")
    issues, compliant = [], []
    for line in lines:
        if line.startswith("- ⚠️"):
            issues.append(Paragraph(line.replace("- ⚠️", "⚠️"), styles["HighlightIssue"]))
        elif line.startswith("- ✅"):
            compliant.append(Paragraph(line.replace("- ✅", "✅"), styles["HighlightCompliant"]))

    if issues:
        elements.append(Paragraph("Potential Issues", styles["SectionHeader"]))
        elements.extend(issues)

    if compliant:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Compliant Clauses", styles["SectionHeader"]))
        elements.extend(compliant)

    resources = {
        "New Jersey": [
            "Resources:",
            "- NJ Truth-in-Renting Guide: https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf",
            "- NJ Tenant Info Page: https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html"
        ],
        "Pennsylvania": [
            "Resources:",
            "- PA Tenant Guide: https://www.attorneygeneral.gov/wp-content/uploads/2018/01/Tenant_Rights.pdf",
            "- PA Legal Aid: https://www.palawhelp.org/issues/housing/landlord-and-tenant-law"
        ]
    }

    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Helpful Resources", styles["SectionHeader"]))
    for res in resources[state]:
        elements.append(Paragraph(res, styles["NormalText"]))

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

state = st.selectbox("Which state is this lease for?", ["New Jersey", "Pennsylvania"], key="state_select")
role = st.radio("Who are you reviewing this lease as?", ["Tenant", "Landlord"], key="role_radio")

email = st.text_input("Your Email (to receive report):", key="email_input")

st.markdown("""
<style>
.sample-button button {
    border: 2px double #FFD700;
    background-color: #FFD700;
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

if st.button("🔍 Try a Sample Lease"):
    log_sample_click()
    st.markdown("### 🧾 Sample Lease Compliance Report")
    st.markdown("""
#### ⚠️ Potential Issues
- ⚠️ **Late Fee**: Lease allows charging an unspecified late fee — this may violate NJ limits.
- ⚠️ **Entry Notice**: Landlord entry clause lacks notice requirements.
- ⚠️ **Repair Language**: Lease says tenant must fix "all issues," which may be too broad under NJ law.

#### ✅ Compliant Clauses
- ✅ **Security Deposit**: Clearly limited to 1.5 months' rent.
- ✅ **Lead Paint Disclosure**: Clause included for pre-1978 properties.
- ✅ **Termination Clause**: Lease states 30-day notice for ending tenancy.
""")

uploaded_file = st.file_uploader("Upload Lease (PDF only)", type="pdf", key="lease_upload")
if uploaded_file and email and "@" in email:
    if email_already_used(email):
        st.error("⚠️ This email has already used its free lease analysis.")
    else:
        lease_text = ""
        for page in PyPDF2.PdfReader(uploaded_file).pages:
            lease_text += page.extract_text() or ""
        st.text_area("📄 Lease Text", lease_text, height=300)

        if st.button("Analyze Lease", key="analyze"):
            save_email(email)
            with st.spinner("Analyzing lease..."):
                rules = {
                    "New Jersey": """
- Security deposit must not exceed 1.5 months’ rent.
- Lease must allow tenant the right to a habitable space.
- Landlord must give 30 days’ notice for rent increases on month-to-month leases.
- Self-help eviction is illegal in NJ.
- Security deposit must be returned within 30 days of lease end.
- Landlord must make repairs within a reasonable time.
- Lease must clearly state responsibility for utilities.
- Landlord must give advance notice before entering unit.
- Lease may not waive tenant's right to a habitable unit or legal process.
- Lease must outline clear termination and renewal process.
- Illegal fees or penalties (e.g., admin fees) may not be charged.
- Security deposit deductions must be itemized and reasonable.
- Tenants may request receipts for rent payments.
- Pre-1978 properties must include lead paint disclosure.
- Evictions must go through the formal NJ court process.
""",
                    "Pennsylvania": """
- Security deposit cannot exceed 2 months’ rent in first year.
- Deposit must be returned within 30 days of lease end with itemized list of deductions.
- Lease must ensure habitability of the rental unit.
- Landlord must make timely repairs and maintain common areas.
- Landlord must disclose lead paint risk for buildings built before 1978.
- Utilities and maintenance responsibilities must be clearly assigned.
- Entry requires reasonable notice unless emergency.
- Self-help eviction is illegal; court process is required.
- Lease must explain renewal or termination procedures.
- Fees and penalties must be legal and clearly listed.
- Tenants have the right to withhold rent in certain conditions (escrow).
- Landlords may be required to register with local municipalities.
- Late fees must be reasonable and non-punitive.
- Tenants can sue for wrongful eviction or unreturned deposits.
- Lease clauses must not waive legal tenant protections.
"""
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
                    pdf_data = generate_redesigned_pdf(cleaned_result, email, role, state)
                    st.download_button("📄 Download as PDF", pdf_data, "lease_analysis.pdf")
                except RateLimitError:
                    st.error("🚫 Too many requests. Please wait and try again.")
