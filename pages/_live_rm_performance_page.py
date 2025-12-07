from streamlit_autorefresh import st_autorefresh
from datetime import datetime, time
from nepali_datetime import date as nepali_date
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from live_updater import live_rm_performance_calc
from pandas.io.formats.style import Styler

# ---------- Reusable helpers ----------

SUMMARY_COLS = [
    "Buy Amount", "Sell Amount", "Net Amount",
    "Ledger Balance", "Adjusted Balance", "Collateral"
]

def right_align_headers(styler: Styler) -> Styler:
    styler.set_table_styles(
        [
            {"selector": "th", "props": [("text-align", "right !important")]},
            {"selector": "thead th", "props": [("text-align", "right !important")]},
            {"selector": "thead tr th", "props": [("text-align", "right !important")]},
            {"selector": "th.col_heading", "props": [("text-align", "right !important")]},
            {"selector": "th.col_heading.level0", "props": [("text-align", "right !important")]},
        ],
        overwrite=True
    )
    return styler

def accounting_format(x):
    if pd.isna(x):
        return ""
    return f"({abs(x):,.2f})" if x < 0 else f"{x:,.2f}"

def highlight_negative(val):
    if pd.isna(val):
        return ""
    return "color: red;" if val < 0 else ""

def coerce_numeric_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=True)
                .replace("", "0")
                .astype(float)
            )
    return df

# ---------- App ----------

class Uarf:
    def __init__(self):
        st.set_page_config("Live RM Performance", page_icon="🟢", layout="wide")

        # Auth & UI
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()
        self.update_time = config.RM_REFRESH_TIME_IN_SECONDS

        # Create engine once
        self.engine = create_engine(helper.get_holding_engine())

       

    # @st.cache_data(ttl=config.RM_REFRESH_TIME_IN_SECONDS)
    def _load_order_book(_self) -> pd.DataFrame:
        # st.info("⬇️ Fetching order book. Please wait ...")
        if _self.role.upper() == "BRO":
            # df = pd.read_sql("SELECT * FROM order_book WHERE 'rmName' = %s", con=_self.engine, params=(_self.username,))
            df = pd.read_sql(
                """SELECT * FROM order_book WHERE "rmName" = %s""",
                con=_self.engine,
                params=(_self.username,)
            )
            print(df)

        else:
            df = pd.read_sql("SELECT * FROM order_book", con=_self.engine)
        df = helper.format_dataframe(df=df)
        if "Client Member Code" in df.columns:
            df = df.rename(columns={"Client Member Code": "Client Code"})
        df = coerce_numeric_columns(df, SUMMARY_COLS)
        return df

    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        col1, col2 = st.columns(2)
        with col1:
            filter_option = st.selectbox(
                "Filter by:",
                ["None", "Rm Name", "Client Code", "Client Name", "Branch"]
            )
        with col2:
            if filter_option == "Rm Name" and "Rm Name" in df.columns:
                rm_name = st.selectbox("Select Rm Name", [""] + sorted(df["Rm Name"].dropna().unique().tolist()))
                if rm_name:
                    df = df[df["Rm Name"] == rm_name]
            elif filter_option == "Client Code" and "Client Code" in df.columns:
                client_code = st.text_input("Enter Client Code")
                if client_code:
                    df = df[df["Client Code"].astype(str).str.contains(client_code, case=False, na=False)]
            elif filter_option == "Client Name" and "Client Name" in df.columns:
                client_name = st.text_input("Enter Client Name")
                if client_name:
                    df = df[df["Client Name"].astype(str).str.contains(client_name, case=False, na=False)]
            elif filter_option == "Branch" and "Branch" in df.columns:
                branch = st.selectbox("Select Branch", [""] + sorted(df["Branch"].dropna().unique().tolist()))
                if branch:
                    df = df[df["Branch"] == branch]
        return df

    def render_page(self):
        # Only run between 11:00 AM and 3:00 PM
        start_auto_refresh = True
        refresh_counter = 0
        if not (time(11, 0) <= datetime.now().time() <= time(15, 2)):
            st.warning(" Updates are paused. Data refresh is active only between 11:00 AM and 03:02 PM.", icon="📢")
            start_auto_refresh = False
            # return

        if start_auto_refresh:
             # Hide anchors
            st.markdown(
                "<style>h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {display: none !important;}</style>",
                unsafe_allow_html=True
            )

            # Custom header
            st.markdown(
                f"""
                <style>
                    .header-container {{
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                    }}
                    .glow-text {{
                        color: rgb(92, 228, 136);
                        animation: glowPulse 1.5s ease-in-out infinite;
                    }}
                    @keyframes glowPulse {{
                        0% {{ text-shadow: 0 0 5px rgba(92, 228, 136,0.4), 0 0 10px rgba(92, 228, 136,0.3); }}
                        50% {{ text-shadow: 0 0 12px rgba(92, 228, 136,0.7), 0 0 20px rgba(92, 228, 136,0.5); }}
                        100% {{ text-shadow: 0 0 5px rgba(92, 228, 136,0.4), 0 0 10px rgba(92, 228, 136,0.3); }}
                    }}
                </style>
                <div class="header-container">
                    <h1 style="margin:0; display:inline;">
                        <span class="glow-text">Live</span> RM Performance
                        <small style="font-style:italic; color:#888; margin-left:5px; font-size:0.4em; font-weight:normal;">
                            (updates every {self.update_time} seconds)
                        </small>
                    </h1>
                </div>
                """,
                unsafe_allow_html=True
            )
            # Auto-refresh every update_time seconds
            refresh_counter = st_autorefresh(
                interval=self.update_time * 1000,
                key="rm_refresh"
            )
        else:
            st.header("Order Book", anchor=False)

        df = self._load_order_book()
        df = self._apply_filters(df)

        # Summary table
        summary = df[SUMMARY_COLS].sum().to_frame(name="Total").T
        st.subheader("📊 Summary", anchor=False)
        styled_summary = (
            summary.style
                .format(accounting_format)
                .map(highlight_negative, subset=SUMMARY_COLS)
                .pipe(right_align_headers)
        )
        st.table(styled_summary)

        st.markdown("---")

        # Detailed table
        df = df.reset_index(drop=True)
        df.index = df.index + 1
        st.subheader("📚 Detailed RM Performance", anchor=False)
        st.badge(f"Total rows: {len(df)}", color="green")
        st.dataframe(
            df.style
            .format({col: accounting_format for col in SUMMARY_COLS if col in df.columns})
            .map(highlight_negative, subset=[c for c in SUMMARY_COLS if c in df.columns]),
            use_container_width=True
        )
        if refresh_counter > 0:
            # Toast after refresh
            time_now = datetime.now().strftime("%I:%M:%S %p")
            st.toast(f"Data just updated {time_now}", icon="🔔")
            helper.show_message("RM Performance data just got refreshed", color="yellow")


