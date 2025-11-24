import streamlit as st
from navigation import render_sidebar
import app_state
from db import db



class Feedback:
    def __init__(self):
        st.set_page_config(page_title="Feedback", page_icon="💬", layout="centered")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()



        render_sidebar()

    def show_headings(self):
        # Clean, modern header
        st.markdown("""
           <style>
               div[data-testid="stVerticalBlock"]:not(section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]) {
                    margin-top: 0px !important;
                }
            </style>
            """, unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">We Value Your Feedback</h1>
                <p style="color: #666; font-size: 1.1rem;">Help us make the app better for you</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")

    def show_buttons(self):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.markdown("#### How was your experience?")
            rating = st.feedback("faces", key="rating")

            # Only show message + save when user clicks a face
            if rating is not None:
                bro_name = self.username or "Anonymous"

                if db.has_given_feedback(bro_name):
                    st.info("You've already shared your feedback. Thank you!")
                else:
                    bro = self.username or "guest"
                    db.save_feedback(bro=bro, star=rating + 1, remarks="")
                    stars_text = ["", "Terrible", "Poor", "Average", "Good", "Excellent"][rating + 1]
                    st.success(f"Thank you, **{bro}**! You rated: **{stars_text}** ({rating + 1} ⭐)")


        with col2:
            st.markdown("#### Have more to say?")
            st.info("💬 Click below to chat with us directly on WhatsApp")

            wa_url = "https://wa.me/9868212319?text=Hi!%20I'd%20like%20to%20share%20feedback%20about%20the%20Trishakti%20app%3A%0A%0A"

            st.markdown(
                f"""
                <div style="text-align: start; margin-top: 20px;">
                    <a href="{wa_url}" target="_blank">
                        <button style="
                            background: #0ab348ff; color: white; border: none; 
                            padding: 12px 28px; font-size: 18px; font-weight: 600;
                            border-radius: 12px; cursor: pointer;
                            box-shadow: 0 6px 20px rgba(37,211,102,0.3);
                            transition: all 0.2s;">
                            📱 Send on WhatsApp
                        </button>
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )



        st.markdown("#### Write Detailed Feedback")
        with st.expander("✍️ Share your thoughts (optional)", expanded=False):
            opinion = st.text_area(
                "", 
                placeholder="Suggestions, issues, or appreciation...",
                height=120,
                key="feedback_text"
            )
            st.markdown("""
                <style>
                    button[kind="primary"] {
                        background-color:  #076f81ff !important;
                        color: white !important;
                        border-radius: 12px !important;
                        padding: 12px 30px !important;
                        font-weight: bold !important;
                        border: none !important;
                    }
                </style>
                """, unsafe_allow_html=True)
            if st.button("Submit Feedback", type="primary"):
                if not opinion.strip():
                    st.warning("Please write something before submitting.")
                elif db.has_given_remarks(self.username):
                    st.info("You've already submitted written feedback. Thank you!")
                else:
                    user = self.username or "guest"
                    db.save_feedback(bro=user, star=0, remarks=opinion.strip())
                    # mark_remarks_given()
                    st.success("Thank you! Your detailed feedback has been saved.")
                    st.balloons()

    def render_page(self):
        self.show_headings()
        self.show_buttons()



if __name__ == "__main__":
    Feedback().render_page()