import streamlit as st
import pandas as pd
from datetime import datetime
from db import db
from utils import auth_utils, helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey

class PayableAndReceivable:
    def __init__(self):
        st.set_page_config("Payable & Receivable", page_icon="💸", layout='wide')
        helper.eliminate_top_padding()

        # app_state.restore_state_from_query_params()
        # app_state.sync_query_params_from_session()
        # app_state.check_authenticaiton_state()
        user = auth_utils.ensure_logged_in()
        self.username= user['username']
        self.role= user['role']
        self.branch = user['branch']
        activate_client_code_hotkey()

        navigation.render_sidebar()
        st.header("💸 Payables & Receivables", anchor=False)
        self.selected_date = st.date_input("Select Date")

        self.weekday_name = self.selected_date.strftime("%A")

    def calculate_commission(self, amount: float) -> float:
        if amount <= 50_000:
            return round(max(amount * 0.0036, 10), 2)
        elif amount <= 500_000:
            return round(amount * 0.0033, 2)
        elif amount <= 2_000_000:
            return round(amount * 0.0031, 2)
        elif amount <= 10_000_000:
            return round(amount * 0.0027, 2)
        else:
            return round(amount * 0.0024, 2)

    def get_floorsheet_by_script_and_date_range(self, script, start_date, end_date):
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

    def load_data(self, selected_date):
        key = str(selected_date)
        if key not in st.session_state:
            st.session_state[key] = {
                'floorsheet': db.get_today_floorsheet(selected_date=selected_date),
                'bc_range': db.get_today_book_closure_range(selected_date=selected_date),
                'bc_t0': db.get_today_book_closure_only(selected_date=selected_date)
            }
        data = st.session_state[key]
        return data['floorsheet'].copy(), data['bc_range'].copy(), data['bc_t0'].copy()

    def uat_page(self):
        floorsheet_df, book_closure_df, df_bc_t0 = self.load_data(self.selected_date)

        if floorsheet_df.empty:
            st.info(f"Floorsheet not found as of date {self.selected_date}", icon="📢")
            st.stop()

        floorsheet_df['broker_comm'] = floorsheet_df['amount'].apply(self.calculate_commission)
        floorsheet_df['sebon_comm'] = floorsheet_df['broker_comm'] * 0.006
        floorsheet_df['tds'] = floorsheet_df['broker_comm'] * 0.12
        floorsheet_df.drop(columns=['id'], inplace=True)
        floorsheet_df.index = floorsheet_df.index  + 1
        st.dataframe(floorsheet_df)
        tds_buy = floorsheet_df.loc[floorsheet_df["transaction_type"].str.upper() == "BUY", "tds"].sum()
        tds_sell = floorsheet_df.loc[floorsheet_df["transaction_type"].str.upper() == "SELL", "tds"].sum()


        total_tds = tds_buy + tds_sell
        # total_tds = floorsheet_df['tds'].sum()
        total_nepse_comm_buy = floorsheet_df.loc[floorsheet_df["transaction_type"].str.upper() == "BUY", "stockcomm"].sum()
        total_nepse_comm_sell= floorsheet_df.loc[floorsheet_df["transaction_type"].str.upper() == "SELL", "stockcomm"].sum()

        total_sebon_comm_buy = floorsheet_df.loc[floorsheet_df["transaction_type"].str.upper() == "BUY", "sebon_comm"].sum()
        total_sebon_comm_sell = floorsheet_df.loc[floorsheet_df["transaction_type"].str.upper() == "SELL", "sebon_comm"].sum()


        buy_mask = floorsheet_df["transaction_type"].str.upper() == "BUY"
        sell_mask = floorsheet_df["transaction_type"].str.upper() == "SELL"

        total_buy_floorsheet = floorsheet_df.loc[buy_mask, ["amount", "stockcomm", "sebon_comm"]].fillna(0).sum().sum()

        total_sell_floorsheet = (floorsheet_df.loc[sell_mask, "amount"].fillna(0).sum() -
                                 floorsheet_df.loc[sell_mask, ["stockcomm", "sebon_comm"]].fillna(0).sum().sum())
        
        # st.write(f"Nepse Buy commission: {total_nepse_comm_buy}")
        # st.write(f"Nepse Sell commission: {total_nepse_comm_sell}")
        # st.write(f"Sebon buy commission: {total_sebon_comm_buy}")
        # st.write(f"Sebon Sell commission: {total_sebon_comm_sell}")
        # st.write(f"TDS buy: {tds_buy}")
        # st.write(f"TDS sell: {tds_sell}")

        total_buy_floorsheet = total_buy_floorsheet + total_nepse_comm_buy + total_sebon_comm_buy
        total_sell_floorsheet = total_sell_floorsheet - total_nepse_comm_sell - total_sebon_comm_sell

        today_date = datetime.now().strftime("%Y-%m-%d")
        if self.selected_date == today_date:
            st.info(f"Today date is selected.")
        col1,col2 = st.columns(2)
        with col1:
            st.error(f"Total Buy: {float(total_buy_floorsheet):,.2f}")
        with col2:
            st.success(f"Total sell: {float(total_sell_floorsheet):,.2f}")

        total_buy_bc = 0
        total_sell_bc = 0
        

        if not book_closure_df.empty:
            st.markdown("---")
            st.header("Reference", anchor=False)
            st.subheader("Book closure data that is in range of start_date and end_date")
            st.badge(f"Total BC: {len(book_closure_df)}")
            book_closure_df.index = book_closure_df.index + 1
            st.dataframe(book_closure_df, width='stretch')

            scripts = book_closure_df["script"].dropna().unique().tolist()

            filtered_df = floorsheet_df[floorsheet_df["symbol"].isin(scripts)]

            bc_nepse_comm_buy = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "BUY", "stockcomm"].sum()
            bc_sebon_comm_buy = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "BUY", "sebon_comm"].sum()
            bc_tds_buy = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "BUY", "tds"].sum()
            
            bc_nepse_comm_sell = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "SELL", "stockcomm"].sum()
            bc_sebon_comm_sell = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "SELL", "sebon_comm"].sum()
            bc_tds_sell = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "SELL", "tds"].sum()

            total_buy_bc = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "BUY", "amount"].sum() + bc_nepse_comm_buy + bc_sebon_comm_buy + bc_tds_buy
            total_sell_bc = filtered_df.loc[filtered_df["transaction_type"].str.upper() == "SELL", "amount"].sum() - bc_nepse_comm_sell + bc_sebon_comm_sell + bc_tds_sell


            # st.write(f"BC BUY nepse commission: {bc_nepse_comm_buy}")
            # st.write(f"BC BUY SEBON commission: {bc_sebon_comm_buy}")
            # st.write(f"BC TDS BUY : {bc_tds_buy}")
            # st.write(f"BC SELL nepse commission: {bc_nepse_comm_sell}")
            # st.write(f"BC SELL SEBON commission: {bc_sebon_comm_sell}")
            st.write(f"BC TDS SELL : {bc_tds_sell}")
        else:
            st.info(f"Book closure data not found.", icon="ℹ️")
        try:
            floorsheet_buy_after = (total_buy_floorsheet - total_buy_bc)- bc_nepse_comm_buy - bc_sebon_comm_buy - bc_tds_buy
            floorsheet_sell_after = (total_sell_floorsheet - total_sell_bc) - bc_nepse_comm_sell - bc_sebon_comm_sell - bc_tds_sell
            col1, col2= st.columns(2)
            col3, col4 = st.columns(2)
        except Exception as e:
            floorsheet_buy_after = total_buy_floorsheet - total_buy_bc 
            floorsheet_sell_after = total_sell_floorsheet - total_sell_bc
            col1, col2= st.columns(2)
            col3, col4 = st.columns(2)

       
        if not book_closure_df.empty:
            with col1:
                st.metric("BC Buy Amount", f"{total_buy_bc:,.2f}")

            with col2:
                st.metric("BC Sell Amount", f"{total_sell_bc:,.2f}")
            with col3:
                st.metric("Buy After BC Deduct", f"{floorsheet_buy_after:,.2f}")

            with col4:
                st.metric("Sell After BC Deduct", f"{floorsheet_sell_after:,.2f}")


        # st.divider()
        # st.write(f"Total Nepse comm - total bc nepse comm BUY: {total_nepse_comm_buy - bc_nepse_comm_buy}")
        # st.write(f"Total Nepse comm - total bc nepse comm SELL: {total_nepse_comm_sell - bc_nepse_comm_sell}")
        # st.write(f"Total TDS - total bc TDS BUY: {tds_buy - bc_tds_buy}")
        # st.write(f"Total TDS - total bc TDS SELL: {tds_sell - bc_tds_sell}")

        if not df_bc_t0.empty:
            st.markdown("---")
            st.header(f"Book closure data with T0 date",anchor=False)
            df_bc_t0.drop(columns=['id', 'created_at', 'updated_by', 'updated_at'], inplace=True)
            
            df_bc_t0.index = df_bc_t0.index + 1
            st.dataframe(df_bc_t0)

            st.markdown("---")
            st.header(f"Book closure data with range of start_date and end_date", anchor=False)
            df_list = []
            for _, row in df_bc_t0.iterrows():
                df_range = self.get_floorsheet_by_script_and_date_range(str(row["script"]), str(row["start_date"]), str(row["end_date"]))
                if not df_range.empty:
                    df_list.append(df_range)

            df_holder = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
            st.badge(f"Total data: {len(df_holder)}")
            try:
                df_holder.drop(columns=["id"], inplace=True)
                df_holder.index = df_holder.index + 1
                st.dataframe(df_holder, width='stretch')

                total_buy_bc_t0 = df_holder.loc[df_holder["transaction_type"].str.upper() == "BUY", "amount"].sum()
                total_sell_bc_t0 = df_holder.loc[df_holder["transaction_type"].str.upper() == "SELL", "amount"].sum()

                final_buy = total_buy_bc_t0 + floorsheet_buy_after
                final_sell = total_sell_bc_t0 + floorsheet_sell_after

                st.markdown("---")

                net_amount = (final_buy - final_sell) + total_tds
                st.badge(f"Total TDS: {total_tds:,.2f}", color="green")
            except Exception:
                pass

        
        else:
            col1, col2 = st.columns(2)
            # st.warning(f"tetst")
            with col1:
                st.metric("Floorsheet Buy", f"{floorsheet_buy_after:,.2f}")
            with col2:   
                st.metric("Floorsheet Sell", f"{floorsheet_sell_after:,.2f}")

            net_amount = (floorsheet_sell_after - floorsheet_buy_after)

            if net_amount<0:
                st.metric("Final Amount (Payable)", f"{net_amount - total_tds:,.2f}", border=True)
            else:
                st.metric("Final Amount (Receivable)", f"{net_amount + total_tds:,.2f}", border=True)


    def uat_page_friday(self):
        st.success(f"Today is Friday", width=300)
        _, _, df_bc_t0 = self.load_data(self.selected_date)

        st.markdown("---")
        st.header(f"Book closure data with T0 date", anchor=False)
        df_bc_t0.drop(columns=['id'], inplace=True)
        df_bc_t0.index = df_bc_t0.index + 1
        st.badge(f"Total data: {len(df_bc_t0)}")
        st.dataframe(df_bc_t0)

        st.markdown("---")
        st.header(f"Book closure data with range of start_date and end_date", anchor=False)
        df_list = []
        for _, row in df_bc_t0.iterrows():
            df_range = self.get_floorsheet_by_script_and_date_range(str(row["script"]), str(row["start_date"]), str(row["end_date"]))
            if not df_range.empty:
                df_list.append(df_range)

        df_holder = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
        st.badge(f"Total data: {len(df_holder)}")

        df_holder['broker_comm'] = df_holder['amount'].apply(self.calculate_commission)
        df_holder['sebon_comm'] = df_holder['broker_comm'] * 0.006
        df_holder['tds'] = df_holder['broker_comm'] * 0.12
        df_holder.drop(columns=['id'], inplace=True)
        df_holder.index = df_holder.index + 1
        st.dataframe(df_holder, width='stretch')

        buy_mask = df_holder["transaction_type"].str.upper() == "BUY"
        sell_mask = df_holder["transaction_type"].str.upper() == "SELL"

        total_buy_floorsheet = df_holder.loc[buy_mask, ["amount", "stockcomm", "sebon_comm"]].fillna(0).sum().sum()

        total_sell_floorsheet = (df_holder.loc[sell_mask, "amount"].fillna(0).sum() -
                                 df_holder.loc[sell_mask, ["stockcomm", "sebon_comm"]].fillna(0).sum().sum())

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Buy:", f"{total_buy_floorsheet:,.2f}")
        
        with col2:
            st.metric("Total sell:", f"{total_sell_floorsheet:,.2f}")
            
        # st.header(f"Total buy: {total_buy_floorsheet:,.2f}")
        # st.header(f"Total sell: {total_sell_floorsheet:,.2f}")


        final_value = (total_buy_floorsheet - total_sell_floorsheet) + df_holder['tds'].sum()
        # st.metric("Final Rec/Pay:", f"{final_value:,.2f}")
        if final_value<0:
            st.metric("Final Amount (Receivable)", f"{final_value:,.2f}", border=True)
        else:
            st.metric("Final Amount (Payable)", f"{final_value:,.2f}", border=True)

        # st.header(f"Final Rec/Pay: {final_value:,.2f}")

    def render_ui(self):
        if self.weekday_name.upper() == 'FRIDAY':
            self.uat_page_friday()
        else:
            self.uat_page()

