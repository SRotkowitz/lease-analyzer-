# app.py

import streamlit as st
from io import BytesIO
import PyPDF2
from openai import OpenAI, RateLimitError
import requests
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from PIL import Image
import time
import pandas as pd
import json
import re

# === helpers ===
EMOJI = {"critical": "🔴", "warning": "🟡", "compliant": "🟢"}

def issues_to_bullets(issues):
    bullets = []
    for it in issues:
        sev = (it.get("severity") or "").lower()
        check = (it.get("check") or "").strip()
        finding = (it.get("finding") or "").strip()
        why = (it.get("why") or "").strip()
        bullets.append(f"- {EMOJI.get(sev, '•')} {sev.title()}: {check} — {finding}. {why}")
    return "\n".join([b for b in bullets if b.strip()])

def issues_to_rows(issues):
    """Turn issues into (Severity, Item) rows for table/PDF."""
    rows = []
    for it in issues:
        sev = (it.get("severity") or "").capitalize()
        check = (it.get("check") or "").strip()
        finding = (it.get("finding") or "").strip()
        why = (it.get("why") or "").strip()
        text = f"{check} — {finding}. {why}".strip(" .")
        rows.append((sev, text))
    return rows

def count_by_severity(issues):
    crit = sum(1 for i in issues if (i.get("severity") or "").lower() == "critical")
    warn = sum(1 for i in issues if (i.get("severity") or "").lower() == "warning")
    comp = sum(1 for i in issues if (i.get("severity") or "").lower() == "compliant")
    return crit, warn, comp

# --- PAGE CONFIG ---
st.set_page_config(page_title="NJ Lease Shield — Landlord Compliance Analyzer", layout="centered")

