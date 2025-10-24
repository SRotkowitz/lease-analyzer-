# app.py

import streamlit as st
from io import BytesIO
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from PIL import Image
import time

# --- PAGE CONFIG (keep only one set_page_config) ---
st.set_page_config(page_title="NJ Lease Shield — Landlord Compliance Analyzer", layout="centered")  # NEW: unified title

# === NJ LANDLORD COMPLIANCE RULES (used in prompt) ===
NJ_RULES = """
Check the lease for these New Jersey compliance areas and report clearly:

1) Required Disclosures:
   - Lead-based paint disclosure for pre-1978 units
   - NJ Truth-in-Renting Guide acknowledgement (where applicable)

2) Security Deposit:
   - Max 1.5 months’ rent cap
   - Interest handling & receipt timelines

3) Late Fees & Rent Increases:
   - Late fee must be stated and reasonable (no vague “unspecified” amounts)
   - Rent increase notice periods and any local rent control considerations

4) Habitability & Repairs:
   - Landlord’s duty to maintain habitable premises cannot be waived
   - Repair responsibilities appear reasonable and lawful

5) Landlord Entry:
   - Reasonable notice for non-emergency entry (typically 24 hours)
   - No unlimited/anytime entry language

6) Anti-Waiver / Illegal Clauses:
   - No clauses that waive statutory rights or court access
   - No “confession of judgment” or patently unenforceable penalties

7) Subletting / Assignment:
   - Terms must be reasonable and not blanket-prohibited if unlawful locally

8) Termination & Notice Periods:
   - Clear, lawful notice periods; no one-sided rights that violate NJ rules

9) Dispute Resolution:
   - Arbitration/venue clauses must be reasonable and not strip core rights

10) Miscellaneous Compliance:
   - Smoking, pets, parking, utilities — ensure terms do not violate NJ law or local ordinances
"""

# --- HERO / POSITIONING ---
st.title("NJ Lease Shield — Landlord Compliance Analyzer")
st.caption("Upload your lease to flag legal risks and missing notices — in minutes.")
st.markdown("**For:** Landlords & Property Managers in New Jersey (PA coming soon)")
st.info(
    "This tool provides an automated compliance summary based on NJ laws and public resources. "
    "It is **not** legal advice.",
    icon="ℹ️"
)
st.divider()

# (Optional) Persona switch — persisted for later logic
persona = st.radio("I am a:", ["Landlord", "Property Manager", "Tenant"], index=0, horizontal=True)
st.session_state["persona"] = persona

# --- CONFIG ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SHEETDB_URL = "https://sheetdb.io/api/v1/ga5o59cph77t9"

# --- LOGGING FUNCTIONS ---
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
try:
    banner = Image.open("banner.png")
    st.image(banner, use_container_width=True)
except Exception:
    pass  # banner is optional; don't break if missing

# --- TRUST BOX (kept) ---
st.markdown("""
<div style='background-color: #e6f2ff; padding: 16px; border-radius: 10px; border: 1px solid #99c2ff; margin-top: 10px;'>
  <strong>✅ Created by NJ & PA-Trained Legal Professionals</strong><br>
  Trusted by over <strong>1,200+ landlords and tenants</strong> to flag risky or illegal lease clauses.<br><br>
  Fast. Confidential. No documents stored.
</div>
""", unsafe_allow_html=True)

# --- SCROLL TO FORM CTA (kept) ---
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

# --- SAMPLE LEASE REPORT (kept) ---
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