if __name__ == "__main__":
    PayableAndReceivable().render_ui()









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
#         st.set_page_config("Payable & Receivable", page_icon="💸", layout='wide')

#         # # Dates
#         # helper.eliminate_top_padding()
#         # self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
#         # self.today_date = datetime.now().strftime("%Y-%m-%d")
#         # self.today_np_date = nepali_date.today()

#         # # Authentication
#         # app_state.restore_state_from_query_params()
#         # app_state.sync_query_params_from_session()
#         # app_state.check_authenticaiton_state()


#         # self.username, self.role = app_state.get_current_user_info()
#         # activate_client_code_hotkey()

#         # # Sidebar
#         # navigation.render_sidebar()
#         st.header("💸 Payables & Receivables", anchor=False)
#         self.selected_date = st.date_input("Select Date")
#         self.weekday_name = self.selected_date.strftime("%A")
#         self.bc_data = None


#     def calculate_commission(self,amount: float) -> float:
#         """
#         Calculate stock commission based on transaction amount.
        
#         Parameters:
#             amount (float): Transaction amount in Rs.
            
#         Returns:
#             commission (float): Commission in Rs.
#         """
#         if amount <= 50_000:
#             # 0.36% or Rs. 10 whichever is higher
#             commission = max(amount * 0.0036, 10)
#         elif amount <= 500_000:
#             commission = amount * 0.0033
#         elif amount <= 2_000_000:
#             commission = amount * 0.0031
#         elif amount <= 10_000_000:
#             commission = amount * 0.0027
#         else:  # above 10 million
#             commission = amount * 0.0024
        