# --- Global app border (works across Streamlit versions) ---
st.markdown(
    """
    <style>
    div[data-testid="stAppViewContainer"] { padding: 12px; background: #f5f5f5; }
    div.block-container,
    section.main > div.block-container,
    div[data-testid="stAppViewContainer"] .block-container {
        border: 3px solid #2E8B57;
        border-radius: 16px;
        padding: 24px !important;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

# --- Green promo box above CTA ---
st.markdown("""
<div style='background-color:#90EE90; padding: 20px; border-radius: 10px; border: 1px solid #2E8B57; text-align: center; margin-top: 20px;'>
  <h4 style='margin-bottom: 10px;'>📄 Upload Your Lease Now</h4>
  <p style='font-size: 16px; margin-top: 0;'>We’ll scan it for red flags based on NJ law.<br>No signup required.</p>
</div>
""", unsafe_allow_html=True)

# --- Start Lease Check (native primary button, centered) ---
st.markdown("<div style='text-align:center; margin: 30px 0;'>", unsafe_allow_html=True)
if st.button("🚀 Start Lease Check", key="cta_start", type="primary", use_container_width=False):
    log_user_action("anonymous", "Clicked Start Lease Check")
    st.session_state.scroll_to_form = True
st.markdown("</div>", unsafe_allow_html=True)

# --- SAMPLE LEASE REPORT ---
if st.session_state.get("scroll_to_form"):
    st.markdown("---")
    st.markdown("### 👀 Try a Sample Lease")
    if st.button("🧾 View Sample Lease Report", type="secondary"):
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
# === STEP 2: UPLOAD FORM with METADATA ===
# =========================
if st.session_state.get("scroll_to_form"):
    st.markdown("### Step 1: Upload Your Lease")

    with st.form("lease_upload_form"):
        colA, colB = st.columns(2)
        with colA:
            state = st.selectbox("Which state?", ["New Jersey"])
        with colB:
            role = st.radio("You are a:", ["Landlord", "Property Manager", "Tenant"], index=0)

        property_address = st.text_input("Property Address (optional)")
        num_units = st.number_input("Number of Units", min_value=1, step=1, value=1)
        year_built = st.number_input("Year Built (optional, helps lead-paint checks)", min_value=1800, max_value=2100, value=1975, step=1)

        uploaded_file = st.file_uploader("Upload Lease (PDF or DOCX)", type=["pdf", "docx"])
        submitted = st.form_submit_button("🔍 Analyze Lease", type="primary")

    if uploaded_file and submitted:
        # Extract text
        lease_text = ""
        try:
            if uploaded_file.name.lower().endswith(".pdf"):
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    lease_text += page.extract_text() or ""
            else:
                st.warning("DOCX support is limited in this version. Please upload a PDF for the best results.")
        except Exception as e:
            st.error(f"Could not read file: {e}")
            st.stop()

        log_user_action("anonymous", "Uploaded Lease")

        # --- HYBRID QUICK CHECKS (deterministic preflags) ---
        quick_flags = []
        # Confession of judgment (often unenforceable)
        if re.search(r"confession of judgment", lease_text, re.I):
            quick_flags.append({"severity": "critical", "check": "Illegal/Unenforceable Clause",
                                "finding": "Confession of judgment language detected",
                                "why": "Likely unenforceable in NJ"})
        # Unlimited/anytime entry
        if re.search(r"(any\s*time|at\s*any\s*time).{0,30}enter", lease_text, re.I):
            quick_flags.append({"severity": "warning", "check": "Landlord Entry",
                                "finding": "Unlimited/anytime entry language",
                                "why": "Entry should include reasonable notice except emergencies"})
        # Security deposit vs rent (simple heuristic)
        m_dep = re.search(r"security\s+deposit[^$]*(\$[\d,]+|\d{3,6})", lease_text, re.I)
        m_rent = re.search(r"rent[^$]*\$?([\d,]+)\s*/\s*month", lease_text, re.I)
        try:
            if m_dep and m_rent:
                dep_str = re.search(r"([\d,]+)", m_dep.group(0)).group(1)
                dep = float(dep_str.replace(",", ""))
                rent = float(m_rent.group(1).replace(",", ""))
                if dep > 1.5 * rent:
                    quick_flags.append({"severity": "critical", "check": "Security Deposit Cap",
                                        "finding": f"Deposit ${dep:.0f} exceeds 1.5× monthly rent (${1.5*rent:.0f})",
                                        "why": "NJ cap = 1.5 months"})
        except:
            pass
        # Lead paint disclosure check using year_built
        if year_built and year_built < 1978 and "lead" not in lease_text.lower():
            quick_flags.append({"severity": "warning", "check": "Lead-Based Paint Disclosure",
                                "finding": "Disclosure not found in text",
                                "why": "Required for pre-1978 units"})

        # --- STRICT STRUCTURED ANALYSIS (JSON-only) ---
        SYSTEM_MSG = {
            "role": "system",
            "content": (
                "You are a compliance assistant for New Jersey residential leases. "
                "Return JSON ONLY that conforms to this schema:\n"
                "{"
                "  'issues': ["
                "    {'severity':'critical|warning|compliant', 'check':'string', 'finding':'string', 'why':'string'}"
                "  ]"
                "}\n"
                "No prose. No headings. No extra keys."
            ),
        }

        USER_MSG = {
            "role": "user",
            "content": f"""
Analyze the LEASE TEXT for compliance with the NJ checklist below.
Focus on landlord exposure (fines, lawsuits, unenforceable clauses, missing disclosures).
Return JSON only, following the schema exactly. No lease quotes, no extra commentary.

CHECKLIST (NJ):
{NJ_RULES}

LEASE TEXT:
{lease_text}
"""
        }

        with st.spinner("Analyzing lease..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[SYSTEM_MSG, USER_MSG],
                    temperature=0.1,
                    max_tokens=900
                )
                raw = response.choices[0].message.content or "{}"
            except RateLimitError:
                st.error("Too many requests. Please wait and try again.")
                st.stop()

        # Parse JSON with safe fallback
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raw2 = raw.strip().strip("`").replace("json", "")
            try:
                data = json.loads(raw2)
            except:
                data = {"issues": []}

        issues = data.get("issues", [])
        # Merge quick flags
        issues.extend(quick_flags)

        # === DISPLAY ===
        st.markdown("### 📊 Step 2: Lease Analysis Results")
        st.write(f"📍 **Property:** {property_address or 'N/A'}  |  🏢 **Units:** {num_units}  |  🧑 **Role:** {role}  |  🏗️ **Year Built:** {year_built or 'N/A'}")

        # Summary badge
        crit, warn, comp = count_by_severity(issues)
        st.markdown(
            f"""
            <div style='background-color:#f7f7f7; padding:12px; border-radius:10px; 
                        border:1px solid #ddd; margin:10px 0;'>
              <b>Compliance Summary</b><br>
              🔴 <b>Critical:</b> {crit} &nbsp;&nbsp;
              🟡 <b>Warnings:</b> {warn} &nbsp;&nbsp;
              🟢 <b>Compliant:</b> {comp}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Table view
        rows = issues_to_rows(issues)
        if rows:
            df = pd.DataFrame(rows, columns=["Severity", "Item"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No items parsed into table.")

        # Bullets (nice for quick scan)
        bullets = issues_to_bullets(issues)
        if bullets:
            st.markdown(bullets)
        else:
            st.warning("No findings returned. Try a different lease or re-run analysis.")

        st.markdown("ℹ️ This analysis is for informational purposes only and does not constitute legal advice.")

        # === EMAIL → PDF DELIVERY (table layout) ===
        email = st.text_input("Enter your email to download this report as a PDF:")
        if email and "@" in email and "." in email:
            save_email(email)
            log_user_action(email, "Downloaded PDF Report")

            def generate_pdf(issues_list, email, role, state, property_address, num_units, year_built):
                buffer = BytesIO()
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=letter,
                    leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
                )
                styles = getSampleStyleSheet()
                elements = [
                    Paragraph("NJ Lease Compliance Report", styles["Heading1"]),
                    Paragraph(f"State: {state}", styles["Normal"]),
                    Paragraph(f"User: {email} ({role})", styles["Normal"]),
                    Paragraph(f"Property: {property_address or 'N/A'} | Units: {num_units} | Year Built: {year_built}", styles["Normal"]),
                    Spacer(1, 12)
                ]
                table_rows = issues_to_rows(issues_list)
                data = [["Severity", "Item"]]
                for sev, item in table_rows:
                    data.append([sev, item])

                if len(data) > 1:
                    tbl = Table(data, colWidths=[90, 420])
                    tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f0f0")),
                        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
                        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                        ("ALIGN", (0,0), (0,-1), "LEFT"),
                        ("VALIGN", (0,0), (-1,-1), "TOP"),
                        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
                        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
                    ]))
                    elements.append(tbl)
                else:
                    elements.append(Paragraph("No findings to report.", styles["Normal"]))

                elements.append(Spacer(1, 12))
                elements.append(Paragraph("Note: This report is informational and not legal advice.", styles["Italic"]))

                doc.build(elements)
                buffer.seek(0)
                return buffer

            pdf_data = generate_pdf(issues, email, role, state, property_address, num_units, year_built)
            st.download_button("📄 Download Lease Analysis as PDF", pdf_data, "lease_analysis.pdf", type="primary")

