from time import sleep
import streamlit as st
from service.mail_cleaner import MailCleaner
import io
import hashlib
import pandas as pd
from db import db
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.custom_hotkey import activate_client_code_hotkey

from pages.BasePage import BasePage


class MailCleanup(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin(margin_top="-4rem")
        st.session_state.active_menu = "kyc"
        st.set_page_config(page_title= "📧 Mail Cleanup", layout="centered")
        navigation.render_sidebar()
        st.title("📧 Mail Cleanup ", anchor=False)


    def render(self):
        if "running" not in st.session_state:
            st.session_state.running = False

        with st.container(border=True):
            st.markdown(
            "<small><i>Note: This bot only works with company email address. For example: ram.christ&#64;trishakti.com.np</i></small>",
            unsafe_allow_html=True
        )
            # ---- Inputs ----
            username = st.text_input("Email Address", placeholder="e.g. ram.christ&#64;trishakti.com.np")
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

if __name__ == "__main__":
    page = MailCleanup()
    page.render()