#         return round(commission, 2)
    

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
        



#     def uat_page(self):

#         floorsheet_df = db.get_today_floorsheet(selected_date=self.selected_date)
#         # Calculate broker commission per row
#         floorsheet_df['broker_comm'] = floorsheet_df['amount'].apply(self.calculate_commission)
#         floorsheet_df['sebon_comm'] = floorsheet_df['broker_comm'] * 0.006  # 0.6%
#         floorsheet_df['tds'] = floorsheet_df['broker_comm'] * 0.12  # 0.6%
#         st.dataframe(floorsheet_df)

#         total_tds = floorsheet_df['tds'].sum()
#         st.header(f"TDS Buy/sell total: {total_tds}")
#         if floorsheet_df.empty:
#             st.info(f"Floorsheet not found as of date {self.selected_date}")
#             st.stop()


#         # --- BUY total (add commissions) ---
#         buy_mask = floorsheet_df["transaction_type"].str.upper() == "BUY"
#         total_buy_floorsheet = (
#             floorsheet_df.loc[buy_mask, ["amount", "stockcomm", "sebon_comm"]]
#             .fillna(0)  # handle any NaN
#             .sum(axis=1) # sum per row
#             .sum()       # sum all rows
#         )

#         # --- SELL total (subtract commissions) ---
#         sell_mask = floorsheet_df["transaction_type"].str.upper() == "SELL"
#         total_sell_floorsheet = (
#             (floorsheet_df.loc[sell_mask, "amount"].fillna(0) -
#             floorsheet_df.loc[sell_mask, ["stockcomm", "sebon_comm"]].fillna(0).sum(axis=1))
#             .sum()
#         )



