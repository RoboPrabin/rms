@echo off
title Live Holdings App

REM Run the login page script with Streamlit
streamlit run "D:\Trishakti\Projects\RPA\track_stock_price\streamlit_login_page.py" --client.showSidebarNavigation=false --server.address 0.0.0.0 --server.port 8501
pause
