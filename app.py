import streamlit as st
import PyPDF2
from openai import OpenAI
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textwrap import wrap

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
        pass

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
            "- PA Tenants' Rights Guide: https://www.phfa.org/forms/housing_services/tenants-rights.pdf",
            "- PA Housing Resources: https://www.attorneygeneral.gov/protect-yourself/landlord-tenant-rights/"
        ]
    }

    pdf.setFont("Helvetica", 10)
    pdf.drawString(x_margin, y, f"{state} Lease Analysis for: {email} ({role})")
    y -= 15

    for line in wrap(disclaimer, 95):
        pdf.setFont("Helvetica-Oblique", 8)
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

# UI
st.title("Lease Analyzer")
st.write("Upload a lease PDF to get started.")

# STATE SELECTOR
state = st.selectbox("Which state is this lease from?", ["New Jersey", "Pennsylvania"])
role = st.radio("Who are you reviewing this lease as?", ["Tenant", "Landlord"])
email = st.text_input("Enter your email to receive one free analysis (required):")
uploaded_file = st.file_uploader("Choose a lease PDF", type="pdf")

# SIDEBAR LINKS
if state == "New Jersey":
    st.sidebar.markdown("📚 **NJ Tenant Resources**")
    st.sidebar.markdown("""
    - [Truth-in-Renting Guide (PDF)](https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf)
    - [Landlord-Tenant Info Page](https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html)
    """)
else:
    st.sidebar.markdown("📚 **PA Tenant Resources**")
    st.sidebar.markdown("""
    - [Tenants' Rights Guide (PDF)](https://www.phfa.org/forms/housing_services/tenants-rights.pdf)
    - [PA AG Housing Info](https://www.attorneygeneral.gov/protect-yourself/landlord-tenant-rights/)
    """)

# DISPLAY EXTRACTED LEASE TEXT
if uploaded_file:
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    lease_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
    st.subheader("Extracted Text:")
    st.text_area("Lease Text", lease_text, height=300)

    if email and "@" in email and "." in email:
        if email_already_used(email):
            st.error("⚠️ This email has already used its free lease analysis.")
        else:
            if st.button("Analyze Lease"):
                save_email(email)

                with st.spinner("Analyzing lease..."):

                    # RULE SETS
                    nj_rules = """
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
"""

                    pa_rules = """
- Security deposit must not exceed 2 months’ rent in the first year.
- Deposit must be returned within 30 days after move-out with itemized deductions.
- Lease must clearly define responsibilities for utilities and maintenance.
- Evictions must follow proper legal proceedings.
- Lead-based paint disclosure is required for pre-1978 housing.
- Lease cannot waive basic habitability rights.
- Landlord must provide notice before entering the property.
- Lease should include renewal and termination clauses.
- Illegal fees (e.g., excessive late fees) are prohibited.
- Lease must not include retaliatory clauses.
"""

                    rules = nj_rules if state == "New Jersey" else pa_rules

                    # GPT PROMPT
                    prompt = f"""
You are a legal assistant trained in {state} landlord-tenant law.
The user reviewing this lease is a {role.lower()}.

Your task is to review the lease text and identify whether it complies with the {state} rules below.

Return the output using this format:

- ⚠️ **Potential Issue:** [short description]
- ✅ **Compliant:** [short description]

Only list each item once. Do not include explanations, summaries, or legal citations.

{state.upper()} RULES:
{rules}

LEASE TEXT:
{lease_text}
"""

                    # GPT CALL
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=800
                    )

                    result = response.choices[0].message.content

                    # DEDUPLICATE LINES
                    lines = result.strip().split("\n")
                    seen = set()
                    cleaned_lines = [line for line in lines if line.strip() and not (line in seen or seen.add(line))]
                    cleaned_result = "\n".join(cleaned_lines)

                # DISPLAY RESULTS + DOWNLOAD OPTIONS
                st.subheader("Analysis:")
                st.markdown(cleaned_result)

                disclaimer = (
                    "Disclaimer: This lease analysis is for educational and informational purposes only and "
                    "does not constitute legal advice. Always consult with a qualified attorney for legal guidance "
                    "regarding your specific situation.\n\n"
                )

                final_text = disclaimer + cleaned_result

                st.download_button("📥 Download as Text", data=final_text, file_name="lease_analysis.txt", mime="text/plain")
                st.download_button("📄 Download as PDF", data=generate_pdf(cleaned_result, email, role, state), file_name="lease_analysis.pdf", mime="application/pdf")

# FOOTER
st.markdown("""
---
🔒 **Disclaimer**  
This tool is for **educational and informational purposes only** and does **not constitute legal advice**.  
Always consult with a qualified attorney for legal guidance related to your lease or rental situation.

🔐 **Privacy Notice**  
We do not store or retain any uploaded lease documents or analysis results. All processing happens temporarily during your session.  
Only your email address is saved (to verify free access) — nothing else is tracked or stored.
---
""")