#         st.info(f"Total Buy: {float(total_buy_floorsheet):,.2f}")
#         st.info(f"Total sell: {float(total_sell_floorsheet):,.2f}")
#         # return {
#         #     "total_buy": float(total_buy),
#         #     "total_sell": float(total_sell),
#         #     "floorsheet_df": floorsheet_df
#         # }

#         book_closure_df = db.get_today_book_closure_range(selected_date=self.selected_date)
#         st.header("Book closure data that is in range of start_date and end_date")
#         st.badge(f"Total BC: {len(book_closure_df)}")
#         st.dataframe(book_closure_df)    
#         # 2. Extract unique scripts
#         scripts = (
#             book_closure_df["script"]
#             .dropna()
#             .unique()
#             .tolist()
#         )
        
#         filtered_df = floorsheet_df[
#             floorsheet_df["symbol"].isin(scripts)
#         ]

#         # 5. Calculate BUY and SELL totals (amount-based)
#         total_buy_bc = (
#             filtered_df.loc[
#                 filtered_df["transaction_type"].str.upper() == "BUY",
#                 "amount"
#             ].sum()
#         )

#         total_sell_bc = (
#             filtered_df.loc[
#                 filtered_df["transaction_type"].str.upper() == "SELL",
#                 "amount"
#             ].sum()
#         )

