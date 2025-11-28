import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import create_engine
import plotly.express as px  # For interactive charts
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation

from utils import helper
class Floorsheet:
    def __init__(self):
        st.set_page_config(page_title=f"Floorsheet", page_icon="📄",layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar() 

        self.intranet_engine = helper.get_intranet_engine()


    def get_floorsheet_by_date(self,selected_date: date) -> pd.DataFrame:
        query = """
            SELECT *
            FROM floorsheet
            WHERE DATE(uploaded_at) = %s
            ORDER BY uploaded_at DESC;
        """
        df = pd.read_sql(query, self.intranet_engine, params=(selected_date,))
        return df
    

    def render_ui(self):
        # --------------------------
        # Streamlit UI
        # --------------------------
        st.title("📄 Floorsheet Records")

        # Date selector
        selected_date = st.date_input(
            label="Select Date",
            value=date.today(),
            help="Floorsheet entries will load based on this date."
        )

        # Search box
        search_term = st.text_input(
            label="🔍 Search",
            placeholder="Type to filter (symbol, client name, etc.)"
        )

        st.markdown("---")

        # Load data
        df = self.get_floorsheet_by_date(selected_date)

        # Apply search filter
        if search_term:
            mask = df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            df = df[mask]

        if df.empty:
            st.warning("No data found for the selected date/search term.")
        else:
            st.dataframe(df, use_container_width=True)

            # ----------------------
            # Client Summary
            # ----------------------
            st.markdown("---")
            st.subheader("📊 Client Summary (Total Buy / Sell / Traded)")

            def client_summary_func(x):
                total_buy_qty = x.loc[x["transaction_type"]=="Buy", "quantity"].sum()
                total_sell_qty = x.loc[x["transaction_type"]=="Sell", "quantity"].sum()
                total_buy_amt = x.loc[x["transaction_type"]=="Buy", "amount"].sum()
                total_sell_amt = x.loc[x["transaction_type"]=="Sell", "amount"].sum()
                total_comm = x["stockcomm"].sum()
                total_traded_qty = total_buy_qty + total_sell_qty
                total_traded_volume = total_buy_amt + total_sell_amt
                return pd.Series({
                    "total_buy_quantity": total_buy_qty,
                    "total_sell_quantity": total_sell_qty,
                    "total_buy_amount": total_buy_amt,
                    "total_sell_amount": total_sell_amt,
                    "total_commission": total_comm,
                    "total_traded_quantity": total_traded_qty,
                    "total_traded_volume": total_traded_volume
                })

            client_summary = df.groupby(["clientcode","clientname"]).apply(client_summary_func).reset_index()
            st.dataframe(client_summary, use_container_width=True)

            # Client Transaction Table in expander
            st.markdown("---")
            with st.expander("🔽 Client Transaction Details (Buy/Sell)"):
                client_transactions = df[["clientcode", "clientname", "symbol", "quantity", "amount", "stockcomm", "transaction_type"]]
                st.dataframe(client_transactions.sort_values(["clientcode","symbol"]), use_container_width=True)

            # ----------------------
            # Branch Summary
            # ----------------------
            st.markdown("---")
            st.subheader("📊 Branch Summary")

            if "branch" in df.columns:
                def branch_summary_func(df_branch):
                    buyer_count = df_branch.loc[df_branch["transaction_type"]=="Buy", "clientcode"].nunique()
                    seller_count = df_branch.loc[df_branch["transaction_type"]=="Sell", "clientcode"].nunique()
                    both_traders = df_branch.groupby("clientcode")["transaction_type"].nunique().eq(2).sum()
                    purchase_turnover = df_branch.loc[df_branch["transaction_type"]=="Buy", "amount"].sum()
                    sales_turnover = df_branch.loc[df_branch["transaction_type"]=="Sell", "amount"].sum()
                    total = purchase_turnover + sales_turnover
                    return pd.Series({
                        "buyer_count": buyer_count,
                        "seller_count": seller_count,
                        "both_traders": both_traders,
                        "purchase_turnover": purchase_turnover,
                        "sales_turnover": sales_turnover,
                        "total": total
                    })

                branch_summary = df.groupby("branch").apply(branch_summary_func).reset_index()
                # Calculate % contribution
                total_turnover = branch_summary["total"].sum()
                branch_summary["%"] = (branch_summary["total"] / total_turnover * 100).round(2)
                st.dataframe(branch_summary, use_container_width=True)

                # ----------------------
                # Branch Pie Chart
                # ----------------------
                st.markdown("---")
                st.subheader("📈 Branch Turnover Contribution")
                print(branch_summary)
                fig = px.pie(
                    branch_summary,
                    names="branch",
                    values="total",
                    title="Branch Contribution to Total Turnover",
                    hover_data=["buyer_count","seller_count","both_traders"],
                    labels={"total":"Total Turnover"}
                )
                st.plotly_chart(fig, width='stretch')

            else:
                st.info("No 'branch' column found in data.")


if __name__ == "__main__":
    Floorsheet().render_ui()