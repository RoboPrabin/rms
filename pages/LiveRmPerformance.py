from db import db
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, time
from nepali_datetime import date as nepali_date
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

from utils import auth_utils, helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from pandas.io.formats.style import Styler
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage


# ---------- Reusable helpers ----------

SUMMARY_COLS = [
    "Buy Amount", "Sell Amount", "Net Amount"
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

# def highlight_negative(val):
#     val = float(str(val).replace(",", ''))
#     if pd.isna(val):
#         return ""
#     return "color: red;" if val < 0 else ""


def highlight_negative(val):
    if pd.isna(val):
        return ""
    try:
        # Convert accounting-style strings to float
        val_str = str(val).replace(",", "").strip()
        if val_str.startswith("(") and val_str.endswith(")"):
            val_float = -float(val_str[1:-1])
        else:
            val_float = float(val_str)
        return "color: red;" if val_float < 0 else ""
    except Exception:
        return ""


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



def get_city_code(full_name: str) -> str:
    """Return the code for a given full city name."""
    city_map = {
        "MAHENDRANAGAR": "MHN",
        "KATHMANDU": "KTM",
        "LALITPUR": "LTP",
        "POKHARA": "PKR",
        "HETAUDA": "HTD",
        "BUTWAL": "BTL",
        "BANEPA": "BNP"
    }
    
    # Convert input to uppercase to make it case-insensitive
    return city_map.get(full_name.upper(), "Unknown")

@st.fragment(run_every="1s")
def live_clock():
    now = datetime.now()
    formatted_time = now.strftime("%I:%M:%S %p")  # 12-hour with seconds
    st.badge(formatted_time, color="green", icon="⌚")
    # st.markdown(
        # f"<h1 style='text-align: center;'>{formatted_time}</h1>",
        # unsafe_allow_html=True
    # )

# ---------- App ----------
class Uarf(BasePage):
    def __init__(self):
        super().__init__()
        # helper.eliminate_top_padding(padding_top="-90rem")
        helper.eliminate_top_margin("-10rem")
        st.session_state.active_menu = "rm"
        st.set_page_config("Live RM Performance", page_icon="🟢", layout="wide")
        navigation.render_sidebar()

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()
        self.update_time = config.RM_REFRESH_TIME_IN_SECONDS

        # Create engine once
        self.engine = create_engine(helper.get_holding_engine())
        
        activate_client_code_hotkey()
        self.bro_due = 0
        self.has_bro_filter = False
        self.has_branch_filter = False
        self.branch_due = 0

    def get_kyc_data(_self):
        rows = db.get_kyc()
        df = pd.DataFrame(rows, columns=['client_code', 'client_fullname', 'branch', 'boid'])
        return df

    # @st.cache_data(ttl=config.RM_REFRESH_TIME_IN_SECONDS-2)
    def _load_trade_book(_self) -> pd.DataFrame:
        # st.info("⬇️ Fetching order book. Please wait ...")
        if _self.role.upper() == "BRO":
            alias = helper.get_alias_name(_self.username)
            # df = pd.read_sql("SELECT * FROM order_book WHERE 'rmName' = %s", con=_self.engine, params=(_self.username,))
            df = pd.read_sql(
                """SELECT * FROM trade_book WHERE "rmName" = %s""",
                con=_self.engine,
                params=(alias,)
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
            alias = helper.get_alias_name(_self.username)

            df = pd.read_sql(
                """SELECT * FROM order_book WHERE bro = %s""",
                con=_self.engine,
                params=(alias,)
            )
        else:
            df = pd.read_sql("SELECT * FROM order_book", con=_self.engine)

        # df = helper.format_dataframe(df=df)
        
        if "Client Member Code" in df.columns:
            df = df.rename(columns={"Client Member Code": "Client Code"})
        df = coerce_numeric_columns(df, SUMMARY_COLS)
        return df
    
    def load_due_list_data_bro(_self, bro_name):
        query = """
        SELECT d.*,
                COALESCE(m."rmName", 'N/A') AS "rmName"
        FROM due_list d
        LEFT JOIN client_rm_map m 
                ON d."clientCode" = m."clientCode"
        WHERE COALESCE(m."rmName", 'N/A') = %s
            AND d.uploaded_at LIKE %s
            AND d.uploaded_at LIKE %s;
        """
        today_like = pd.Timestamp("today").strftime("%Y-%m-%d") + "%"
        am_like = "% AM"
        params = (bro_name, today_like, am_like)
        df = pd.read_sql(query, _self.engine, params=params)
        return df


    def load_due_list_data_according_to_branch(self, branch_name):
        query = """
        SELECT * FROM due_list 
        WHERE branch = %s 
        AND uploaded_at LIKE %s;
        """
        
        # Example: '2026-01-05% AM'
        today_am_like = pd.Timestamp("today").strftime("%Y-%m-%d") + "% AM"
        
        params = (branch_name, today_am_like)
        
        df = pd.read_sql(query, self.engine, params=params)
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
                    due_list = self.load_due_list_data_bro(bro_name=rm_name)
                    bro_due_sum = due_list['adjustedBalance'].sum()
                    self.bro_due = bro_due_sum
                    self.has_bro_filter = True
                    
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
                    df_due_list = self.load_due_list_data_according_to_branch(branch_name=get_city_code(full_name=branch))
                    total_due_branch = df_due_list['adjustedBalance'].sum()
                    self.has_branch_filter = True
                    self.branch_due = total_due_branch
        return df

    def _clean_numeric_columns(self, df, cols):
        for col in cols:
            if col in df.columns:
                # Remove commas and convert to float
                df[col] = (
                    df[col]
                    .astype(str)                # ensure string for replace
                    .str.replace(",", "", regex=False)
                    .replace("", "0")           # handle empty strings
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    
    def show_trade_book(self):
        df = self._load_trade_book()
        df = self._apply_filters(df)
        target_cols = SUMMARY_COLS + ["Ledger Balance", "Adjusted Balance"]
        df = self._clean_numeric_columns(df, target_cols)
       



        total_turnover = (df['Buy Amount'].sum() * -1) + df['Sell Amount'].sum()
        # Summary table
        summary = df[SUMMARY_COLS].sum().to_frame(name="Total").T
        summary.insert(3, "Total Turnover", total_turnover)
        if self.role == 'BRO':
            due_list = self.load_due_list_data_bro(bro_name=self.username)
            bro_due_sum = due_list['adjustedBalance'].sum()
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center;margin-bottom: 1rem;margin-top: 1.6rem;">
                    <h3 style="margin-bottom: -18px;">📊 Summary</h4>
                    <span style="
                        background-color: rgba(255, 108, 108, 0.2); 
                        color: rgb(255, 108, 108); 
                        font-size: 0.9rem; 
                        padding: 3px 8px; 
                        border-radius: 6px;
                        margin-top:1.6rem;
                    ">
                        Total Adjusted Due Balance: {bro_due_sum:,.2f}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            if self.has_bro_filter:
                due_amount = self.bro_due
                label = "Total Adjusted Due Balance"
            elif self.has_branch_filter:
                due_amount = self.branch_due
                label = "Total Adjusted Due Balance"
            else:
                due_amount = None

            if due_amount is not None:
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; margin-top: 1.6rem;">
                        <h3 style="margin-bottom: -18px;">📊 Summary</h3>
                        <span style="
                            background-color: rgba(255, 108, 108, 0.2); 
                            color: rgb(255, 108, 108); 
                            font-size: 0.9rem; 
                            padding: 3px 8px; 
                            border-radius: 6px;
                            margin-top:1.6rem;
                        ">
                            {label}: {due_amount:,.2f}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("📊 Summary")

            


        summary.rename(columns={"Net Amount": "Net Settlement Amount"}, inplace=True)
        styled_summary = (
            summary.style
                .format(accounting_format)
                .map(highlight_negative, subset=['Buy Amount', 'Net Settlement Amount'])
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
        target_cols = SUMMARY_COLS + ["Ledger Balance", "Adjusted Balance"]
        valid_cols = [c for c in target_cols if c in df.columns]

        selected_row = st.dataframe(
            df.style
            .format({col: accounting_format for col in valid_cols})
            .map(highlight_negative, subset=valid_cols),
            width="stretch",
            selection_mode='single-row', 
            key='detailed_rm_performance',
            on_select='rerun'
        )

        if selected_row:
            selected_indices = selected_row.selection.rows
            if selected_indices:
                # Get the first selected index (since it's single-row mode)
                idx = selected_indices[0]
                row_data = df.iloc[idx]
                client_code = row_data["Client Code"]
                client_name = row_data["Client Name"]
                client_branch = row_data["Branch"]
                df_order_book: pd.DataFrame = self.load_order_book_data()
                df_completed_order = df_order_book[
                    (df_order_book["activeStatus"] == "COMPLETED") &
                    (df_order_book["clientCode"] == client_code)
                ]
                try:
                    self.show_stocks_of_selected_client(df_completed_order, client_name, client_code, client_branch)
                except Exception as e:
                    pass


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
        # statuses = [s for s in df["activeStatus"].dropna().unique().tolist() if s != "COMPLETED"]
        statuses =  [s for s in df["activeStatus"].dropna().unique().tolist()]
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
                .map(highlight_negative, subset=["Amount",])
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

        live_clock()
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

    # @st.dialog(title="Trade Completed", width='large')
    # def show_stocks_of_selected_client(self, df:pd.DataFrame, client_name, client_code, client_branch):
    #     st.caption(f"{client_name} | {client_code} | {client_branch}")
    #     unique_symbols = df["symbol"].unique()
    #     # print(len(unique_symbols))
    #     df = df.copy()
    #     df.sort_values(by="amount", inplace=True, ascending=False)
    #     df.reset_index(drop=True, inplace=True)
    #     # Multiply Amount by -1 only when buyOrSell == "BUY"
    #     df.loc[df["buyOrSell"] == "BUY", "amount"] = df.loc[df["buyOrSell"] == "BUY", "amount"] * -1
    #     df.index = df.index + 1
    #     selected_cols = [
    #     "symbol",
    #     "buyOrSell",
    #     "orderQuantity",
    #     "orderPrice",
    #     "amount",
    #     "orderTime",
    #     "activeStatus",          
    #     ]
    #     df = df[selected_cols]
    #     df = df.rename(columns=helper.camel_to_title)
       
    #     styler = (
    #     df.style
    #         .format({
    #             "Order Quantity": "{:,.0f}",   # integers with commas
    #             "Order Price": accounting_format,
    #             "Amount": accounting_format
    #         })
    #         .map(highlight_negative, subset=["Order Quantity", "Order Price", "Amount"])
    #     )
    #     st.badge(f"Total Trade: {len(unique_symbols)}", color='green')
    #     st.dataframe(styler)


    @st.dialog(title="Trade Completed", width='large')
    def show_stocks_of_selected_client(self, df: pd.DataFrame, client_name, client_code, client_branch):
        st.caption(f"{client_name} | {client_code} | {client_branch}")
        
        df = df.copy()
        df.sort_values(by="amount", inplace=True, ascending=False)
        df.reset_index(drop=True, inplace=True)
        df.loc[df["buyOrSell"] == "BUY", "amount"] = df.loc[df["buyOrSell"] == "BUY", "amount"] * -1
        df.index = df.index + 1

        selected_cols = [
            "symbol",
            "buyOrSell",
            "orderQuantity",
            "orderPrice",
            "amount",
            "orderTime",
            "activeStatus",          
        ]
        df = df[selected_cols]
        df = df.rename(columns=helper.camel_to_title)

        # # --- Trade Summary ---
        # # Group by symbol and buy/sell, sum order quantity and amount
        # trade_summary = df.groupby(["Symbol", "Buy Or Sell"], as_index=False).agg({
        #     "Order Quantity": "sum",
        #     "Amount": "sum"
        # })

        # # Optional: formatting numbers nicely
        # trade_summary["Order Quantity"] = trade_summary["Order Quantity"].map("{:,.0f}".format)
        # trade_summary["Amount"] = trade_summary["Amount"].map(accounting_format)
        # trade_summary.index = trade_summary.index + 1

        #  # --- Style negative Amounts ---
        # styler_summary = trade_summary.style.map(
        #     highlight_negative, subset=["Amount"]
        # )



        # st.subheader("📊 Trade Summary")
        # unique_symbols = df["Symbol"].nunique()
        # st.badge(f"Total Trade: {unique_symbols}", color='green')
        # st.dataframe(styler_summary, use_container_width=True)



        # --- Trade Summary ---
        trade_summary = df.groupby(["Symbol", "Buy Or Sell"], as_index=False).agg(
            Order_Quantity=("Order Quantity", "sum"),
            Amount=("Amount", "sum"),
            Transaction_Count=("Symbol", "count")  # count of rows per Symbol x Buy Or Sell
        )

        # Reorder columns exactly as requested
        trade_summary = trade_summary[["Symbol", "Buy Or Sell", "Order_Quantity", "Amount", "Transaction_Count"]]

        # Format numbers
        trade_summary["Order_Quantity"] = trade_summary["Order_Quantity"].map("{:,.0f}".format)
        trade_summary["Amount"] = trade_summary["Amount"].map(accounting_format)
        trade_summary["Transaction_Count"] = trade_summary["Transaction_Count"].map("{:,.0f}".format)
        trade_summary.columns = [col.replace("_", " ") for col in trade_summary.columns]

        # Reset index
        trade_summary.index = trade_summary.index + 1

        # --- Style negative Amounts ---
        styler_summary = trade_summary.style.map(
            highlight_negative, subset=["Amount"]
        )

        # Display
        st.subheader("📊 Trade Summary")
        st.dataframe(styler_summary, use_container_width=True)



        st.divider()
        st.subheader("📃 Trade Details")
        search_query = st.text_input("Search by Symbol")
        df_filtered = df.copy()
        if search_query:
            df_filtered = df_filtered[df_filtered["Symbol"].str.contains(search_query, case=False, na=False)]
        df_filtered = df_filtered.reset_index(drop=True)
        df_filtered.index = df_filtered.index + 1
        st.badge(f"Total Transactions: {len(df_filtered)}", color='green')
        styler = (
            df_filtered.style
                .format({
                    "Order Quantity": "{:,.0f}",
                    "Order Price": accounting_format,
                    "Amount": accounting_format
                })
                .map(highlight_negative, subset=["Amount"]))
        st.dataframe(styler, width='stretch')








if __name__ == "__main__":
    Uarf().render_page()