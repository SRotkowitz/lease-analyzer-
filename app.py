import streamlit as st
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from textwrap import wrap
import time

# Set Streamlit page configuration
st.set_page_config(page_title="Lease Analyzer", page_icon="📄", layout="centered")

# Load OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

# Functions (same as your version)
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

# UI layout improvement
st.markdown("<h1 style='text-align:center;'>📄 NJ/PA Lease Risk Checker</h1>", unsafe_allow_html=True)
st.markdown("Upload your lease. Our AI checks for legal red flags — fast, free, and private.")

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

# Add a trust panel
with st.expander("🔐 Privacy & Legal Notes"):
    st.markdown("""
    - We do **not** store your lease files.
    - Only your email is saved for access tracking.
    - This tool is **not legal advice** — it’s an automated review based on state rules.
    """)

# Show helpful resources
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
