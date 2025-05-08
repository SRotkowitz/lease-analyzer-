import streamlit as st
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textwrap import wrap
import time

# Set Streamlit page config
st.set_page_config(page_title="Lease Analyzer", page_icon="📄", layout="centered")

from PIL import Image

banner = Image.open("banner.png")
st.image(banner, use_column_width=True)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

def log_sample_click():
    data = {"data": [{"Email": "sample_demo_click"}]}
    try:
        response = requests.post(SHEETDB_URL, json=data)
        if response.status_code != 201:
            st.warning("Something went wrong logging the sample click.")
    except Exception as e:
        st.error("Error logging the sample click.")

def email_already_used(email):
    response = requests.get(f"{SHEETDB_URL}/search?Email={email}")
    return response.status_code == 200 and len(response.json()) > 0

def save_email(email):
    data = {"data": [{"Email": email}]}
    try:
        response = requests.post(SHEETDB_URL, json=data)
        if response.status_code != 201:
            st.warning("Something went wrong saving your email.")
    except Exception as e:
        st.error("Error saving email.")

def generate_pdf(content, email, role, state):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 40
    y = height - 40

    disclaimer = (
        "Disclaimer: This lease analysis is for educational and informational purposes only and "
        "does not constitute legal advice. Always consult with a qualified attorney for legal guidance "
        "regarding your specific situation."
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
    y -= 15

    wrapped_disclaimer = wrap(disclaimer, 95)
    pdf.setFont("Helvetica-Oblique", 8)
    for line in wrapped_disclaimer:
        pdf.drawString(x_margin, y, line)
        y -= 12

    y -= 10
    pdf.setFont("Helvetica", 11)
    pdf.drawString(x_margin, y, "-" * 95)
    y -= 20

    pdf.setFont("Helvetica", 10)
    for line in content.split("\n"):
        wrapped_lines = wrap(line, 95)
        for wrapped_line in wrapped_lines:
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

# Header & UI
st.markdown("<h1 style='text-align:center;'>📄 NJ/PA Lease Risk Checker</h1>", unsafe_allow_html=True)
st.markdown("Upload your lease. Our AI checks for legal red flags — fast, free, and private.")

# Optional: Try a sample lease for preview
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

st.markdown("## Step 1: Choose Your State and Role")
col1, col2 = st.columns(2)
with col1:
    state = st.selectbox("Which state is this lease for?", ["New Jersey", "Pennsylvania"])
with col2:
    role = st.radio("Who are you reviewing this lease as?", ["Tenant", "Landlord"])

st.markdown("## Step 2: Upload Lease and Enter Email")
col3, col4 = st.columns([3, 2])
with col3:
    uploaded_file = st.file_uploader("Upload Lease (PDF only)", type="pdf")
with col4:
    email = st.text_input("Your Email (to receive report):")

with st.expander("🔐 Privacy & Legal Notes"):
    st.markdown("""
    - We do **not** store your lease files.
    - Only your email is saved for access tracking.
    - This tool is **not legal advice** — it’s an automated review based on state rules.
    """)

with st.sidebar:
    st.markdown("📚 **Helpful Resources**")
    if state == "New Jersey":
        st.markdown("""
- [NJ Truth-in-Renting Guide](https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf)
- [Landlord-Tenant Info (NJ)](https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html)
        """)
    else:
        st.markdown("""
- [PA Tenant Guide](https://www.attorneygeneral.gov/wp-content/uploads/2018/01/Tenant_Rights.pdf)
- [PA Legal Aid Housing](https://www.palawhelp.org/issues/housing/landlord-and-tenant-law)
        """)

if uploaded_file:
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    lease_text = ""
    for page in pdf_reader.pages:
        lease_text += page.extract_text() or ""

    st.subheader("📄 Extracted Lease Text")
    st.text_area("Lease Text", lease_text, height=300)

    if email and "@" in email and "." in email:
        if email_already_used(email):
            st.error("⚠️ This email has already used its free lease analysis.")
        else:
            if st.button("Analyze Lease"):
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
                    except RateLimitError:
                        st.error("🚫 Too many requests. Please wait and try again shortly.")
                        st.stop()

                    result = response.choices[0].message.content
                    lines = result.strip().split("\n")
                    seen = set()
                    cleaned_lines = [line for line in lines if line.strip() and not (line in seen or seen.add(line))]
                    cleaned_result = "\n".join(cleaned_lines)

                if cleaned_result:
                    st.subheader("📊 Analysis Results")
                    st.markdown(cleaned_result)

                    disclaimer = (
                        "Disclaimer: This lease analysis is for educational and informational purposes only and "
                        "does not constitute legal advice. Always consult with a qualified attorney for legal guidance "
                        "regarding your specific situation.\n\n"
                    )
                    final_text = disclaimer + cleaned_result

                    st.download_button(
                        label="📥 Download as Text",
                        data=final_text,
                        file_name="lease_analysis.txt",
                        mime="text/plain"
                    )

                    pdf_data = generate_pdf(cleaned_result, email, role, state)
                    st.download_button(
                        label="📄 Download as PDF",
                        data=pdf_data,
                        file_name="lease_analysis.pdf",
                        mime="application/pdf"
                    )
