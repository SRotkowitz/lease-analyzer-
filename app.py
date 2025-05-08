
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

# Page configuration
st.set_page_config(page_title="Lease Analyzer", page_icon="📄", layout="centered")

# Banner image
banner = Image.open("banner.png")
st.image(banner, use_container_width=True)

# Initialize OpenAI and sheet logging
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

def email_already_used(email):
    response = requests.get(f"{SHEETDB_URL}/search?Email={email}")
    return response.status_code == 200 and len(response.json()) > 0

def save_email(email):
    data = {"data": [{"Email": email}]}
    try:
        response = requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to save email.")

def log_sample_click():
    data = {"data": [{"Email": "sample_demo_click"}]}
    try:
        requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to track demo preview.")

def generate_pdf(content, email, role, state):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 40
    y = height - 40

    disclaimer = (
        "Disclaimer: This lease analysis is for educational and informational purposes only and "
        "does not constitute legal advice. Always consult with a qualified attorney."
    )

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

    pdf.setFont("Helvetica", 10)
    pdf.drawString(x_margin, y, f"{state} Lease Analysis for: {email} ({role})")
    y -= 20

    pdf.setFont("Helvetica-Oblique", 8)
    for line in wrap(disclaimer, 95):
        pdf.drawString(x_margin, y, line)
        y -= 12

    y -= 10
    pdf.setFont("Helvetica", 11)
    pdf.drawString(x_margin, y, "-" * 95)
    y -= 20

    pdf.setFont("Helvetica", 10)
    for line in content.split("\n"):
        for wrapped_line in wrap(line, 95):
            if y < 50:
                pdf.showPage()
                y = height - 40
                pdf.setFont("Helvetica", 10)
            pdf.drawString(x_margin, y, wrapped_line)
            y -= 14

    y -= 20
    pdf.setFont("Helvetica-Bold", 10)
    for line in resources[state]:
        if y < 50:
            pdf.showPage()
            y = height - 40
            pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_margin, y, line)
        y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer

# Sidebar help
with st.sidebar:
    st.markdown("📚 **Helpful Resources**")
    state_preview = st.session_state.get("state_select", "New Jersey")
    if state_preview == "New Jersey":
        st.markdown("- [NJ Truth-in-Renting Guide](https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf)")
        st.markdown("- [NJ Landlord-Tenant Info](https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html)")
    else:
        st.markdown("- [PA Tenant Rights Guide](https://www.attorneygeneral.gov/wp-content/uploads/2018/01/Tenant_Rights.pdf)")
        st.markdown("- [PA Legal Aid Housing](https://www.palawhelp.org/issues/housing/landlord-and-tenant-law)")

# Step 1
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

# Step 2
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

# Step 3
st.markdown("""
<div style="border: 1px solid #ccc; border-radius: 10px; padding: 20px; background-color: #f9f9f9; margin-top: 20px">
<h4>Step 3: Try a Sample Analysis (Optional)</h4>
</div>
""", unsafe_allow_html=True)

# Styled sample button
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
</style>
<div class="sample-button">
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

---
This sample analysis was generated using the same AI rules applied to real leases.
""")

# Process uploaded file
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

            # Styled analyze button
            st.markdown("""
<style>
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
<div class="analyze-button">
""", unsafe_allow_html=True)

            if st.button("Analyze Lease"):
                save_email(email)
                with st.spinner("Analyzing lease..."):
                    rules = { ... }  # SAME rules dict as earlier
                    prompt = f"..."  # SAME prompt logic as earlier
                    ...
