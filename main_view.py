import streamlit as st
import extra_streamlit_components as stx
import time
from pages.LoginPageT import LoginPage
from pages.Dashboard import Dashboard
from streamlit_js_eval import streamlit_js_eval

# Initialize Cookie Manager

def main():
    cookie_manager = stx.CookieManager(key="maint_cookie_manager")
    token = cookie_manager.get("jwt_token")
    if token or st.session_state.get("authenticated"):
        Dashboard().show()
    else:
        lp = LoginPage(cookie_manager=cookie_manager)
        lp.render_page()


if __name__ == "__main__":
    main()