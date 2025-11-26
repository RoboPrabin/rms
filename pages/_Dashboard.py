from config import config
from time import sleep
import streamlit as st
import pandas as pd
from sqlalchemy import text,create_engine
import io
from utils import page_url
from utils.helper import camel_to_title, format_with_comma, hide_components, get_holding_engine
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation


class Dashboard:
    def __init__(self):
        # st.set_page_config(page_title="Dashboard")
        st.set_page_config(page_title=f"Dashboard", page_icon="🏠",layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()

        print(self.username, self.role)

        self.refresh_sec = config.REFRESH_TIME_IN_SECONDS + 1  
        navigation.render_sidebar() 
        self.df: pd.DataFrame = None

    # ---------------------------------------------------------
    # LOAD DATA
    # ---------------------------------------------------------
    # @st.cache_data(ttl=helper.default_ttl())
    # def load_data(_self):
    #     engine = sqlalchemy.create_engine(get_holding_engine())
    #     df = pd.read_sql(f"SELECT * FROM holdings WHERE bro={_self.username}", engine)
    #     if len(df) >=1:
    #         # df = pd.read_sql("SELECT * FROM holdings", engine)
    #         df = None
    #         return df
    #     return df

    def load_data(_self):
        engine = create_engine(get_holding_engine())
        result = None
        with engine.connect() as conn:
            if _self.role.strip().upper() not in [r.upper() for r in helper.get_hero_role()]:
                print("Loading data for BRO:", _self.username)
                result = conn.execute(
                    text("SELECT * FROM holdings WHERE bro = :username"), 
                    {"username": _self.username.upper()}
                )
            else:
                result = conn.execute(text("SELECT * FROM holdings"))

            # result = conn.execute(text("SELECT * FROM holdings WHERE bro = :username"), {"username": _self.username})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            _self.df = df
        return df if not df.empty else None

    def show_header(_self):
        helper.adjust_ui()


        st.markdown(
            f"""
            <style>
                .header-container {{ 
                    display:flex; 
                    justify-content:space-between; 
                    align-items:center; 
                }}

                .glow-text {{
                    color: red;
                    animation: glowPulse 1.5s ease-in-out infinite;
                }}

                @keyframes glowPulse {{
                    0% {{ text-shadow: 0 0 5px rgba(255,0,0,0.4), 0 0 10px rgba(255,0,0,0.3); }}
                    50% {{ text-shadow: 0 0 12px rgba(255,0,0,0.7), 0 0 20px rgba(255,0,0,0.5); }}
                    100% {{ text-shadow: 0 0 5px rgba(255,0,0,0.4), 0 0 10px rgba(255,0,0,0.3); }}
                }}
            </style>

            <div class="header-container">
                <h1 style="margin:0; display:inline;">
                    <span class="glow-text">Live</span> Client Holdings
                    <small style="font-style:italic; color:#888; margin-left:5px; font-size:0.4em; font-weight:normal;">
                        (updates every {_self.refresh_sec} seconds)
                    </small>
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("""
        <style>
        button[aria-label="Download as CSV"], button[aria-label="Search"] {
            display:none !important;
        }
        </style>
        """, unsafe_allow_html=True)

    def show_holdings(_self):
        with st.spinner("Loading data. Please wait ..."):
            # sleep(5)
            df:pd.DataFrame = _self.load_data()
            df.rename(columns=lambda x: camel_to_title(x), inplace=True)

            columns_to_drop = [
                'Id', 'Username', 'Dp', 'Isin', 'REMARKS', 'SCRIPTDESC', 'Demat Pending',
                'Freeze Balance', 'Locking Balance', 'Remarks', 'Wacc Calculated Quantity',
                'Wacc Rate', 'Total Cost Of Capital', 'Pending Wacc Quantity',
                'Pending Wacc Rate', 'Pending Wacc', 'Pending Wacc Count',
                'Pending Wacc Valuation', 'Pending Wacc Total Quantity',
                'Pending Wacc Source', 'Script Desc', 'Average Broker Commission',
                'Sebon', 'Dp Fee', 'Capital Gain', 'Estimated Capital Gain Tax',
                'Ledger Fetched'
            ]

            df = df.drop(columns=columns_to_drop, errors="ignore")

            df = df.sort_values(by="Name").reset_index(drop=True)

            # column_order = [
            #     'Bro', 'Name', 'Boid', 'Client Code', 'Ledger Balance',
            #     'Script', 'Ltp', 'Market Value', 'Profit Loss', 'Profit Loss Percentage'
            # ]
            # df :pd.DataFrame= df[column_order + [c for c in df.columns if c not in column_order]]

            column_order = [
                'Bro', 'Name', 'Boid', 'Client Code', 'Ledger Balance',
                'Script', 'Ltp', 'Market Value', 'Profit Loss', 'Profit Loss Percentage'
            ]

            # Keep only existing columns
            existing_columns = [c for c in column_order if c in df.columns]
            df = df[existing_columns + [c for c in df.columns if c not in existing_columns]]



            df = df.round(2)
            df = helper.format_negative_numbers(df)
            df.rename(columns={"Profit Loss": "Profit (Loss)", "Profit Loss Percentage": "Profit (Loss) Percentage"}, inplace=True)
            df = helper.format_dataframe(df)
            df.index = df.index + 1
            # df = _self.add_total_row_to_top(df) 
            _self.df = df
            # sleep(1.3)


    def show_download_button(_self):
        # ---------------------------------------------------------
        # DOWNLOAD BUTTON + NAV BUTTONS
        # ---------------------------------------------------------
        output = io.BytesIO()
        _self.df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)

        role = _self.role
        if role in helper.get_hero_role():
            st.download_button("📥 Download XLSX", data=output, file_name="client_holdings_TSL.xlsx", width='content')

    def show_search_box(_self):
        # ---------------------------------------------------------
        # SEARCH
        # ---------------------------------------------------------
        search = st.text_input("Search in table", "").strip()

        if search:
            mask = _self.df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
            df_filtered = _self.df[mask]
            df_filtered.index = df_filtered.index + 1
        else:
            df_filtered = _self.df

        # def highlight_rows(row):
        #     if "(" in str(row.get("Profit Loss", "")):
        #         return ["background-color: #ffcccc; color: black"] * len(row)  # light red
        #     else:
        #         return [""] * len(row)

        # styled_df = _self.df.style.apply(highlight_rows, axis=1)

        # st.dataframe(styled_df, width="content")
        # st.table(_self.df.style.apply(highlight_rows, axis=1))

        st.dataframe(df_filtered, width='stretch')

    def hide_download_csv_button():
        # ---------------------------------------------------------
        # CSS cleanup
        # ---------------------------------------------------------
        st.markdown("""
        <style>
        button[aria-label="Download as CSV"], button[aria-label="Search"] {
            display:none !important;
        }
        </style>
        """, unsafe_allow_html=True)

        
        # _self.hide_download_csv_button()
    
    def render_dashboard(_self):
        # Check access
        # print(len(_self.role))
        _self.load_data()

        if  _self.df.empty and _self.role.strip() == "BRO":
            st.warning("No holdings data found for your BRO ID.", icon="⚠️")
            st.warning("Please add client's Meroshare account to know current holdings.", icon="⚠️")
            if st.button("➕ Add Meroshare Account"):
                st.switch_page(page_url.meroshare_url)
            st.stop()

        # Show header once
        _self.show_header()

        # Auto-refresh loop
        while True:
            helper.show_message("Data just got refreshed ...", "yellow")
            _self.show_holdings()
            _self.show_download_button()
            _self.show_search_box()
            _self.show_totals(_self.df)
            sleep(_self.refresh_sec)
            st.rerun()
            



    def show_totals(_self, df: pd.DataFrame):
        # Columns you want to summarize
        target_cols = [
            "Market Value",
            "Profit (Loss)",
            "Profit (Loss) Percentage",
            "Current Balance",
            "Ledger Balance",      # Your "Current Balance"
            "Free Balance",
            "Pledge Balance",
            "Total Purchase Cost",
            "Calculated Wacc"
        ]

        # Some may not exist depending on df → filter safe
        target_cols = [c for c in target_cols if c in df.columns]

        if not target_cols:
            return

        # Convert all numbers to float safely
        def to_float(x):
            if pd.isna(x):
                return 0.0

            x = str(x).replace(",", "").strip()

            # Convert (1,233.22) -> -1233.22
            if x.startswith("(") and x.endswith(")"):
                x = "-" + x[1:-1]

            try:
                return float(x)
            except:
                return 0.0

        clean_df = df[target_cols].map(to_float)

        # Summation
        totals = clean_df.sum()

        # Build output row
        total_df = pd.DataFrame([totals])
        total_df.insert(0, "Summary", ["TOTAL"])

        # Format beautification
        def fmt(v):
            if isinstance(v, float):
                if v < 0:
                    return f"({abs(v):,.2f})"
                else:
                    return f"{v:,.2f}"

            return v


        total_df = total_df.map(fmt)
        st.markdown("### 📌 Summary Totals", unsafe_allow_html=True)
        st.dataframe(total_df, width='stretch', hide_index=True)


   
    
    

if __name__ == "__main__":
    dashboad = Dashboard()
    dashboad.render_dashboard()
    


    