st.divider()

# --- Light trust box (kept) ---
st.markdown("""
<div style='background-color: #e6f2ff; padding: 16px; border-radius: 10px; border: 1px solid #99c2ff; margin-top: 10px;'>
  <strong>✅ Created by NJ & PA-Trained Legal Professionals</strong><br>
  Trusted by over <strong>1,200+ landlords and tenants</strong> to flag risky or illegal lease clauses.<br><br>
  Fast. Confidential. No documents stored.
</div>
""", unsafe_allow_html=True)

st.divider()

# --- Testimonials ---
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

# Testimonial button (native secondary, subtle)
st.markdown('<div style="text-align:center;">', unsafe_allow_html=True)
if st.button("Next Testimonial", key="testimonial_next", type="secondary"):
    st.session_state.testimonial_index = (st.session_state.testimonial_index + 1) % len(testimonials)
st.markdown("</div>", unsafe_allow_html=True)

# --- Disclaimer (yellow) ---
st.markdown("""
<div style='background-color: #FFF8DC; padding: 16px; border-radius: 10px; 
            border: 1px solid #FFD700; margin-top: 30px; font-size: 14px;'>
  <strong>Disclaimer:</strong> This lease analysis is for informational purposes only and does not constitute legal advice.<br>
  <strong>Privacy:</strong> We do not store your documents or results. Only your email is recorded temporarily for usage tracking.
</div>
""", unsafe_allow_html=True)
