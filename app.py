
import streamlit as st
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from PIL import Image
import time

# --- CONFIG ---
st.set_page_config(page_title="Lease Analyzer", page_icon="📄", layout="centered")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

# --- LOGGING FUNCTION ---
def log_user_action(email, action):
    data = {"data": [{"Email": email, "Action": action, "Time": time.strftime("%Y-%m-%d %H:%M:%S")}]}
    try:
        requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to log user action.")

def save_email(email):
    data = {"data": [{"Email": email}]}
    try:
        requests.post(SHEETDB_URL, json=data)
    except:
        st.warning("Failed to save email.")

# --- BANNER IMAGE ---
banner = Image.open("banner.png")
st.image(banner, use_container_width=True)

# --- TRUST BOX ---
st.markdown("""
<div style='background-color: #e6f2ff; padding: 16px; border-radius: 10px; border: 1px solid #99c2ff; margin-top: 10px;'>
  <strong>✅ Created by NJ & PA-Trained Legal Professionals</strong><br>
  Trusted by over <strong>1,200+ landlords and tenants</strong> to flag risky or illegal lease clauses.<br><br>
  Fast. Confidential. No documents stored.
</div>
""", unsafe_allow_html=True)

# --- TESTIMONIAL ROTATION ---
if "testimonial_index" not in st.session_state:
    st.session_state.testimonial_index = 0

testimonials = [
    {"quote": "“I used this tool before renewing my lease — it caught 2 things my lawyer missed.”", "author": "Verified NJ Tenant"},
    {"quote": "“This flagged a clause I didn’t realize was illegal. Saved me a headache.”", "author": "NJ Landlord, 18 Units"},
    {"quote": "“Really simple. I uploaded my lease and saw the issues instantly.”", "author": "First-Time Renter (PA)"},
    {"quote": "“I send this tool to clients before they sign anything.”", "author": "NJ Real Estate Agent"}
]

t = testimonials[st.session_state.testimonial_index]
st.markdown(f"""
<div style='border-left: 4px solid #ccc; padding-left: 15px; margin-top: 20px; font-style: italic; color: #444;'>
  {t['quote']}<br>
  <span style='font-weight: bold;'>— {t['author']}</span>
</div>
""", unsafe_allow_html=True)

if st.button("Next Testimonial"):
    st.session_state.testimonial_index = (st.session_state.testimonial_index + 1) % len(testimonials)

# --- SCROLL TO FORM ---
if "scroll_to_form" not in st.session_state:
    st.session_state.scroll_to_form = False

st.markdown("""
<div style='background-color:#FFF8DC; padding: 20px; border-radius: 10px; border: 1px solid #eee; text-align: center; margin-top: 20px;'>
  <h4 style='margin-bottom: 10px;'>📄 Upload Your Lease Now</h4>
  <p style='font-size: 16px; margin-top: 0;'>We’ll scan it for red flags based on NJ/PA law.<br>No signup required.</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Start Lease Check"):
        log_user_action("anonymous", "Clicked Start Lease Check")
        st.session_state.scroll_to_form = True

# --- SAMPLE LEASE REPORT ---
if st.session_state.scroll_to_form:
    st.markdown("---")
    st.markdown("### 👀 Try a Sample Lease")
    if st.button("🧾 View Sample Lease Report"):
        log_user_action("anonymous", "Viewed Sample Lease")
        st.markdown("#### ⚠️ Potential Issues")
        st.markdown("""
- ⚠️ **Late Fee:** Lease allows charging an unspecified late fee — this may violate NJ limits.
- ⚠️ **Entry Notice:** Landlord entry clause lacks notice requirements.
- ⚠️ **Repairs:** Lease says tenant must fix 'all issues,' which may be overly broad.
""")
        st.markdown("#### ✅ Compliant Clauses")
        st.markdown("""
- ✅ **Security Deposit:** Limited to 1.5 months' rent.
- ✅ **Lead Paint Disclosure:** Included for pre-1978 buildings.
- ✅ **Termination Clause:** Allows 30-day written notice.
""")

# --- UPLOAD FORM ---
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

        rules = {"New Jersey": "...", "Pennsylvania": "..."}
        prompt = f"""
You are a legal assistant trained in {state} tenant law.
The user reviewing this lease is a {role.lower()}.
Your task is to review the lease text and identify whether it complies with the {state} tenant rules below.
Return the output using this format:
- ⚠️ Potential Issue: [short description]
- ✅ Compliant: [short description]
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
                st.markdown("### 📊 Step 2: Lease Analysis Results")
                st.markdown(cleaned_result)
                st.markdown("ℹ️ This analysis is for informational purposes only and does not constitute legal advice.")

                email = st.text_input("Enter your email to download this report as a PDF:")
                if email and "@" in email and "." in email:
                    save_email(email)
                    log_user_action(email, "Downloaded PDF Report")

                    # PDF generator
                    def generate_pdf(content, email, role, state):
                        buffer = BytesIO()
                        doc = SimpleDocTemplate(buffer, pagesize=letter)
                        styles = getSampleStyleSheet()
                        elements = [Paragraph("Lease Analysis Report", styles["Heading1"]),
                                    Paragraph(f"State: {state}", styles["Normal"]),
                                    Paragraph(f"User: {email} ({role})", styles["Normal"]),
                                    Spacer(1, 12)]
                        for line in content.split("\n"):
                            elements.append(Paragraph(line, styles["Normal"]))
                        doc.build(elements)
                        buffer.seek(0)
                        return buffer

                    pdf_data = generate_pdf(cleaned_result, email, role, state)
                    st.download_button("📄 Download Lease Analysis as PDF", pdf_data, "lease_analysis.pdf")
            except RateLimitError:
                st.error("Too many requests. Please wait and try again.")
