import streamlit as st

# Create a sidebar selection
selection = st.sidebar.radio(
    "Test page hiding",
    ["Show all pages", "Hide pages 1 and 2", "Hide Other apps Section"],
)
