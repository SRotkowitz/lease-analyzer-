import streamlit as st
import PyPDF2
import openai
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textwrap import wrap

# 🔧 TEMP: Hardcoded key for debug
openai.api_key = "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"  # Replace this with your real key

# ✅ TEST OpenAI connection
try:
    test_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Test"}]
    )
    st.success("✅ GPT is working: " + test_response.choices[0].message.content)
except Exception as e:
    st.error("❌ GPT test failed: " + str(e))

SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

def email_already_used(email):
    try:
        response = requests.get(f"{SHEETDB_URL}/search?Email={email}")
        return response.status_code == 200 and len(response.json()) > 0
    except:
        return False

def save_email(email):
    try:
        requests.post(SHEETDB_URL, json={"data": [{"Email": email}]})
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
        "does not constitute legal advice. Always consult with a qualified attorney."
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

# Streamlit App
st.title("Lease Analyzer")
state = st.selectbox("Which state is this lease for?", ["New Jersey", "Pennsylvania"])
role = st.radio("Who are you reviewing this lease as?", ["Tenant", "Landlord"])
email = st.text_input("Enter your email to receive one free analysis (required):")
uploaded_file = st.file_uploader("Choose a lease PDF", type="pdf")

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
                        "New Jersey": "- Max 1.5 months deposit\n- 30 days notice for rent changes\n- Must return deposit in 30 days\n- Entry requires notice\n- Habitable condition required",
                        "Pennsylvania": "- Max 2 months deposit (year 1)\n- Return deposit in 30 days with itemization\n- Must maintain safe conditions\n- Entry notice required\n- Self-help eviction illegal"
                    }

                    prompt = f"""
You are a legal assistant trained in {state} tenant law.
The user is a {role.lower()}.
Please list any potential issues or compliant terms.

Rules to check:
{rules[state]}

LEASE TEXT:
{lease_text}
"""

                    try:
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.2,
                            max_tokens=800
                        )
                        analysis = response.choices[0].message.content.strip()
                        st.subheader("Analysis")
                        st.markdown(analysis)

                        full_text = "Disclaimer: This lease analysis is for educational use only.\n\n" + analysis
                        st.download_button("📥 Download as Text", data=full_text, file_name="lease_analysis.txt")
                        st.download_button("📄 Download as PDF", data=generate_pdf(analysis, email, role, state), file_name="lease_analysis.pdf", mime="application/pdf")

                    except Exception as e:
                        st.error("❌ GPT request failed: " + str(e))

st.markdown("---\n🔒 **Privacy Note:** We only save your email to verify access. No files or analysis are stored.\n---")
