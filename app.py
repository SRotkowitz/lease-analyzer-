import streamlit as st
import PyPDF2
import openai
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textwrap import wrap

openai.api_key = st.secrets["OPENAI_API_KEY"]
SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

def email_already_used(email):
    response = requests.get(f"{SHEETDB_URL}/search?Email={email}")
    return response.status_code == 200 and len(response.json()) > 0

def save_email(email):
    data = {"data": [{"Email": email}]}
    try:
        response = requests.post(SHEETDB_URL, json=data)
    except Exception:
        st.warning("Could not save email to database.")

def generate_pdf(content, email, role, state):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 40
    y = height - 40

    disclaimer = (
        "Disclaimer: This lease analysis is for educational and informational purposes only and "
        "does not constitute legal advice. Always consult with a qualified attorney for legal guidance."
    )

    pdf.setFont("Helvetica", 10)
    pdf.drawString(x_margin, y, f"{state} Lease Analysis for: {email} ({role})")
    y -= 20

    for line in wrap(disclaimer, 95):
        pdf.drawString(x_margin, y, line)
        y -= 12

    y -= 20
    for line in content.split("\n"):
        for wrapped in wrap(line, 95):
            if y < 50:
                pdf.showPage()
                y = height - 40
                pdf.setFont("Helvetica", 10)
            pdf.drawString(x_margin, y, wrapped)
            y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer

# App Start
st.title("Lease Analyzer")
state = st.selectbox("Which state is this lease for?", ["New Jersey", "Pennsylvania"])
role = st.radio("Who are you reviewing this lease as?", ["Tenant", "Landlord"])
email = st.text_input("Enter your email to receive one free analysis (required):")
uploaded_file = st.file_uploader("Choose a lease PDF", type="pdf")

st.sidebar.markdown("📚 **Helpful Resources**")
if state == "New Jersey":
    st.sidebar.markdown("""
- [NJ Truth-in-Renting Guide](https://www.nj.gov/dca/divisions/codes/publications/pdf_lti/truth_in_renting.pdf)
- [NJ Tenant Info](https://www.nj.gov/dca/divisions/codes/offices/landlord_tenant_information.html)
""")
else:
    st.sidebar.markdown("""
- [PA Tenant Rights Guide](https://www.attorneygeneral.gov/wp-content/uploads/2018/01/Tenant_Rights.pdf)
- [PA Legal Aid](https://www.palawhelp.org/issues/housing/landlord-and-tenant-law)
""")

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

                    rules = {
                        "New Jersey": """
- Security deposit must not exceed 1.5 months' rent.
- Lease must allow tenant the right to a habitable space.
- 30 days' notice required for rent increase.
- Self-help eviction is illegal.
- Deposit must be returned in 30 days.
- Repairs must be made timely.
- Utilities responsibility must be clear.
- Entry notice required.
- Illegal to waive habitability or legal process.
- Lease must clarify renewal or termination.
""",
                        "Pennsylvania": """
- Max 2 months' deposit in year one.
- Deposit returned in 30 days w/ itemization.
- Habitable condition is required.
- Landlord must maintain common areas.
- Pre-1978: lead paint disclosure required.
- Entry with notice unless emergency.
- No self-help eviction allowed.
- Lease must explain termination rules.
"""
                    }

                    prompt = f"""
You are a legal assistant trained in {state} tenant law.
The user reviewing this lease is a {role.lower()}.
Your job is to review the lease and list only the issues found OR items that comply.

Use this format:
- ⚠️ Potential Issue: ...
- ✅ Compliant: ...

{rules[state]}
LEASE TEXT:
{lease_text}
"""

                    try:
                        st.info("📡 Sending request to OpenAI...")
                        response = openai.ChatCompletion.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.2,
                            max_tokens=800
                        )
                        st.success("✅ OpenAI responded.")
                    except Exception:
                        st.error("🚫 Unexpected error contacting OpenAI. Please try again later.")
                        st.stop()

                    result = response.choices[0].message.content.strip()
                    lines = list(dict.fromkeys([line.strip() for line in result.split("\n") if line.strip()]))
                    cleaned_result = "\n".join(lines)

                    st.subheader("Analysis:")
                    st.markdown(cleaned_result)

                    full_txt = (
                        "Disclaimer: This lease analysis is for educational and informational purposes only and "
                        "does not constitute legal advice.\n\n" + cleaned_result
                    )

                    st.download_button("📥 Download as Text", data=full_txt, file_name="lease_analysis.txt")
                    st.download_button("📄 Download as PDF", data=generate_pdf(cleaned_result, email, role, state),
                                       file_name="lease_analysis.pdf", mime="application/pdf")

# Footer
st.markdown("""
---
🔒 **Disclaimer**  
This tool is for educational and informational purposes only and does not constitute legal advice.  
Always consult with a qualified attorney.

🔐 **Privacy Notice**  
We do not store lease documents or analysis results. Only your email is saved to verify access.
---
""")
