import streamlit as st

# Custom CSS to remove button border
hide_button_border_css = """
<style>
/* Target the button element by its class or data-testid */
/* You might need to inspect your button's element in the browser's developer tools
   to find the correct class or data-testid for more specific targeting. */
button {
    border: none !important;
}

/* Optional: Remove the focus outline as well, if desired */
button:focus {
    outline: none !important;
    box-shadow: none !important;
}
</style>
"""

# Inject the CSS into the Streamlit app
st.markdown(hide_button_border_css, unsafe_allow_html=True)

st.button("My Button")