if __name__ == "__main__":
    Uarf().render_page()

















# from datetime import datetime, time
# from time import sleep
# from nepali_datetime import date as nepali_date
# from datetime import datetime
# import streamlit as st
# import pandas as pd
# from sqlalchemy import create_engine

# from utils import helper
# import streamlit_bridge.app_state as app_state
# import streamlit_bridge.navigation as navigation
# from config import config  # if needed elsewhere
# from live_updater import live_rm_performance_calc
# from pandas.io.formats.style import Styler



# # ---------- Reusable helpers ----------

# SUMMARY_COLS = [
#     "Buy Amount", "Sell Amount", "Net Amount",
#     "Ledger Balance", "Adjusted Balance", "Collateral"
# ]

# def right_align_headers(styler: Styler) -> Styler:
#     styler.set_table_styles(
#         [
#             {"selector": "th", "props": [("text-align", "right !important")]},
#             {"selector": "thead th", "props": [("text-align", "right !important")]},
#             {"selector": "thead tr th", "props": [("text-align", "right !important")]},
#             {"selector": "th.col_heading", "props": [("text-align", "right !important")]},
#             {"selector": "th.col_heading.level0", "props": [("text-align", "right !important")]},
#         ],
#         overwrite=True
#     )
#     return styler

# def accounting_format(x):
#     if pd.isna(x):
#         return ""
#     return f"({abs(x):,.2f})" if x < 0 else f"{x:,.2f}"

# def highlight_negative(val):
#     if pd.isna(val):
#         return ""
#     return "color: red;" if val < 0 else ""

# def coerce_numeric_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
#     for col in cols:
#         if col in df.columns:
#             df[col] = (
#                 df[col]
#                 .astype(str)
#                 .str.replace(",", "", regex=True)
#                 .replace("", "0")  # guard empty strings
#                 .astype(float)
#             )
#     return df

# # ---------- App ----------

# class Uarf:
#     def __init__(self):
#         st.set_page_config("Live RM Performance", page_icon="🟢", layout="wide")
        
#         # Auth & UI
#         app_state.restore_state_from_query_params()
#         app_state.sync_query_params_from_session()
#         app_state.check_authenticaiton_state()
#         self.username, self.role = app_state.get_current_user_info()
#         navigation.render_sidebar()

#         self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
#         self.today_np_date = nepali_date.today()

#         self.update_time = config.RM_REFRESH_TIME_IN_SECONDS


#         # Create engine once
#         self.engine = create_engine(helper.get_holding_engine())
#         st.markdown(
#             """
#             <style>
#                 h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
#                     display: none !important;
#                 }
#             </style>
#             """,
#             unsafe_allow_html=True
#         )

