import streamlit as st
import PyPDF2
from openai import OpenAI

# Set your OpenAI API key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("NJ Lease Analyzer")
st.write("Upload a lease PDF to get started.")
st.markdown("""
---
🔒 **Disclaimer:**  
This tool is for **educational and informational purposes only** and does **not constitute legal advice**.  
Always consult with a qualified attorney for legal guidance related to your lease or rental situation.
---
""")


uploaded_file = st.file_uploader("Choose a lease PDF", type="pdf")

if uploaded_file is not None:
    # Read and extract text from the PDF
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    lease_text = ""
    for page in pdf_reader.pages:
        lease_text += page.extract_text() or ""

    st.subheader("Extracted Text:")
    st.text_area("Lease Text", lease_text, height=300)

    # Button to run analysis
    if st.button("Analyze Lease"):
        with st.spinner("Analyzing lease using NJ tenant law..."):
            nj_rules = """
- Security deposit must not exceed 1.5 months’ rent.
- Lease must allow tenant the right to a habitable space.
- Landlord must give 30 days’ notice for rent increases on month-to-month leases.
- Self-help eviction is illegal in NJ.
- Security deposit must be returned within 30 days of lease end.
"""

            prompt = f"""
You are a legal assistant trained in New Jersey tenant law.

Your task is to review the lease text and identify whether it complies with the NJ tenant rules below.

Return the output using this format:

- ⚠️ **Potential Issue:** [short description]
- ✅ **Compliant:** [short description]

Do NOT explain or include references. Just list the issue or compliance in this simple bullet format.

Only list each item once. Do not repeat or summarize. Do not restate the list again at the end. Do not include anything after the last bullet point. Your response must end immediately after the last item.

Do not include any titles like "Analysis" in your response. Just start with the first bullet point.

NJ RULES:
{nj_rules}

LEASE TEXT:
{lease_text}
"""

            # GPT-4 API call
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600
            )

            result = response.choices[0].message.content

            # Remove duplicate lines
            lines = result.strip().split("\n")
            seen = set()
            cleaned_lines = []

            for line in lines:
                line = line.strip()
                if line and line not in seen:
                    seen.add(line)
                    cleaned_lines.append(line)

            cleaned_result = "\n".join(cleaned_lines)

        st.subheader("Analysis:")
        st.markdown(cleaned_result)
