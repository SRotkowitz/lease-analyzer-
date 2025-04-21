import streamlit as st
import PyPDF2

st.title("NJ Lease Analyzer")
st.write("Upload a lease PDF to get started.")

uploaded_file = st.file_uploader("Choose a lease PDF", type="pdf")

if uploaded_file is not None:
    # Read and extract text from the PDF
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    lease_text = ""
    for page in pdf_reader.pages:
        lease_text += page.extract_text() or ""

    st.subheader("Extracted Text:")
    st.text_area("Lease Text", lease_text, height=300)

import openai

# After extracting lease_text...
    st.subheader("Extracted Text:")
    st.text_area("Lease Text", lease_text, height=300)

    # Button to run analysis
    if st.button("Analyze Lease"):
        with st.spinner("Analyzing lease using NJ tenant law..."):

            # Sample rules (you can expand later)
            nj_rules = """
- Security deposit must not exceed 1.5 months’ rent.
- Lease must allow tenant the right to a habitable space.
- Landlord must give 30 days’ notice for rent increases on month-to-month leases.
- Self-help eviction is illegal in NJ.
- Security deposit must be returned within 30 days of lease end.
"""

            # Create prompt
            prompt = f"""
You are a legal assistant trained in New Jersey tenant law.
Review this lease text and compare it to the NJ rules below.
List
