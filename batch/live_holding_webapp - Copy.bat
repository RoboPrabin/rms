@echo off
title Live Holdings App

REM Run the login page script with Streamlit
streamlit run "E:\Trishakti\Projects\track_stock_price\streamlit_login_page.py" --server.headless true --client.showSidebarNavigation=false --server.address=8501

pause
