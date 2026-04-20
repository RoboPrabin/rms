from time import sleep
import streamlit as st
from service.mail_cleaner import MailCleaner


st.set_page_config(page_title="Mail Cleanup Bot", layout="centered")
st.title("📧 Mail Cleanup Bot", anchor=False)

# ---- Session State ----
if "running" not in st.session_state:
    st.session_state.running = False

with st.container(border=True):
    st.markdown(
    "<small><i>Note: This bot only works with company email address. For example: ram.christ&#64;trishakti.com.np</i></small>",
    unsafe_allow_html=True
)
    # ---- Inputs ----
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    subject = st.text_input("Subject to Delete")

    # ---- Dynamic Button Label ----
    button_label = "🚀 Start Clean Up"
    if st.session_state.running:
        button_label = "⏳ Please wait..."

    # ---- Button ----
    if st.button(button_label, disabled=st.session_state.running):

        if not username or not password or not subject:
            st.warning("All fields are required.")
            st.stop()

        st.session_state.running = True
        st.rerun()

# ---- Execution Block ----
if st.session_state.running:

    progress_text = st.empty()
    progress_bar = st.empty()

    try:
        cleaner = MailCleaner(username, password)

        progress_text.info("Connecting to mail server...", icon="ℹ️")
        cleaner.connect()

        progress_text.success("Bot connected to the email server.", icon="✅")
        sleep(1)
        progress_text.info("Searching emails with provided subject...", icon="🔎")
        email_ids = cleaner.get_matching_email_ids(subject)
        total = len(email_ids)

        if total == 0:
            progress_text.empty()
            st.warning("No emails found with given subject.", icon="⚠️")
            st.session_state.running = False
            sleep(2)
            st.rerun()
        progress_bar.progress(0)
        for current, total in cleaner.delete_emails_stream(email_ids):
            percent = int((current / total) * 100)

            progress_text.info(f"Deleted Emails {current}/{total}", icon="🚮")
            progress_bar.progress(percent)

        cleaner.close()

        st.success(f"✅ Cleanup completed. Total deleted emails: {total}")
        sleep(1)
        st.rerun()


    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        sleep(1)
        st.rerun()

    finally:
        st.session_state.running = False