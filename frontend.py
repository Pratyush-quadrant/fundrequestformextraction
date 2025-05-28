import streamlit as st
import os
from main import upload_and_process_file

st.set_page_config(page_title="Goodwill Foundation – Fund Requisition Portal")
st.title("Goodwill Foundation – Fund Requisition Portal")


if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None

uploaded_file = st.file_uploader("Upload your Fund Requisition Form (PDF only)", type=["pdf"])

if uploaded_file is not None:
    if uploaded_file.type != "application/pdf":
        st.error("Only PDF files are allowed. Please upload a valid PDF.")
    else:
        # Save file temporarily
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.uploaded_filename = uploaded_file.name

        # Only process if not already processed
        if st.session_state.extracted_data is None:
            extracted = upload_and_process_file(uploaded_file.name)
            st.session_state.extracted_data = extracted

        st.success("Your fund requisition has been uploaded. If your requisition qualifies, our team will reach out to you.")

        # Show extracted data in the app
        if st.session_state.extracted_data:
            st.subheader("Extracted Data from PDF")
            st.json(st.session_state.extracted_data)

        # Clean up file
        os.remove(uploaded_file.name)

else:
    # Reset extracted data if no file is uploaded
    st.session_state.extracted_data = None
    st.session_state.uploaded_filename = None
