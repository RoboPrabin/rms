import streamlit as st
from streamlit_lottie import st_lottie
import json
from config import config
# Cache the loader for performance
@st.cache_data
def load_lottie_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# Path to your animation
anim_path_login = config.login_animation_path
anim_path_otp = config.otp_animation_path

lottie_animation_login = load_lottie_file(anim_path_login)
lottie_animation_otp = load_lottie_file(anim_path_otp)


def show_login_animation():
    # Show the animation
    st_lottie(
        lottie_animation_login,
        speed=1,          # Normal speed
        loop=True,        # Infinite loop
        quality="high",   # High-quality rendering
        height=420        # Adjust height as needed
    )


def show_otp_animation():
    # Show the animation
    st_lottie(
        lottie_animation_otp,
        speed=1,          # Normal speed
        loop=True,        # Infinite loop
        quality="high",   # High-quality rendering
        height=200        # Adjust height as needed
    )