#         bc_trans_script_buy_amount = total_buy_bc
#         bc_trans_script_sell_amount = total_sell_bc
#         st.header(f"bc_trans_script_buy_amount: {bc_trans_script_buy_amount:,.2f}")
#         st.header(f"bc_trans_script_sell_amount: {bc_trans_script_sell_amount:,.2f}")

#         floorsheet_buy_amount_after_deducting_bc_trans_script = total_buy_floorsheet - total_buy_bc
#         floorsheet_sell_amount_after_deducting_bc_trans_script = total_sell_floorsheet - total_sell_bc

#         st.header(f"floorsheet_buy_amount_after_deducting_bc_trans_script: {floorsheet_buy_amount_after_deducting_bc_trans_script:,.2f}")
#         st.header(f"floorsheet_sell_amount_after_deducting_bc_trans_script: {floorsheet_sell_amount_after_deducting_bc_trans_script:,.2f}")
        
#         st.markdown("---")
#         st.header(f"Book closure data with T0 date")
#         df_bc_t0 = db.get_today_book_closure_only(selected_date=self.selected_date)
#         st.dataframe(df_bc_t0)

#         st.markdown("---")
#         st.header(f"Book closure data with range of start_date and end_date")
#         df_list = []

#         for _, row in df_bc_t0.iterrows():
#             script = str(row["script"])
#             start_date = str(row["start_date"])
#             end_date = str(row["end_date"])

#             df_range = self.get_floorsheet_by_script_and_date_range(
#                 script=script,
#                 start_date=start_date,
#                 end_date=end_date
#             )

#             if not df_range.empty:
#                 df_list.append(df_range)