# =========================
# === STEP 2: UPLOAD FORM with METADATA (NEW) ===
# =========================
if st.session_state.scroll_to_form:
    st.markdown("### Step 1: Upload Your Lease")

    with st.form("lease_upload_form"):  # NEW: consolidated form
        colA, colB = st.columns(2)
        with colA:
            # Narrow scope to NJ for now; PA soon (you can add back later)
            state = st.selectbox("Which state?", ["New Jersey"])  # NEW
        with colB:
            role = st.radio("You are a:", ["Landlord", "Property Manager", "Tenant"], index=0)  # NEW default to landlord

        # NEW: simple property metadata for organization
        property_address = st.text_input("Property Address (optional)")  # NEW
        num_units = st.number_input("Number of Units", min_value=1, step=1, value=1)  # NEW

        # Allow PDF or DOCX to reduce friction
        uploaded_file = st.file_uploader("Upload Lease (PDF or DOCX)", type=["pdf", "docx"])  # NEW

        submitted = st.form_submit_button("🔍 Analyze Lease")

    if uploaded_file and submitted:
        # Extract text (PDF path shown; DOCX can be added later)
        lease_text = ""
        try:
            if uploaded_file.name.lower().endswith(".pdf"):
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    lease_text += page.extract_text() or ""
            else:
                # Minimal DOCX fallback: instruct user to upload PDF for now
                st.warning("DOCX support is limited in this version. Please upload a PDF for the best results.")
        except Exception as e:
            st.error(f"Could not read file: {e}")
            st.stop()

        log_user_action("anonymous", "Uploaded Lease")

        # --- RULES / PROMPT (kept but slightly reframed) ---
        # You can replace "..." with your real NJ rule text later
        rules = {"New Jersey": "..."}
        # Reframe: make it compliance/liability oriented when role != Tenant
        lens = "landlord compliance and liability" if role in ["Landlord", "Property Manager"] else "tenant rights and protections"  # NEW

        prompt = f"""
# --- RULES / PROMPT (landlord-compliance tuned) ---
state = "New Jersey"  # we’re scoped to NJ for now
lens = "landlord compliance and liability" if role in ["Landlord", "Property Manager"] else "tenant rights and protections"

prompt = f"""
You are a legal assistant trained in {state} {lens}.
The user is a {role.lower()} reviewing a residential lease in {state}.
Analyze the LEASE TEXT for compliance with the checklist below.
Respond ONLY in this format, using the exact emoji and labels:

- 🔴 Critical Risk: [one-line description of the problem + why it’s unlawful or high-risk]
- 🟡 Warning: [one-line description of likely unenforceable/weak or needs clarification]
- 🟢 Compliant: [one-line description of a clause that appears compliant]

Rules for output:
- Be concise. One line per bullet.
- No long paragraphs. No legal citations unless necessary for clarity.
- If a category is not present, do NOT fabricate it—just omit.
- Prioritize landlord exposure (fines, lawsuits, unenforceable clauses, disclosures).

CHECKLIST (NJ):
{NJ_RULES}

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
                # NEW: show context so PMs can tie report to a property
                st.write(f"📍 **Property:** {property_address or 'N/A'}  |  🏢 **Units:** {num_units}  |  🧑 **Role:** {role}")  # NEW
                st.markdown(cleaned_result)
                
                # === MINI-STEP: COMPLIANCE SUMMARY BADGE ===
                # Count how many risks and compliant clauses the AI returned
                critical_count = cleaned_result.count("🔴")
                warning_count = cleaned_result.count("🟡")
                compliant_count = cleaned_result.count("🟢")
                
                # Display a summary banner
                st.markdown(
                    f"""
                    <div style='background-color:#f7f7f7; padding:12px; border-radius:10px; 
                                border:1px solid #ddd; margin-bottom:10px;'>
                      <b>Compliance Summary</b><br>
                      🔴 <b>Critical:</b> {critical_count} &nbsp;&nbsp;
                      🟡 <b>Warnings:</b> {warning_count} &nbsp;&nbsp;
                      🟢 <b>Compliant:</b> {compliant_count}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("ℹ️ This analysis is for informational purposes only and does not constitute legal advice.")

                # === EMAIL → PDF DELIVERY (kept) ===
                email = st.text_input("Enter your email to download this report as a PDF:")
                if email and "@" in email and "." in email:
                    save_email(email)
                    log_user_action(email, "Downloaded PDF Report")

                    def generate_pdf(content, email, role, state, property_address, num_units):
                        buffer = BytesIO()
                        doc = SimpleDocTemplate(buffer, pagesize=letter)
                        styles = getSampleStyleSheet()
                        elements = [
                            Paragraph("Lease Analysis Report", styles["Heading1"]),
                            Paragraph(f"State: {state}", styles["Normal"]),
                            Paragraph(f"User: {email} ({role})", styles["Normal"]),
                            Paragraph(f"Property: {property_address or 'N/A'} | Units: {num_units}", styles["Normal"]),
                            Spacer(1, 12)
                        ]
                        for line in content.split("\n"):
                            elements.append(Paragraph(line, styles["Normal"]))
                        doc.build(elements)
                        buffer.seek(0)
                        return buffer

                    pdf_data = generate_pdf(cleaned_result, email, role, state, property_address, num_units)  # NEW: pass metadata
                    st.download_button("📄 Download Lease Analysis as PDF", pdf_data, "lease_analysis.pdf")
            except RateLimitError:
                st.error("Too many requests. Please wait and try again.")

# --- TESTIMONIAL ROTATION (kept) ---
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

st.markdown("""
**Disclaimer:** This lease analysis is for informational purposes only and does not constitute legal advice.  
**Privacy:** We do not store your documents or results. Only your email is recorded temporarily for usage tracking.
""")
