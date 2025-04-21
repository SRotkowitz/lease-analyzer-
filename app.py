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