#         # Final combined dataframe
#         df_holder = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
#         st.badge(f"Total data: {len(df_holder)}")
#         st.dataframe(df_holder, width='stretch')

#         st.markdown("---")
#         total_buy_bc_t0 = (
#             df_holder.loc[
#                 df_holder["transaction_type"].str.upper() == "BUY",
#                 "amount"
#             ].sum()
#         )

#         total_sell_bc_t0 = (
#             df_holder.loc[
#                 df_holder["transaction_type"].str.upper() == "SELL",
#                 "amount"
#             ].sum()
#         )

#         final_buy = total_buy_bc_t0 + floorsheet_buy_amount_after_deducting_bc_trans_script
#         final_sell = total_sell_bc_t0 + floorsheet_sell_amount_after_deducting_bc_trans_script

#         st.markdown("---")
#         st.header(f"After adding t0 in floorsheet buy: {final_buy}")
#         st.header(f"After adding t0 in floorsheet sell: {final_sell}")

#         net_amount = (final_buy - final_sell)
#         if net_amount<0:
#             net_amount = (final_buy - final_sell) + total_tds
#         else:
#             net_amount = (final_buy - final_sell) - total_tds


#         st.header(f"Final amount: {net_amount:,.2f}")
    
    
    
#     def uat_page_friday(self):
#         st.success(f"Today is Friday")
#         st.markdown("---")
#         st.header(f"Book closure data with T0 date")
#         df_bc_t0 = db.get_today_book_closure_only(selected_date=self.selected_date)
#         st.dataframe(df_bc_t0)

#         st.markdown("---")
#         st.header(f"Book closure data with range of start_date and end_date")
#         df_list = []


#         for _, row in df_bc_t0.iterrows():
#             script = str(row["script"])
#             start_date = str(row["start_date"])
#             end_date = str(row["end_date"])

#             df_range = self.get_floorsheet_by_script_and_date_range(
#                 script=script,
#                 start_date=start_date,
#                 end_date=end_date
#             )

#             if not df_range.empty:
#                 df_list.append(df_range)

#         # Final combined dataframe
#         df_holder = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
#         st.badge(f"Total data: {len(df_holder)}")
#         df_holder['broker_comm'] = df_holder['amount'].apply(self.calculate_commission)
#         df_holder['sebon_comm'] = df_holder['broker_comm'] * 0.006  # 0.6%
#         df_holder['tds'] = df_holder['broker_comm'] * 0.12  # 0.6%
#         st.dataframe(df_holder, width='stretch')



#         st.markdown("---")
#         # --- BUY total (add commissions) ---
#         buy_mask = df_holder["transaction_type"].str.upper() == "BUY"
#         total_buy_floorsheet = (
#             df_holder.loc[buy_mask, ["amount", "stockcomm", "sebon_comm"]]
#             .fillna(0)  # handle any NaN
#             .sum(axis=1) # sum per row
#             .sum()       # sum all rows
#         )

#         # --- SELL total (subtract commissions) ---
#         sell_mask = df_holder["transaction_type"].str.upper() == "SELL"
#         total_sell_floorsheet = (
#             (df_holder.loc[sell_mask, "amount"].fillna(0) -
#             df_holder.loc[sell_mask, ["stockcomm", "sebon_comm"]].fillna(0).sum(axis=1))
#             .sum()
#         )


#         st.header(f"Total buy: {total_buy_floorsheet:,.2f}")
#         st.header(f"Total sell: {total_sell_floorsheet:,.2f}")

#         final_value = (total_buy_floorsheet - total_sell_floorsheet) + df_holder['tds'].sum()
#         st.header(f"Final Rec/Pay: {final_value:,.2f}")





#     def render_ui(self):
#         if self.weekday_name.upper() == 'FRIDAY':
#             self.uat_page_friday()
#         else:
#             self.uat_page()

# # ---------------------------------------------------------
# # ✅ Run App
# # ---------------------------------------------------------
# if __name__ == "__main__":
#     PayableAndReceivable().render_ui()