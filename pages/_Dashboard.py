from time import sleep
import streamlit as st
import pandas as pd
import sqlalchemy
import io
from utils import page_url
from utils.helper import camel_to_title, format_with_comma, hide_components, get_holding_engine
from utils import helper
import app_state
import navigation


class Dashboard:
    def __init__(self):
        # st.set_page_config(page_title="Dashboard")
        st.set_page_config(page_title=f"Dashboard |",page_icon="🏠",layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()

        
        navigation.render_sidebar() 
        self.df: pd.DataFrame = None

    # ---------------------------------------------------------
    # LOAD DATA
    # ---------------------------------------------------------
    @st.cache_data(ttl=helper.default_ttl())
    def load_data(_self):
        engine = sqlalchemy.create_engine(get_holding_engine())
        df = pd.read_sql("SELECT * FROM holdings", engine)
        return df

    def show_header(_self):
        helper.adjust_ui()


        st.markdown("""
            <style>
                .header-container { 
                    display:flex; 
                    justify-content:space-between; 
                    align-items:center; 
                }

                /* Pulsing Glow */
                .glow-text {
                    color: red;
                    animation: glowPulse 1.5s ease-in-out infinite;
                }

                @keyframes glowPulse {
                    0% { text-shadow: 0 0 5px rgba(255,0,0,0.4), 0 0 10px rgba(255,0,0,0.3); }
                    50% { text-shadow: 0 0 12px rgba(255,0,0,0.7), 0 0 20px rgba(255,0,0,0.5); }
                    100% { text-shadow: 0 0 5px rgba(255,0,0,0.4), 0 0 10px rgba(255,0,0,0.3); }
                }
            </style>

            <div class="header-container">
                <h1><span class="glow-text">Live</span> Client Holdings</h1>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <style>
        button[aria-label="Download as CSV"], button[aria-label="Search"] {
            display:none !important;
        }
        </style>
        """, unsafe_allow_html=True)

    def show_holdings(_self):
        with st.spinner("Loading holdings data..."):
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

            column_order = [
                'Bro', 'Name', 'Boid', 'Client Code', 'Ledger Balance',
                'Script', 'Ltp', 'Market Value', 'Profit Loss', 'Profit Loss Percentage'
            ]
            df = helper.format_negative_numbers(df)
            df :pd.DataFrame= df[column_order + [c for c in df.columns if c not in column_order]]
            df.rename(columns={"Profit Loss": "Profit (Loss)", "Profit Loss Percentage": "Profit (Loss) Percentage"}, inplace=True)
            df = helper.format_dataframe(df)
            df.index = df.index + 1
            _self.df = df
            sleep(1.3)


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

        st.dataframe(df_filtered, width='content')

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

    def render_dashboard(_self):
        _self.show_header()
        _self.show_holdings()
        _self.show_download_button()
        _self.show_search_box()
        # _self.hide_download_csv_button()



if __name__ == "__main__":
    dashboad = Dashboard()
    dashboad.render_dashboard()
    


    