#         # st.header("🟢 Live RM Performance", anchor=False)
#         st.markdown(
#             f"""
#             <style>
#                 .header-container {{ 
#                     display:flex; 
#                     justify-content:space-between; 
#                     align-items:center; 
#                 }}

#                 .glow-text {{
#                     color: rgb(92, 228, 136);
#                     animation: glowPulse 1.5s ease-in-out infinite;
#                 }}

#                 @keyframes glowPulse {{
#                     0% {{ text-shadow: 0 0 5px rgba(92, 228, 136,0.4), 0 0 10px rgba(92, 228, 136,0.3); }}
#                     50% {{ text-shadow: 0 0 12px rgba(92, 228, 136,0.7), 0 0 20px rgba(92, 228, 136,0.5); }}
#                     100% {{ text-shadow: 0 0 5px rgba(92, 228, 136,0.4), 0 0 10px rgba(92, 228, 136,0.3); }}
#                 }}
#             </style>

#             <div class="header-container">
#                 <h1 style="margin:0; display:inline;">
#                     <span class="glow-text">Live</span> RM Performance
#                     <small style="font-style:italic; color:#888; margin-left:5px; font-size:0.4em; font-weight:normal;">
#                         (updates every {self.update_time} seconds)
#                     </small>
#                 </h1>
#             </div>
#             """,
#             unsafe_allow_html=True
#         )

#     @st.cache(ttl=config.RM_REFRESH_TIME_IN_SECONDS + 1)
#     def _load_order_book(_self) -> pd.DataFrame:
#         query = "SELECT * FROM order_book"
#         df = pd.read_sql(query, con=_self.engine)
#         df = helper.format_dataframe(df=df)
#         # Normalize naming for filters
#         if "Client Member Code" in df.columns:
#             df = df.rename(columns={"Client Member Code": "Client Code"})
#         # Ensure numeric columns are numeric for math/formatting
#         df = coerce_numeric_columns(df, SUMMARY_COLS)
#         return df

#     def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
#         col1, col2 = st.columns(2)
#         with col1:
#             filter_option = st.selectbox(
#                 "Filter by:",
#                 ["None", "Rm Name", "Client Code", "Client Name", "Branch"]
#             )

#         with col2:
#             if filter_option == "Rm Name" and "Rm Name" in df.columns:
#                 rm_name = st.selectbox("Select Rm Name", [""] + sorted(df["Rm Name"].dropna().unique().tolist()))
#                 if rm_name:
#                     df = df[df["Rm Name"] == rm_name]

#             elif filter_option == "Client Code" and "Client Code" in df.columns:
#                 client_code = st.text_input("Enter Client Code")
#                 if client_code:
#                     df = df[df["Client Code"].astype(str).str.contains(client_code, case=False, na=False)]

#             elif filter_option == "Client Name" and "Client Name" in df.columns:
#                 client_name = st.text_input("Enter Client Name")
#                 if client_name:
#                     df = df[df["Client Name"].astype(str).str.contains(client_name, case=False, na=False)]

#             elif filter_option == "Branch" and "Branch" in df.columns:
#                 branch = st.selectbox("Select Branch", [""] + sorted(df["Branch"].dropna().unique().tolist()))
#                 if branch:
#                     df = df[df["Branch"] == branch]

#         return df

#     def render_page(self):

#         while time(11, 0) <= datetime.now().time() <= time(15, 0):
#             df = self._load_order_book()
#             df = self._apply_filters(df)


#             # Summary table
#             summary = df[SUMMARY_COLS].sum().to_frame(name="Total").T
#             st.subheader("📊 Summary", anchor=False)

#             styled_summary = (
#                 summary.style
#                     .format(accounting_format)                              # format numbers with parentheses
#                     .map(highlight_negative, subset=SUMMARY_COLS)           # red for negatives
#                     .pipe(right_align_headers)                              # align headers right
#             )

#             st.table(styled_summary)

#             st.markdown("---")

#             # Detailed table
#             df = df.reset_index(drop=True)
#             df.index = df.index + 1

#             st.subheader("📚 Detailed RM Performance", anchor=False)
#             st.badge(f"Total rows: {len(df)}", color="green")
#             st.dataframe(
#                 df.style
#                 .format({col: accounting_format for col in SUMMARY_COLS if col in df.columns})
#                 .map(highlight_negative, subset=[c for c in SUMMARY_COLS if c in df.columns]),
#                 use_container_width=True
#             )

#             time_now = datetime.now().strftime("%I:%M:%S %p")
#             helper.show_message("RM Performance data just got refreshed", color="green")
#             helper.show_message(f"Waiting for {self.update_time + 1}", color="yellow")

#             sleep(self.update_time + 1)
#             st.toast(f"Data just updated {time_now}", icon="🔔")
#             sleep(2)
#             st.rerun()



# if __name__ == "__main__":
#     Uarf().render_page()