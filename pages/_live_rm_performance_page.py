from db import db
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
        
        

    def get_kyc_data(_self):
        rows = db.get_kyc()
        df = pd.DataFrame(rows, columns=['client_code', 'client_fullname', 'branch', 'boid'])
        return df

    # @st.cache_data(ttl=config.RM_REFRESH_TIME_IN_SECONDS-2)
    def _load_trade_book(_self) -> pd.DataFrame:
        # st.info("⬇️ Fetching order book. Please wait ...")
        if _self.role.upper() == "BRO":
            # df = pd.read_sql("SELECT * FROM order_book WHERE 'rmName' = %s", con=_self.engine, params=(_self.username,))
            df = pd.read_sql(
                """SELECT * FROM trade_book WHERE "rmName" = %s""",
                con=_self.engine,
                params=(_self.username,)
            )
        else:
            df = pd.read_sql("SELECT * FROM trade_book", con=_self.engine)

        df = helper.format_dataframe(df=df)
        if "Client Member Code" in df.columns:
            df = df.rename(columns={"Client Member Code": "Client Code", 'Rm Name':'Bro'})
        df = coerce_numeric_columns(df, SUMMARY_COLS)
        return df
    

    # @st.cache_data(ttl=config.RM_REFRESH_TIME_IN_SECONDS-2)
    def load_order_book_data(_self) -> pd.DataFrame:
        if _self.role.upper() == "BRO":
            df = pd.read_sql(
                """SELECT * FROM order_book WHERE bro = %s""",
                con=_self.engine,
                params=(_self.username,)
            )
        else:
            df = pd.read_sql("SELECT * FROM order_book", con=_self.engine)

        # df = helper.format_dataframe(df=df)
        
        if "Client Member Code" in df.columns:
            df = df.rename(columns={"Client Member Code": "Client Code"})
        df = coerce_numeric_columns(df, SUMMARY_COLS)
        return df
    


    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        col1, col2 = st.columns(2)
        with col1:
            filter_option = st.selectbox(
                "Filter by:",
                ["None", "Bro", "Client Code", "Client Name", "Branch"]
            )
        with col2:
            if filter_option == "Bro" and "Bro" in df.columns:
                rm_name = st.selectbox("Select Bro", [""] + sorted(df["Bro"].dropna().unique().tolist()))
                if rm_name:
                    df = df[df["Bro"] == rm_name]
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


    def show_trade_book(self):
        df = self._load_trade_book()
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
        df.sort_values(by="Buy Amount", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.index = df.index + 1
        st.subheader("📚 Detailed RM Performance", anchor=False)
        st.badge(f"Total rows: {len(df)}", color="green")
        st.dataframe(
            df.style
            .format({col: accounting_format for col in SUMMARY_COLS if col in df.columns})
            .map(highlight_negative, subset=[c for c in SUMMARY_COLS if c in df.columns]),
            width='stretch'
        )
        

    
    def show_order_book(self):
        st.set_page_config(layout='wide')
        df:pd.DataFrame = self.load_order_book_data()
        df_kyc = self.get_kyc_data()
        df = df.merge(
            df_kyc[["client_code", "client_fullname", "branch"]],
            how="left",
            left_on="clientCode",
            right_on="client_code"
        )

        df.drop(columns=["client_code"], inplace=True)
        df.rename(columns={"client_fullname":"clientName"}, inplace=True)
        df["branch"] = df["branch"].str.upper()
        # df.drop(columns=['Client_Code'], inplace=True)
        # statuses = ["All"] + df["activeStatus"].dropna().unique().tolist()
        # Get unique statuses except "COMPLETED"
        statuses = [s for s in df["activeStatus"].dropna().unique().tolist() if s != "COMPLETED"]
        # statuses = ["All"] + [s for s in df["activeStatus"].dropna().unique().tolist() if s != "COMPLETED"]
        selected_status = st.radio("Filter by Active Status:", options=statuses, horizontal=True)

        # Filter dataframe
        if selected_status == "All":
            filtered_df = df
        else:
            filtered_df = df[df["activeStatus"] == selected_status]

        # --- BUY and SELL totals ---
        buy_total = filtered_df.loc[filtered_df["buyOrSell"] == "BUY", "amount"].sum()
        sell_total = filtered_df.loc[filtered_df["buyOrSell"] == "SELL", "amount"].sum()

        net_total = buy_total + sell_total

       
        summary_df = pd.DataFrame([{
            "Buy Amount": buy_total,
            "Sell Amount": sell_total,
            "Net Amount": net_total
        }])

        summary_df.index = summary_df.index + 1

        numeric_cols = ["Buy Amount", "Sell Amount", "Net Amount"]
        summary_df = coerce_numeric_columns(summary_df, numeric_cols)
        
        summary_df['Buy Amount'] = summary_df["Buy Amount"] * -1
        summary_df['Net Amount'] = summary_df["Buy Amount"] + summary_df["Sell Amount"]
        # Apply formatting + right-align headers
        summary_df.index = ["Total"]
        styled_summary = (
            summary_df.style
                .format(accounting_format, subset=numeric_cols)
                .map(highlight_negative, subset=numeric_cols)
                .pipe(right_align_headers)
                .hide(axis="index")
        )
        st.table(styled_summary)
        # st.dataframe(styled_summary, hide_index=True)



        st.markdown("---")

        st.badge(f"Total Rows: {len(filtered_df)}", color="green" )

        
        # Correct column order
        column_order = ['bro', 'clientCode','clientName', 'branch' ,'symbol', 'buyOrSell', 'orderQuantity', 'orderPrice', 'amount']
        remaining_cols = [col for col in df.columns if col not in column_order]
        final_order = column_order + remaining_cols
        filtered_df = filtered_df[final_order]

        # Coerce numeric BEFORE formatting (use lowercase 'amount')

        # Apply BUY/SELL transformation safely on numeric
        filtered_df["amount"] = filtered_df.apply(
            lambda row: -abs(row["amount"]) if row["buyOrSell"] == "BUY" else abs(row["amount"]),
            axis=1
        )

        # Now uppercase columns
        filtered_df = helper.format_dataframe(filtered_df)

        filtered_df = coerce_numeric_columns(filtered_df, ["Amount"])
        # Reset index for display
        filtered_df.reset_index(drop=True, inplace=True)


        filtered_df.sort_values(by="Amount", inplace=True)
        filtered_df.reset_index(inplace=True, drop=True)
        filtered_df.index = filtered_df.index + 1
        # Apply accounting_format + highlight_negative
        styled_df = (
            filtered_df.style
                .format({"Amount": accounting_format})   # now safe, column is numeric
                .map(highlight_negative, subset=["Amount"])
        )

        # Show styled dataframe
        st.dataframe(styled_df, width='stretch')



        # st.dataframe(filtered_df, use_container_width=True)


    def show_live_performance_header(self):

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

    def render_page(self):
        has_time_up = False
        refresh_counter = 0
        if not (time(11, 0) <= datetime.now().time() <= time(15, 5)):
            st.warning(" Updates are paused. Data refresh is active only between 11:02 AM and 03:05 PM.", icon="📢")
            has_time_up = True

        if not has_time_up:
            refresh_counter = st_autorefresh(
                interval= self.update_time * 1000,
                key="rm_refresh"
            )
            
        if "last_refresh_counter" not in st.session_state:
            st.session_state.last_refresh_counter = refresh_counter
            # return

        st.markdown(
            "<style>h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {display: none !important;}</style>",
            unsafe_allow_html=True
        )
        if has_time_up:
            st.header("📜 BRO Performance", anchor=False)
        else:
            self.show_live_performance_header()

        view_option = st.radio(
            "Select View:",
            options=["Trade Book", "Order Book" ],
            index=0,   
            horizontal=True
        )

        st.markdown("---")
        if view_option == "Trade Book":
            self.show_trade_book()
        else:
            self.show_order_book()

        if refresh_counter > st.session_state.last_refresh_counter:
            time_now = datetime.now().strftime("%I:%M:%S %p")
            st.toast(f"Data just updated {time_now}", icon="🔔")

        # Update tracker
        st.session_state.last_refresh_counter = refresh_counter


if __name__ == "__main__":
    Uarf().render_page()