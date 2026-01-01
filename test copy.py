from db import db
import streamlit_hotkeys as hotkeys
import plotly.express as px
from datetime import datetime, timedelta
from nepali_datetime import date as nepali_date
from datetime import datetime
import streamlit as st
import pandas as pd
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey

class PayableAndReceivable:
    def __init__(self):
        # helper.eliminate_top_padding()
        st.set_page_config("Payable & Receivable", page_icon="💸", layout='wide')

        # # Dates
        # self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        # self.today_date = datetime.now().strftime("%Y-%m-%d")
        # self.today_np_date = nepali_date.today()

        # # Authentication
        # # app_state.restore_state_from_query_params()
        # # app_state.sync_query_params_from_session()
        # # app_state.check_authenticaiton_state()


        # # self.username, self.role = app_state.get_current_user_info()
        # activate_client_code_hotkey()

        # # Sidebar
        # navigation.render_sidebar()
        st.header("💸 Payables & Receivables", anchor=False)
        self.selected_date = st.date_input("Select Date")
        self.bc_data = None
                

    def get_floorsheet_by_script_and_date_range(self,script, start_date, end_date):
        query = """
            SELECT *
            FROM floorsheet
            WHERE symbol = %s
            AND uploaded_at::date BETWEEN %s AND %s
        """
        conn = db.get_connection()

        with conn.cursor() as cur:
            cur.execute(query, (script, start_date, end_date))
            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description]
            return pd.DataFrame(rows, columns=columns)


    def calculate_today_book_closure_buy_sell(self):
        """
        Calculate total BUY and SELL amounts from today's floorsheet
        for scripts present in today's book closure data.

        Returns:
            dict: {
                'scripts': list[str],
                'total_buy': float,
                'total_sell': float,
                'filtered_df': pd.DataFrame
            }
        """

        # 1. Get today's book-closure data
        book_closure_df = db.get_today_book_closure_range(selected_date=self.selected_date)
        self.bc_data = book_closure_df

        if book_closure_df.empty:
            return {
                "scripts": [],
                "total_buy": 0.0,
                "total_sell": 0.0,
                "filtered_df": book_closure_df
            }

        # 2. Extract unique scripts
        scripts = (
            book_closure_df["script"]
            .dropna()
            .unique()
            .tolist()
        )

        # 3. Get today's floorsheet
        floorsheet_df = db.get_today_floorsheet(selected_date=self.selected_date)

        if floorsheet_df.empty:
            return {
                "scripts": scripts,
                "total_buy": 0.0,
                "total_sell": 0.0,
                "filtered_df": floorsheet_df
            }

        # 4. Filter floorsheet for book-closure scripts
        filtered_df = floorsheet_df[
            floorsheet_df["symbol"].isin(scripts)
        ]

        # 5. Calculate BUY and SELL totals (amount-based)
        total_buy = (
            filtered_df.loc[
                filtered_df["transaction_type"].str.upper() == "BUY",
                "amount"
            ].sum()
        )

        total_sell = (
            filtered_df.loc[
                filtered_df["transaction_type"].str.upper() == "SELL",
                "amount"
            ].sum()
        )

        return {
            "scripts": scripts,
            "total_buy": float(total_buy),
            "total_sell": float(total_sell),
            "filtered_df": filtered_df
        }


    def calculate_today_floorsheet_buy_sell(self):
        """
        Calculate total BUY and SELL amounts from today's floorsheet.

        Returns:
            dict: {
                'total_buy': float,
                'total_sell': float,
                'floorsheet_df': pd.DataFrame
            }
        """

        floorsheet_df = db.get_today_floorsheet(selected_date=self.selected_date)
        
        if floorsheet_df.empty:
            st.info(f"Floorsheet not found as of date {self.selected_date}")
            st.stop()
            return {
                "total_buy": 0.0,
                "total_sell": 0.0,
                "floorsheet_df": floorsheet_df
            }

        total_buy = (
            floorsheet_df.loc[
                floorsheet_df["transaction_type"].str.upper() == "BUY",
                "amount"
            ].sum()
        )

        total_sell = (
            floorsheet_df.loc[
                floorsheet_df["transaction_type"].str.upper() == "SELL",
                "amount"
            ].sum()
        )

        return {
            "total_buy": float(total_buy),
            "total_sell": float(total_sell),
            "floorsheet_df": floorsheet_df
        }


    def calculate_book_closure_range_buy_sell(self):
        """
        For each script in today's book closure:
        - Fetch floorsheet data between start_date and end_date
        - Calculate total BUY and SELL amounts

        Returns:
            pd.DataFrame with:
            ['script', 'start_date', 'end_date', 'total_buy', 'total_sell', 'net_amount']
        """

        df_bc = db.get_today_book_closure_only(selected_date=self.selected_date)
        st.header(f"T0 data from {self.selected_date} floorsheet")
        st.dataframe(df_bc)
        if df_bc.empty:
            return df_bc

        results = []

        for _, row in df_bc.iterrows():
            script = row["script"]
            start_date = row["start_date"]
            end_date = row["end_date"]

            # Fetch floorsheet for script + date range
            fs_df = self.get_floorsheet_by_script_and_date_range(
                script=script,
                start_date=start_date,
                end_date=end_date
            )

            if fs_df.empty:
                total_buy = 0.0
                total_sell = 0.0
            else:
                total_buy = (
                    fs_df.loc[
                        fs_df["transaction_type"].str.upper() == "BUY",
                        "amount"
                    ].sum()
                )

                total_sell = (
                    fs_df.loc[
                        fs_df["transaction_type"].str.upper() == "SELL",
                        "amount"
                    ].sum()
                )

            results.append({
                "script": script,
                "start_date": start_date,
                "end_date": end_date,
                "total_buy": float(total_buy),
                "total_sell": float(total_sell),
                "net_amount": float(total_buy - total_sell)
            })

        return pd.DataFrame(results)


    def render_page(self):

    

        today_book_closure_result = self.calculate_today_book_closure_buy_sell()
        summary_df = pd.DataFrame([{
            "scripts": ", ".join(today_book_closure_result["scripts"]) if isinstance(today_book_closure_result["scripts"], list) else today_book_closure_result["scripts"],
            "total_buy": today_book_closure_result["total_buy"],
            "total_sell": today_book_closure_result["total_sell"]
        }])
        st.dataframe(summary_df)



        business_summary = self.calculate_today_floorsheet_buy_sell()
        st.header(f"Today's Floorsheet BUY: {business_summary['total_buy']:,.2f}")
        st.header(f"Today's Floorsheet SELL: {business_summary['total_sell']:,.2f}")





        st.markdown("---")
        st.subheader("📊 Book Closure – Buy/Sell Summary (Date Range Wise)")

        summary_df = self.calculate_book_closure_range_buy_sell()
        st.header(f"BC to be minus")
        st.dataframe(summary_df)
        col1, col2, col3 = st.columns(3)

        today_buy_after_book_close = (business_summary['total_buy'] - today_book_closure_result['total_buy']) - summary_df['total_buy'].sum()
        today_sell_after_book_close = (business_summary['total_sell'] - today_book_closure_result['total_sell']) - summary_df['total_sell'].sum()
        st.markdown("---")
        st.header(f"Buy Amount after Book Closure: {today_buy_after_book_close:,.2f}")
        st.header(f"Sell Amount after Book Closure: {today_sell_after_book_close:,.2f}")


        rec_or_pay = today_buy_after_book_close - today_sell_after_book_close
        st.header(f"Total Payables/Receivables is : {rec_or_pay:,.2f}")
        st.markdown("---")
        st.subheader(f"Book closure as of {self.selected_date}")
        st.badge(f"Total: {len(self.bc_data)}")
        st.dataframe(self.bc_data)


    def uat_page(self):
        floorsheet_df = db.get_today_floorsheet(selected_date=self.selected_date)
        st.dataframe(floorsheet_df)
        if floorsheet_df.empty:
            st.info(f"Floorsheet not found as of date {self.selected_date}")
            st.stop()
            return {
                "total_buy": 0.0,
                "total_sell": 0.0,
                "floorsheet_df": floorsheet_df
            }

        total_buy_florsheet = (
            floorsheet_df.loc[
                floorsheet_df["transaction_type"].str.upper() == "BUY",
                "amount"
            ].sum()
        )

        total_sell_floorsheet = (
            floorsheet_df.loc[
                floorsheet_df["transaction_type"].str.upper() == "SELL",
                "amount"
            ].sum()
        )

        st.info(f"Total Buy: {float(total_buy_florsheet):,.2f}")
        st.info(f"Total sell: {float(total_sell_floorsheet):,.2f}")
        # return {
        #     "total_buy": float(total_buy),
        #     "total_sell": float(total_sell),
        #     "floorsheet_df": floorsheet_df
        # }

        book_closure_df = db.get_today_book_closure_range(selected_date=self.selected_date)
        st.header("Book closure data that is in range of start_date and end_date")
        st.badge(f"Total BC: {len(book_closure_df)}")
        st.dataframe(book_closure_df)    
        # 2. Extract unique scripts
        scripts = (
            book_closure_df["script"]
            .dropna()
            .unique()
            .tolist()
        )
        
        filtered_df = floorsheet_df[
            floorsheet_df["symbol"].isin(scripts)
        ]

        # 5. Calculate BUY and SELL totals (amount-based)
        total_buy_bc = (
            filtered_df.loc[
                filtered_df["transaction_type"].str.upper() == "BUY",
                "amount"
            ].sum()
        )

        total_sell_bc = (
            filtered_df.loc[
                filtered_df["transaction_type"].str.upper() == "SELL",
                "amount"
            ].sum()
        )

        bc_trans_script_buy_amount = total_buy_bc
        bc_trans_script_sell_amount = total_sell_bc
        st.header(f"bc_trans_script_buy_amount: {bc_trans_script_buy_amount:,.2f}")
        st.header(f"bc_trans_script_sell_amount: {bc_trans_script_sell_amount:,.2f}")

        floorsheet_buy_amount_after_deducting_bc_trans_script = total_buy_florsheet - total_buy_bc
        floorsheet_sell_amount_after_deducting_bc_trans_script = total_sell_floorsheet - total_sell_bc

        st.header(f"floorsheet_buy_amount_after_deducting_bc_trans_script: {floorsheet_buy_amount_after_deducting_bc_trans_script:,.2f}")
        st.header(f"floorsheet_sell_amount_after_deducting_bc_trans_script: {floorsheet_sell_amount_after_deducting_bc_trans_script:,.2f}")
        
        st.markdown("---")
        st.header(f"Book closure data with T0 date")
        df_bc_t0 = db.get_today_book_closure_only(selected_date=self.selected_date)
        st.dataframe(df_bc_t0)

        st.markdown("---")
        st.header(f"Book closure data with range of start_date and end_date")
        df_list = []

        for _, row in df_bc_t0.iterrows():
            script = str(row["script"])
            start_date = str(row["start_date"])
            end_date = str(row["end_date"])

            df_range = self.get_floorsheet_by_script_and_date_range(
                script=script,
                start_date=start_date,
                end_date=end_date
            )

            if not df_range.empty:
                df_list.append(df_range)

        # Final combined dataframe
        df_holder = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
        st.badge(f"Total data: {len(df_holder)}")
        st.dataframe(df_holder, width='stretch')

        st.markdown("---")
        total_buy_bc_t0 = (
            df_holder.loc[
                df_holder["transaction_type"].str.upper() == "BUY",
                "amount"
            ].sum()
        )

        total_sell_bc_t0 = (
            df_holder.loc[
                df_holder["transaction_type"].str.upper() == "SELL",
                "amount"
            ].sum()
        )

        final_buy = total_buy_bc_t0 + floorsheet_buy_amount_after_deducting_bc_trans_script
        final_sell = total_sell_bc_t0 + floorsheet_sell_amount_after_deducting_bc_trans_script
        net_amount = final_buy - final_sell
        st.header(f"Final amount: {net_amount:,.2f}")

# ---------------------------------------------------------
# ✅ Run App
# ---------------------------------------------------------
if __name__ == "__main__":
    PayableAndReceivable().uat_page()