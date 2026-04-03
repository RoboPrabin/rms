from utils.security import decrypt_data
import streamlit as st
import asyncio
import time
from datetime import datetime
from utils import helper, page_url
from service.otp_service import create_user_otp, verify_user_otp, get_otp_expiry
from assets.lottie_anim import show_otp_animation
class OTPPage:
    def __init__(self):
        st.set_page_config(page_title="OTP Verification", layout="centered", page_icon="🔑")
        helper.eliminate_top_margin("-4rem")

        if "username" not in st.session_state:
            st.error("Session invalid.")
            st.switch_page(page_url.login_url)
            st.stop()

    @st.fragment(run_every="1s")
    def render_otp_controls(self):
        """This section refreshes every second to update the timer"""
        expires_at = get_otp_expiry(st.session_state.username)
        
        if expires_at:
            # Calculate remaining time
            remaining = (expires_at - datetime.utcnow()).total_seconds()
            
            if remaining > 0:
                mins, secs = divmod(int(remaining), 60)
                st.write(f"OTP expires in: **{mins:02d}:{secs:02d}**")
                # Show a disabled button or just text while waiting
                st.button("Resend OTP", disabled=True)
            else:
                st.warning("Your OTP has expired. Please request a new one.")
                if st.button("Resend OTP"):
                    self.handle_resend()
                    st.rerun() # Refresh to start new timer
        else:
            # If no OTP exists for some reason
            if st.button("Send OTP", icon="📩"):
                self.handle_resend()
                st.rerun()

    def handle_resend(self):
        with st.spinner("Sending new OTP..."):
            try:
                asyncio.run(create_user_otp(
                    st.session_state.username,
                    st.session_state.email
                ))
                st.toast("New OTP sent!", icon="📩")
            except Exception as e:
                st.error(f"Failed to resend: {e}")

    def display(self):
        st.subheader("OTP Verification", anchor=False)
        # Wrap the email in backticks
        # st.info(f"Verify the code sent to {st.session_state.email}", icon="ℹ️")
        st.info(f"Verify the code sent to : `{st.session_state.email}`", icon="ℹ️")

        # The actual Input Form
        with st.form("otp_form"):
            show_otp_animation()
            otp = st.text_input("Enter 6-digit Code", max_chars=6, placeholder="000000").strip()
            submit = st.form_submit_button("Verify OTP", icon="🛡️")
            
            if submit:
                if verify_user_otp(st.session_state.username, otp):
                    st.success("OTP verified successfully!", icon="✅")
                    time.sleep(0.3)
                    if st.session_state.role == "USER":
                        st.switch_page(page_url.book_closure_url)
                    else:
                        st.switch_page(page_url.dashbord_url)
                else:
                    st.error("Invalid or Expired OTP")

        # The Timer and Resend Logic (Handles its own 1s refresh)
        self.render_otp_controls()

if __name__ == "__main__":
    page = OTPPage()
    page.display()