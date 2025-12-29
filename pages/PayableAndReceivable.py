from db import db
import streamlit as st
import pandas as pd
from datetime import datetime
from nepali_datetime import date as nepali_date

from utils import helper
from utils.custom_hotkey import activate_client_code_hotkey
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation


class PayableAndReceivable:

    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config(
            page_title="Payable & Receivable",
            page_icon="💸",
            layout="wide"
        )

        # Dates
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.today_np_date = nepali_date.today()

        # Auth
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()

        self.username, self.role = app_state.get_current_user_info()
        activate_client_code_hotkey()

        # Sidebar
        navigation.render_sidebar()
        st.header("💸 Payables & Receivables", anchor=False)
        self.selected_date = st.date_input("Select date")
        self.weekday = self.selected_date.strftime("%A")
        # Cache data
        self.floorsheet_df = db.get_today_floorsheet(selected_date=self.selected_date)
        if self.floorsheet_df.empty:
            st.info(f"Floorsheet not found to selected date. Please choose different date.")
            st.stop()
        self.book_closure_df = db.get_today_book_closure_range(selected_date=self.selected_date)
        self.book_closure_only_df = db.get_today_book_closure_only(selected_date = self.selected_date)

    # --------------------------------------------------
    # 🔹 Utility Methods
    # --------------------------------------------------

    @staticmethod
    def calculate_buy_sell(df: pd.DataFrame):
        if df.empty:
            return 0.0, 0.0

        grouped = (
            df.assign(tt=df["transaction_type"].str.upper())
              .groupby("tt")["amount"]
              .sum()
        )

        return (
            float(grouped.get("BUY", 0.0)),
            float(grouped.get("SELL", 0.0))
        )

    # --------------------------------------------------
    # 🔹 Business Logic
    # --------------------------------------------------

    def today_floorsheet_summary(self):
        buy, sell = self.calculate_buy_sell(self.floorsheet_df)
        return buy, sell

    def today_book_closure_summary(self):
        if self.book_closure_df.empty or self.floorsheet_df.empty:
            return 0.0, 0.0

        scripts = self.book_closure_df["script"].dropna().unique()
        filtered_df = self.floorsheet_df[
            self.floorsheet_df["symbol"].isin(scripts)
        ]

        return self.calculate_buy_sell(filtered_df)

    def book_closure_range_summary(self):
        if self.book_closure_only_df.empty:
            return pd.DataFrame()

        results = []

        for _, row in self.book_closure_only_df.iterrows():
            fs_df = db.get_floorsheet_by_script_and_date_range(
                row["script"],
                row["start_date"],
                row["end_date"]
            )

            buy, sell = self.calculate_buy_sell(fs_df)

            results.append({
                "script": row["script"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "total_buy": buy,
                "total_sell": sell,
                "net_amount": buy - sell
            })

        return pd.DataFrame(results)

    # --------------------------------------------------
    # 🔹 UI Layer
    # --------------------------------------------------
    def render_page(self):
        with st.spinner("Loading .....", show_time=True):
            today_buy, today_sell = self.today_floorsheet_summary()
            bc_today_buy, bc_today_sell = self.today_book_closure_summary()

            summary_df = self.book_closure_range_summary()
            range_buy = summary_df["total_buy"].sum() if not summary_df.empty else 0.0
            range_sell = summary_df["total_sell"].sum() if not summary_df.empty else 0.0

            buy_after_bc = (today_buy - bc_today_buy) - range_buy
            sell_after_bc = (today_sell - bc_today_sell) - range_sell
            total_payable_receivable = buy_after_bc - sell_after_bc

            st.markdown("<br>", unsafe_allow_html=True)
            # st.divider()
            col1, col2= st.columns(2)
            if total_payable_receivable <0:
                st.balloons()
            col1.metric(label=f"Total Payables/Receivables on {db.get_t3_date(selected_date=self.selected_date)}", value=f"Rs. {total_payable_receivable:,.2f}", border=True)
            st.divider()

            col1, col2 = st.columns(2)
            if self.selected_date.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d"):
                col1.metric(label="Today's Floorsheet BUY", value=f"Rs. {today_buy:,.2f}")
                col2.metric(label="Today's Floorsheet SELL", value=f"Rs. {today_sell:,.2f}")
            else:
                col1.metric(label=f"{self.weekday} Floorsheet BUY", value=f"Rs. {today_buy:,.2f}")
                col2.metric(label=f"{self.weekday} Floorsheet SELL", value=f"Rs. {today_sell:,.2f}")


            st.divider()
            col1, col2= st.columns(2)
            col1.metric(label="Sell after Book Closure", value=f"Rs. {sell_after_bc:,.2f}")
            col2.metric(label="Buy after Book Closure", value=f"Rs. {buy_after_bc:,.2f}")





# --------------------------------------------------
# ✅ Run App
# --------------------------------------------------
if __name__ == "__main__":
    PayableAndReceivable().render_page()












# from db import db
# import streamlit_hotkeys as hotkeys
# import plotly.express as px
# from datetime import datetime, timedelta
# from nepali_datetime import date as nepali_date
# from datetime import datetime
# import streamlit as st
# import pandas as pd
# from utils import helper
# import streamlit_bridge.app_state as app_state
# import streamlit_bridge.navigation as navigation
# from utils.formatting import *
# from utils.custom_hotkey import activate_client_code_hotkey
# class PayableAndReceivable:
#     def __init__(self):
#         helper.eliminate_top_padding()
#         st.set_page_config("Payable & Receivable", page_icon="💸", layout='wide')

#         # Dates
#         self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
#         self.today_date = datetime.now().strftime("%Y-%m-%d")
#         self.today_np_date = nepali_date.today()

#         # Authentication
#         app_state.restore_state_from_query_params()
#         app_state.sync_query_params_from_session()
#         app_state.check_authenticaiton_state()


#         self.username, self.role = app_state.get_current_user_info()
#         activate_client_code_hotkey()

#         # Sidebar
#         navigation.render_sidebar()
#         st.header("💸 Payables & Receivables", anchor=False)

                

#     def get_floorsheet_by_script_and_date_range(self,script, start_date, end_date):
#         query = """
#             SELECT *
#             FROM floorsheet
#             WHERE symbol = %s
#             AND uploaded_at::date BETWEEN %s AND %s
#         """
#         conn = db.get_connection()

#         with conn.cursor() as cur:
#             cur.execute(query, (script, start_date, end_date))
#             rows = cur.fetchall()
#             columns = [desc.name for desc in cur.description]
#             return pd.DataFrame(rows, columns=columns)






#     def calculate_today_book_closure_buy_sell(self):
#         """
#         Calculate total BUY and SELL amounts from today's floorsheet
#         for scripts present in today's book closure data.

#         Returns:
#             dict: {
#                 'scripts': list[str],
#                 'total_buy': float,
#                 'total_sell': float,
#                 'filtered_df': pd.DataFrame
#             }
#         """

#         # 1. Get today's book-closure data
#         book_closure_df = db.get_today_book_closure_range()

#         if book_closure_df.empty:
#             return {
#                 "scripts": [],
#                 "total_buy": 0.0,
#                 "total_sell": 0.0,
#                 "filtered_df": book_closure_df
#             }

#         # 2. Extract unique scripts
#         scripts = (
#             book_closure_df["script"]
#             .dropna()
#             .unique()
#             .tolist()
#         )

#         # 3. Get today's floorsheet
#         floorsheet_df = db.get_today_floorsheet()

#         if floorsheet_df.empty:
#             return {
#                 "scripts": scripts,
#                 "total_buy": 0.0,
#                 "total_sell": 0.0,
#                 "filtered_df": floorsheet_df
#             }

#         # 4. Filter floorsheet for book-closure scripts
#         filtered_df = floorsheet_df[
#             floorsheet_df["symbol"].isin(scripts)
#         ]

#         # 5. Calculate BUY and SELL totals (amount-based)
#         total_buy = (
#             filtered_df.loc[
#                 filtered_df["transaction_type"].str.upper() == "BUY",
#                 "amount"
#             ].sum()
#         )

#         total_sell = (
#             filtered_df.loc[
#                 filtered_df["transaction_type"].str.upper() == "SELL",
#                 "amount"
#             ].sum()
#         )

#         return {
#             "scripts": scripts,
#             "total_buy": float(total_buy),
#             "total_sell": float(total_sell),
#             "filtered_df": filtered_df
#         }


#     def calculate_today_floorsheet_buy_sell(self):
#         """
#         Calculate total BUY and SELL amounts from today's floorsheet.

#         Returns:
#             dict: {
#                 'total_buy': float,
#                 'total_sell': float,
#                 'floorsheet_df': pd.DataFrame
#             }
#         """

#         floorsheet_df = db.get_today_floorsheet()

#         if floorsheet_df.empty:
#             return {
#                 "total_buy": 0.0,
#                 "total_sell": 0.0,
#                 "floorsheet_df": floorsheet_df
#             }

#         total_buy = (
#             floorsheet_df.loc[
#                 floorsheet_df["transaction_type"].str.upper() == "BUY",
#                 "amount"
#             ].sum()
#         )

#         total_sell = (
#             floorsheet_df.loc[
#                 floorsheet_df["transaction_type"].str.upper() == "SELL",
#                 "amount"
#             ].sum()
#         )

#         return {
#             "total_buy": float(total_buy),
#             "total_sell": float(total_sell),
#             "floorsheet_df": floorsheet_df
#         }


#     def calculate_book_closure_range_buy_sell(self):
#         """
#         For each script in today's book closure:
#         - Fetch floorsheet data between start_date and end_date
#         - Calculate total BUY and SELL amounts

#         Returns:
#             pd.DataFrame with:
#             ['script', 'start_date', 'end_date', 'total_buy', 'total_sell', 'net_amount']
#         """

#         df_bc = db.get_today_book_closure_only()

#         if df_bc.empty:
#             return df_bc

#         results = []

#         for _, row in df_bc.iterrows():
#             script = row["script"]
#             start_date = row["start_date"]
#             end_date = row["end_date"]

#             # Fetch floorsheet for script + date range
#             fs_df = self.get_floorsheet_by_script_and_date_range(
#                 script=script,
#                 start_date=start_date,
#                 end_date=end_date
#             )

#             if fs_df.empty:
#                 total_buy = 0.0
#                 total_sell = 0.0
#             else:
#                 total_buy = (
#                     fs_df.loc[
#                         fs_df["transaction_type"].str.upper() == "BUY",
#                         "amount"
#                     ].sum()
#                 )

#                 total_sell = (
#                     fs_df.loc[
#                         fs_df["transaction_type"].str.upper() == "SELL",
#                         "amount"
#                     ].sum()
#                 )

#             results.append({
#                 "script": script,
#                 "start_date": start_date,
#                 "end_date": end_date,
#                 "total_buy": float(total_buy),
#                 "total_sell": float(total_sell),
#                 "net_amount": float(total_buy - total_sell)
#             })

#         return pd.DataFrame(results)


#     def render_page(self):



#         today_book_closure_result = self.calculate_today_book_closure_buy_sell()
#         business_summary = self.calculate_today_floorsheet_buy_sell()
#         st.header("Today's Floorsheet BUY: " + str(business_summary['total_buy']))
#         st.header("Today's Floorsheet SELL: " + str(business_summary['total_sell']))






#         st.subheader("📊 Book Closure – Buy/Sell Summary (Date Range Wise)")

#         summary_df = self.calculate_book_closure_range_buy_sell()
#         col1, col2, col3 = st.columns(3)

#         today_buy_after_book_close = (business_summary['total_buy'] - today_book_closure_result['total_buy']) - summary_df['total_buy'].sum()
#         today_sell_after_book_close = (business_summary['total_sell'] - today_book_closure_result['total_sell']) - summary_df['total_sell'].sum()
#         st.markdown("---")
#         st.header("Buy Amount after Book Closure: " + str(today_buy_after_book_close))
#         st.header("Sell Amount after Book Closure: " + str(today_sell_after_book_close))


#         st.header(f"Total Payables/Receivables is : {today_buy_after_book_close - today_sell_after_book_close}")




# # ---------------------------------------------------------
# # ✅ Run App
# # ---------------------------------------------------------
# if __name__ == "__main__":
#     PayableAndReceivable().render_page()