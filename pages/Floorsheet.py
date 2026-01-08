from datetime import datetime
from nepali_datetime import date as nepali_date
import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import create_engine
import plotly.express as px
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.custom_hotkey import activate_client_code_hotkey


intranet_engine = helper.get_holding_engine()

@st.cache_data(ttl=120)
def get_floorsheet_by_date(selected_date: date):
    query = """
        SELECT f.*,
            COALESCE(m."rmName", 'N/A') AS "rmName"
        FROM floorsheet f
        LEFT JOIN client_rm_map m ON f.clientcode = m."clientCode"
        WHERE DATE(f.uploaded_at) = %s
        ORDER BY f.uploaded_at DESC;
    """
    return pd.read_sql(query, intranet_engine, params=(selected_date,))

# ✔ Cache client summary per date
@st.cache_data(ttl=120)
def compute_client_summary(df: pd.DataFrame):
    def client_summary_func(x):
        buy = x["transaction_type"] == "Buy"
        sell = x["transaction_type"] == "Sell"
        return pd.Series({
            "total_buy_quantity": x.loc[buy, "quantity"].sum(),
            "total_sell_quantity": x.loc[sell, "quantity"].sum(),
            "total_buy_amount": x.loc[buy, "amount"].sum(),
            "total_sell_amount": x.loc[sell, "amount"].sum(),
            "total_commission": x["stockcomm"].sum(),
            "total_traded_quantity": x["quantity"].sum(),
            "total_traded_volume": x["amount"].sum(),
        })
    return (
            df.groupby(["clientcode", "clientname", "rmName"], group_keys=False, observed=True)
            .apply(client_summary_func, include_groups=False)
            .reset_index()
        )


# ✔ Cache branch summary per date
@st.cache_data(ttl=120)
def compute_branch_summary(df: pd.DataFrame):
    if "branch" not in df.columns:
        return pd.DataFrame()

    def branch_summary_func(g):
        buy = g["transaction_type"] == "Buy"
        sell = g["transaction_type"] == "Sell"
        return pd.Series({
            "buyer_count": g.loc[buy, "clientcode"].nunique(),
            "seller_count": g.loc[sell, "clientcode"].nunique(),
            "both_traders": g.groupby("clientcode")["transaction_type"].nunique().eq(2).sum(),
            "purchase_turnover": g.loc[buy, "amount"].sum(),
            "sales_turnover": g.loc[sell, "amount"].sum(),
            "total": g["amount"].sum(),
        })

    # df2 = df.groupby("branch", group_keys=False).apply(branch_summary_func).reset_index()
    df2 = (
            df.groupby("branch", group_keys=False, observed=True)
            .apply(lambda g: branch_summary_func(g), include_groups=False)
            .reset_index()
        )


    total_turnover = df2["total"].sum()
    df2["%"] = (df2["total"] / total_turnover * 100).round(2)
    return df2

# ✔ Cache piechart summary per date
@st.cache_data(ttl=120)
def compute_pie_summary(df: pd.DataFrame):
    if "branch" not in df.columns:
        return pd.DataFrame()
    return df.groupby("branch")["amount"].sum().reset_index().rename(columns={"amount": "total"})


class Floorsheet:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config(page_title="Floorsheet", page_icon="📄", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()
        today = datetime.today()
        activate_client_code_hotkey()

        # Get the day name (e.g. Monday, Tuesday)
        self.day_name = today.strftime("%A")


    # ✔ FIX: Proper decorator placement
    # @st.cache_data(ttl=6000)
    # def get_floorsheet_by_date(_self, selected_date: date):
    #     query = """
    #         SELECT *
    #         FROM floorsheet
    #         WHERE DATE(uploaded_at) = %s
    #         ORDER BY uploaded_at DESC;
    #     """
    #     return pd.read_sql(query, _self.intranet_engine, params=(selected_date,))



    def render_ui(self):
        st.title("📄 Floorsheet Records", anchor=False)
        col1, col2, col3 = st.columns(3)
        search_term = ""

        with col1:
            selected_date = st.date_input("Select Date", value=date.today())

        # ✔ Query is executed only ONCE because cached
        df = get_floorsheet_by_date(selected_date)
        # print(df.columns)
        # --- Filtering UI (unchanged) ---
        with col2:
            filter_option = st.selectbox(
                "Filter by:",
                ["None", "Script", "Client Code", "Client Name", "Branch", "Buy", "Sell"]
            )

            if filter_option == "Branch" and "branch" in df.columns:
                with col3:
                    options = sorted(df["branch"].dropna().unique().tolist())
                    search_term = st.selectbox("Select Branch", options)
            elif filter_option not in ["None", "Buy", "Sell"]:
                with col3:
                    search_term = st.text_input("Search", placeholder="Enter value...")

        st.markdown("---")

        # ✔ Filtering is very cheap; keep it same
        if filter_option == "Script" and search_term:
            df = df[df["symbol"].astype(str).str.contains(search_term, case=False, na=False)]
        elif filter_option == "Client Code" and search_term:
            df = df[df["clientcode"].astype(str).str.contains(search_term, case=False, na=False)]
        elif filter_option == "Client Name" and search_term:
            df = df[df["clientname"].astype(str).str.contains(search_term, case=False, na=False)]
        elif filter_option == "Branch" and search_term:
            df = df[df["branch"].astype(str) == search_term]
        elif filter_option == "Buy":
            df = df[df["transaction_type"].str.lower() == "buy"]
        elif filter_option == "Sell":
            df = df[df["transaction_type"].str.lower() == "sell"]
        elif filter_option == "None" and search_term:
            mask = df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            df = df[mask]

        df.sort_values(by="clientname", inplace=True)
        df.reset_index(drop=True, inplace=True)

        if df.empty:
            st.warning("No data found for the selected date/search term.")
            st.stop()

        # --- RADIO BUTTON ---
        view_mode = st.radio(
            "Select View",
            ["Floorsheet", "Client Summary", "Branch Summary", "Branch Piechart", "BRO Summary"],
            horizontal=True,
            key="view_mode"
        )

        with st.spinner("Loading…"):

            # ✔ Use cached summaries instead of recomputing
            if view_mode == "Floorsheet":
                display_df = df

            elif view_mode == "Client Summary":
                display_df = compute_client_summary(df)

            elif view_mode == "Branch Summary":
                display_df = compute_branch_summary(df)

            elif view_mode == "Branch Piechart":
                display_df = compute_pie_summary(df)

            else:
                display_df = df

            st.badge(f"**Total rows :** {len(display_df):,}", color="green")

            # ----- EVERYTHING BELOW IS LITERALLY YOUR SAME UI -----
            # (No UI or logic changed — only data source is cached above)

            # --- Floorsheet View ---
            if view_mode == "Floorsheet":
                display_df = display_df.copy()
                display_df.index = display_df.index + 1
                display_df.drop(columns=['id', 'contractnumber', 'tradetime','uploaded_at', 'bankdeposit'], inplace=True)
                display_df.rename(columns={
                    "quantity":"Quantity",
                    "symbol":"Symbol",
                    "buyerbrokingfirmcode":"Buyer Broker",
                    "sellerbrokingfirmcode":"Seller Broker",
                    "clientname":"Client Name",
                    "clientcode":"Client Code",
                    "rate": "Rate",
                    "amount":"Amount",
                    "stockcomm":"Commission Gain",
                    "branch":"Branch",
                    "transaction_type": "Transaction Type",
                    "rmName": "BRO"
                }, inplace=True)

                desired = [
                    "BRO","Branch","Client Code","Client Name","Symbol","Transaction Type",
                    "Quantity","Rate","Amount","Commission Gain","Buyer Broker","Seller Broker"
                ]
                display_df = display_df[desired]

                numeric_cols = display_df.select_dtypes(include=["int64", "float64"]).columns
                display_df[numeric_cols] = display_df[numeric_cols].map(lambda x: f"{x:,}")
                st.dataframe(display_df, use_container_width=True)

            # --- Client Summary ---
            elif view_mode == "Client Summary":
                st.subheader("👨‍👩‍👧‍👦 Client Summary (Total Buy / Sell / Traded)", anchor=False)
                display_df = display_df.copy()
                display_df.index = display_df.index + 1
                display_df = display_df.round(2)
                display_df.rename(columns={
                    "clientcode":"Client Code",
                    "clientname":"Client Name",
                    "total_buy_quantity":"Total Buy Quantity",
                    "total_sell_quantity":"Total Sell Quantity",
                    "total_buy_amount":"Total Buy Amount",
                    "total_sell_amount":"Total Sell Amount",
                    "total_commission":"Total Commission Gain",
                    "total_traded_quantity":"Total Traded Quantity",
                    "total_traded_volume":"Total Traded Volume",
                    "rmName":"BRO"
                }, inplace=True)

                desired = [
                    "BRO","Client Code","Client Name","Total Buy Quantity","Total Buy Amount",
                    "Total Sell Quantity","Total Sell Amount","Total Traded Quantity",
                    "Total Traded Volume","Total Commission Gain"
                ]
                display_df = display_df[desired]

                numeric = display_df.select_dtypes(include=["int64", "float64"]).columns
                display_df[numeric] = display_df[numeric].map(lambda x: f"{x:,}")
                st.dataframe(display_df, use_container_width=True)

                st.markdown("---")
                with st.expander("📜 Client Transaction Details (Buy/Sell)"):
                    details = df[["rmName","clientcode","clientname","symbol","quantity","amount","stockcomm","transaction_type"]]
                    details = details.copy()
                    details.index = details.index + 1
                    details.rename(columns={
                        "clientcode":"Client Code","clientname":"Client Name",
                        "symbol":"Symbol","quantity":"Quantity","amount":"Amount",
                        "stockcomm":"Commission Gain","transaction_type":"Transaction Type", "rmName":"BRO"
                    }, inplace=True)

                    numeric = details.select_dtypes(include=["int64","float64"]).columns
                    details[numeric] = details[numeric].map(lambda x: f"{x:,}")
                    details = details.sort_values(by="Client Name")
                    details.reset_index(drop=True, inplace=True)
                    details.index = details.index + 1
                    st.dataframe(details, use_container_width=True)

            # --- Branch Summary ---
            elif view_mode == "Branch Summary":
                
                st.subheader("𖦥 Branch Summary : " + str(nepali_date.today()) + " (" + self.day_name + ")", anchor=False)
                if not display_df.empty:
                    df2 = display_df.copy()
                    df2.index = df2.index + 1
                    totals = df2[[
                        "buyer_count","seller_count","both_traders",
                        "purchase_turnover","sales_turnover","total"
                    ]].sum()

                    # df2.rename(columns={
                    #     "total":"Total","sales_turnover":"Sales Turnover",
                    #     "purchase_turnover":"Purchase Turnover","both_traders":"Both Traders",
                    #     "seller_count":"Total Sellers","buyer_count":"Total Buyers",
                    #     "branch":"Branch","%":"Branch Contribution %"
                    # }, inplace=True)

                    # df2 = df2.sort_values(by="Total", ascending=False)
                    # df2 = df2.round(2)

                    # numeric = df2.select_dtypes(include=["int64","float64"]).columns
                    # df2[numeric] = df2[numeric].map(lambda x: f"{x:,}")
                    # df2.reset_index(drop=True, inplace=True)
                    # df2.index = df2.index + 1

                    # cols_to_clean = ["Total Buyers", "Total Sellers", "Both Traders"]

                    # for col in cols_to_clean:
                    #     df2[col] = df2[col].apply(
                    #         lambda x: str(int(float(x))) if pd.notnull(x) else ""
                    #     )

                    # st.dataframe(df2, width='stretch')


                    # Rename columns
                    df2.rename(columns={
                        "total": "Total",
                        "sales_turnover": "Sales Turnover",
                        "purchase_turnover": "Purchase Turnover",
                        "both_traders": "Both Traders",
                        "seller_count": "Total Sellers",
                        "buyer_count": "Total Buyers",
                        "branch": "Branch",
                        "%": "Branch Contribution %"
                    }, inplace=True)

                    # Sort
                    df2 = df2.sort_values(by="Total", ascending=False)

                    # -----------------------------
                    # ADD TOTAL ROW (BEFORE FORMAT)
                    # -----------------------------
                    numeric_cols = df2.select_dtypes(include=["int64", "float64"]).columns

                    total_row = df2[numeric_cols].sum()
                    total_row["Branch"] = "TOTAL"

                    df2 = pd.concat([df2, pd.DataFrame([total_row])], ignore_index=True)

                    # -----------------------------
                    # FORMATTING
                    # -----------------------------
                    df2 = df2.round(2)

                    df2[numeric_cols] = df2[numeric_cols].map(lambda x: f"{x:,}")

                    cols_to_clean = ["Total Buyers", "Total Sellers", "Both Traders"]
                    for col in cols_to_clean:
                        df2[col] = df2[col].apply(
                            lambda x: str(int(float(x.replace(",", "")))) if pd.notnull(x) else ""
                        )

                    # Index starts from 1
                    df2.index = df2.index + 1   
                    df2.loc[df2["Branch"] == "TOTAL", "Branch Contribution %"] = 100
                    df2.index = df2.index.astype(str)
                    df2.iloc[-1, df2.columns.get_loc("Branch")] = "TOTAL"
                    df2.index = list(df2.index[:-1]) + [""]

                    def highlight_total_row(row):
                        return ["font-weight: bold"] * len(row) if row.name == df2.index[-1] else [""] * len(row)

                    styled_df = df2.style.apply(highlight_total_row, axis=1)

                    # Display
                    # st.dataframe(df2, width="stretch")
                    st.dataframe(styled_df, width="stretch")



                    # # totals row
                    # total_df = pd.DataFrame([totals])
                    # total_df.insert(0, "", "TOTAL")

                    # formatted_df = total_df.copy()
                    # formatted_df["buyer_count"] = formatted_df["buyer_count"].map("{:,.0f}".format)
                    # formatted_df["seller_count"] = formatted_df["seller_count"].map("{:,.0f}".format)
                    # formatted_df["both_traders"] = formatted_df["both_traders"].map("{:,.0f}".format)
                    # formatted_df["purchase_turnover"] = formatted_df["purchase_turnover"].map("Rs. {:,.0f}".format)
                    # formatted_df["sales_turnover"] = formatted_df["sales_turnover"].map("Rs. {:,.0f}".format)
                    # formatted_df["total"] = formatted_df["total"].map("Rs. {:,.0f}".format)

                    # formatted_df.rename(columns={
                    #     "buyer_count":"Total Buyers","seller_count":"Total Sellers",
                    #     "both_traders":"Both Traders","purchase_turnover":"Purchase Turnover",
                    #     "sales_turnover":"Sales Turnover","total":"Total"
                    # }, inplace=True)

                    # st.markdown("---")
                    # st.subheader("➤ Summary Totals", anchor=False)
                    # st.dataframe(formatted_df, width='stretch', hide_index=True)

            # --- Piechart ---
            elif view_mode == "Branch Piechart":
                st.subheader("Branch Turnover Contribution", anchor=False)
                if not display_df.empty:
                    fig = px.pie(display_df, names="branch", values="total")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No 'branch' column found in data.")
            elif view_mode == "BRO Summary":
                st.subheader("👨🏻‍🦱 BRO Summary", anchor=False)
                if display_df.empty:
                    st.info("No data")
                    return

                df2 = display_df.copy()

                # Compute per row
                df2["is_buyer"] = (df2["transaction_type"] == "Buy").astype(int)
                df2["is_seller"] = (df2["transaction_type"] == "Sell").astype(int)
                df2["purchase_turnover"] = df2.apply(lambda row: row["amount"] if row["transaction_type"] == "Buy" else 0, axis=1)
                df2["sales_turnover"] = df2.apply(lambda row: row["amount"] if row["transaction_type"] == "Sell" else 0, axis=1)
                df2["total"] = df2["purchase_turnover"] + df2["sales_turnover"]

                # Group by rmName
                grouped = df2.groupby("rmName").agg(
                    buyer_count=("is_buyer", "sum"),
                    seller_count=("is_seller", "sum"),
                    purchase_turnover=("purchase_turnover", "sum"),
                    sales_turnover=("sales_turnover", "sum"),
                    total=("total", "sum")
                ).reset_index()

                # Unique buyers/sellers per BRO
                buyers = df2[df2["is_buyer"] == 1].groupby("rmName")["clientcode"].nunique()
                sellers = df2[df2["is_seller"] == 1].groupby("rmName")["clientcode"].nunique()
                both = df2.groupby("rmName")["clientcode"].apply(lambda x: set(df2[df2["rmName"] == x.name]["clientcode"].unique()) &
                                                            set(df2[(df2["rmName"] == x.name) & (df2["is_buyer"] == 1)]["clientcode"].unique()) &
                                                            set(df2[(df2["rmName"] == x.name) & (df2["is_seller"] == 1)]["clientcode"].unique())).map(len)

                grouped = grouped.merge(buyers.rename("unique_buyers"), on="rmName", how="left")
                grouped = grouped.merge(sellers.rename("unique_sellers"), on="rmName", how="left")
                grouped["both_traders"] = grouped.apply(lambda row: len(set(df2[(df2["rmName"] == row["rmName"]) & df2["is_buyer"] == 1]["clientcode"]) &
                                                                        set(df2[(df2["rmName"] == row["rmName"]) & df2["is_seller"] == 1]["clientcode"])), axis=1)

                totals = grouped[["unique_buyers", "unique_sellers", "both_traders", "purchase_turnover", "sales_turnover", "total"]].sum()

                grouped.drop(columns=['buyer_count', 'seller_count'], inplace=True)
                grouped.rename(columns={
                    "rmName": "BRO",
                    "unique_buyers": "Total Buyers",
                    "unique_sellers": "Total Sellers",
                    "both_traders": "Both Traders",
                    "purchase_turnover": "Purchase Turnover",
                    "sales_turnover": "Sales Turnover",
                    "total": "Total"
                }, inplace=True)

                grouped["BRO Contribution %"] = (grouped["Total"] / grouped["Total"].sum() * 100).round(2)
                grouped = grouped.sort_values(by="Total", ascending=False)

                numeric_cols = [ "Purchase Turnover", "Sales Turnover", "Total"]
                # grouped = grouped["BRO" + numeric_cols]
                grouped[numeric_cols] = grouped[numeric_cols].map(lambda x: f"{x:,}")

                grouped.reset_index(drop=True, inplace=True)
                grouped.index = grouped.index + 1
                column_order = ['BRO','Total Buyers', 'Total Sellers', 'Both Traders', 'Purchase Turnover', 'Sales Turnover','Total', 'BRO Contribution %']
                grouped = grouped[column_order]
                st.dataframe(grouped, use_container_width=True)

                # # Totals
                # total_df = pd.DataFrame([{
                #     "BRO": "TOTAL",
                #     "Total Buyers": totals["unique_buyers"],
                #     "Total Sellers": totals["unique_sellers"],
                #     "Both Traders": totals["both_traders"],
                #     "Purchase Turnover": totals["purchase_turnover"],
                #     "Sales Turnover": totals["sales_turnover"],
                #     "Total": totals["total"]
                # }])

                # total_df[numeric_cols] = total_df[numeric_cols].map(lambda x: f"{x:,.0f}")
                # total_df[["Purchase Turnover", "Sales Turnover", "Total"]] = total_df[["Purchase Turnover", "Sales Turnover", "Total"]].map(lambda x: "Rs. " + x)

                # st.markdown("---")
                # st.subheader("➤ Summary Totals", anchor=False)
                # st.dataframe(total_df, hide_index=True, use_container_width=True)

if __name__ == "__main__":
    Floorsheet().render_ui()









# import streamlit as st
# import pandas as pd
# from datetime import date
# from sqlalchemy import create_engine
# import plotly.express as px  # For interactive charts
# from db import db
# import streamlit_bridge.app_state as app_state
# import streamlit_bridge.navigation as navigation

# from utils import helper
# class Floorsheet:
#     def __init__(self):
#         st.set_page_config(page_title=f"Floorsheet", page_icon="📄",layout="wide")
#         app_state.restore_state_from_query_params()
#         app_state.sync_query_params_from_session()
#         app_state.check_authenticaiton_state()
#         self.username, self.role = app_state.get_current_user_info()
#         navigation.render_sidebar() 

#         self.intranet_engine = helper.get_holding_engine()
#         self.calculate_count = 0

#     st.cache_data(ttl=6000)
#     def get_floorsheet_by_date(self,selected_date: date) -> pd.DataFrame:
#         query = """
#             SELECT *
#             FROM floorsheet
#             WHERE DATE(uploaded_at) = %s
#             ORDER BY uploaded_at DESC;
#         """
#         df = pd.read_sql(query, self.intranet_engine, params=(selected_date,))
#         return df



#     def render_ui(self):
#         st.title("📄 Floorsheet Records")
#         col1, col2, col3 = st.columns(3)
#         search_term = ""

#         with col1:
#             selected_date = st.date_input("Select Date", value=date.today())

#         # Load raw data first so we can extract unique branches
#         df = self.get_floorsheet_by_date(selected_date)

#         with col2:
#             filter_option = st.selectbox(
#                 "Filter by:",
#                 ["None", "Script", "Client Code", "Client Name", "Branch", "Buy", "Sell"]
#             )

#             # Show appropriate input depending on filter
#             if filter_option == "Branch" and "branch" in df.columns:
#                 with col3:
#                     branch_options = sorted(df["branch"].dropna().unique().tolist())
#                     search_term = st.selectbox("Select Branch", branch_options)
#             elif filter_option not in ["None", "Buy", "Sell"]:
#                 with col3:
#                     search_term = st.text_input("Search", placeholder="Enter value...")

#         st.markdown("---")

#         # Apply filter logic
#         if filter_option == "Script" and search_term:
#             df = df[df["symbol"].astype(str).str.contains(search_term, case=False, na=False)]
#         elif filter_option == "Client Code" and search_term:
#             df = df[df["clientcode"].astype(str).str.contains(search_term, case=False, na=False)]
#         elif filter_option == "Client Name" and search_term:
#             df = df[df["clientname"].astype(str).str.contains(search_term, case=False, na=False)]
#         elif filter_option == "Branch" and search_term:
#             df = df[df["branch"].astype(str) == search_term]
#         elif filter_option == "Buy":
#             df = df[df["transaction_type"].str.lower() == "buy"]
#         elif filter_option == "Sell":
#             df = df[df["transaction_type"].str.lower() == "sell"]
#         elif filter_option == "None" and search_term:
#             # fallback: search across all columns
#             mask = df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
#             df = df[mask]



#         df.sort_values(by="clientname", inplace=True)
#         df.reset_index(drop=True, inplace=True)


#         if df.empty:
#             st.warning("No data found for the selected date/search term.")
#             st.stop()

#         # Radio button
#         view_mode = st.radio(
#             "Select View",
#             ["Floorsheet", "Client Summary", "Branch Summary", "Branch Piechart"],
#             horizontal=True,
#             key="view_mode"
#         )
#         with st.spinner("Loading . . . . . ."):
#             # Determine what will be displayed + its length
#             if view_mode == "Floorsheet":
#                 display_df = df
#             elif view_mode == "Client Summary":
#                 def client_summary_func(x):
#                     buy = x["transaction_type"] == "Buy"
#                     sell = x["transaction_type"] == "Sell"
#                     return pd.Series({
#                         "total_buy_quantity": x.loc[buy, "quantity"].sum(),
#                         "total_sell_quantity": x.loc[sell, "quantity"].sum(),
#                         "total_buy_amount": x.loc[buy, "amount"].sum(),
#                         "total_sell_amount": x.loc[sell, "amount"].sum(),
#                         "total_commission": x["stockcomm"].sum(),
#                         "total_traded_quantity": x["quantity"].sum(),
#                         "total_traded_volume": x["amount"].sum(),
#                     })
#                 display_df = (
#                                 df.groupby(["clientcode", "clientname"], group_keys=False)
#                                 .apply(client_summary_func, include_groups=False)
#                                 .reset_index()
#                             )
#             elif view_mode == "Branch Summary":
#                 if "branch" in df.columns:
#                     def branch_summary_func(g):
#                         buy = g["transaction_type"] == "Buy"
#                         sell = g["transaction_type"] == "Sell"
#                         return pd.Series({
#                             "buyer_count": g.loc[buy, "clientcode"].nunique(),
#                             "seller_count": g.loc[sell, "clientcode"].nunique(),
#                             "both_traders": g.groupby("clientcode")["transaction_type"].nunique().eq(2).sum(),
#                             "purchase_turnover": g.loc[buy, "amount"].sum(),
#                             "sales_turnover": g.loc[sell, "amount"].sum(),
#                             "total": g["amount"].sum(),
#                         })
#                     display_df = df.groupby("branch", group_keys=False).apply(
#                         branch_summary_func, include_groups=False
#                     ).reset_index()
#                     total_turnover = display_df["total"].sum()
#                     display_df["%"] = (display_df["total"] / total_turnover * 100).round(2)
#                 else:
#                     display_df = pd.DataFrame()  # empty → will show info below
#             elif view_mode == "Branch Piechart":
#                 if "branch" in df.columns:
#                     display_df = df.groupby("branch")["amount"].sum().reset_index()
#                     display_df.columns = ["branch", "total"]
#                 else:
#                     display_df = pd.DataFrame().copy()
#             else:
#                 display_df = df

#             st.badge(f"**Total rows :** {len(display_df):,}", color="green")

#             if view_mode == "Floorsheet":
#                 display_df.index = display_df.index + 1
#                 display_df.drop(columns=['id', 'contractnumber', 'tradetime','uploaded_at', 'bankdeposit'], inplace=True)
#                 display_df.rename(columns={
#                     "quantity":"Quantity",
#                     "symbol":"Symbol",
#                     "buyerbrokingfirmcode":"Buyer Broker",
#                     "sellerbrokingfirmcode":"Seller Broker",
#                     "clientname":"Client Name",
#                     "clientcode":"Client Code",
#                     "rate": "Rate",
#                     "amount":"Amount",
#                     "stockcomm":"Commission Gain",
#                     "branch":"Branch",
#                     "transaction_type": "Transaction Type"
#                 }, inplace=True)

#                 desired_order = [
#                     "Branch",
#                     "Client Code",
#                     "Client Name",
#                     "Symbol",
#                     "Transaction Type",
#                     "Quantity",
#                     "Rate",
#                     "Amount",
#                     "Commission Gain",
#                     "Buyer Broker",
#                     "Seller Broker",
#                 ]

#                 display_df = display_df[desired_order]
#                 # Format all numeric columns with commas
#                 numeric_cols = display_df.select_dtypes(include=["int64", "float64"]).columns
#                 display_df[numeric_cols] = display_df[numeric_cols].map(lambda x: f"{x:,}")


#                 st.dataframe(display_df, use_container_width=True)

#             elif view_mode == "Client Summary":
#                 st.subheader("👨‍👩‍👧‍👦 Client Summary (Total Buy / Sell / Traded)", anchor=False)
#                 display_df.index = display_df.index + 1
#                 display_df = display_df.round(2)
#                 display_df.rename(columns={
#                     "clientcode":"Client Code",
#                     "clientname":"Client Name",
#                     "total_buy_quantity":"Total Buy Quantity",
#                     "total_sell_quantity":"Total Sell Quantity",
#                     "total_buy_amount":"Total Buy Amount",
#                     "total_sell_amount":"Total Sell Amount",
#                     "total_commission":"Total Commission Gain",
#                     "total_traded_quantity":"Total Traded Quantity",
#                     "total_traded_volume":"Total Traded Volume"
#                 }, inplace=True)
                
#                 desired_order = [
#                     "Client Code",
#                     "Client Name",
#                     "Total Buy Quantity",
#                     "Total Buy Amount",
#                     "Total Sell Quantity",
#                     "Total Sell Amount",
#                     "Total Traded Quantity",
#                     "Total Traded Volume",
#                     "Total Commission Gain",
#                 ]

#                 display_df = display_df[desired_order]
#                 # Format all numeric columns with commas
#                 numeric_cols = display_df.select_dtypes(include=["int64", "float64"]).columns
#                 display_df[numeric_cols] = display_df[numeric_cols].map(lambda x: f"{x:,}")

#                 st.dataframe(display_df, use_container_width=True)
#                 st.markdown("---")
#                 with st.expander("📜 Client Transaction Details (Buy/Sell)"):
#                     details = df[["clientcode", "clientname", "symbol", "quantity", "amount", "stockcomm", "transaction_type"]]
#                     details = details.sort_values(by="stockcomm", ascending=False)
#                     details.index = details.index + 1
#                     details.rename(columns={
#                         "clientcode":"Client Code",
#                         "clientname":"Client Name",
#                         "symbol":"Symbol",
#                         "quantity":"Quantity",
#                         "amount":"Amount",
#                         "stockcomm":"Commission Gain",
#                         "transaction_type":"Transaction Type",
#                     }, inplace=True)

#                     desired_order = ["Client Code", "Client Name", "Symbol", "Transaction Type", "Quantity", "Amount","Commission Gain"]

#                     # Format all numeric columns with commas
#                     numeric_cols = details.select_dtypes(include=["int64", "float64"]).columns
#                     details[numeric_cols] = details[numeric_cols].map(lambda x: f"{x:,}")

#                     details = details[desired_order]
#                     details.sort_values(by="Client Name", inplace=True)
#                     details.reset_index(inplace=True, drop=True)
#                     details.index = details.index+1
#                     st.dataframe(details, use_container_width=True)

#             elif view_mode == "Branch Summary":
#                 st.subheader("𖦥 Branch Summary")
#                 if "branch" in df.columns and not display_df.empty:
#                     display_df.index = display_df.index + 1

#                     totals = display_df[[
#                         "buyer_count", "seller_count", "both_traders",
#                         "purchase_turnover", "sales_turnover", "total"
#                     ]].sum()


#                     display_df.rename(columns={
#                         "total":"Total",
#                         "sales_turnover":"Sales Turnover",
#                         "purchase_turnover":"Purchase Turnover",
#                         "both_traders":"Both Traders",
#                         "seller_count":"Total Seller",
#                         "buyer_count":"Total Buyers",
#                         "branch" : "Branch",
#                         "%" : "Branch Contribution %"
#                     }, inplace=True)
#                     display_df = display_df.sort_values(by="Total", ascending=False)
#                     display_df = display_df.round(2)
#                     # Format numeric columns with commas
#                     numeric_cols = display_df.select_dtypes(include=["int64", "float64"]).columns
#                     display_df[numeric_cols] = display_df[numeric_cols].map(lambda x: f"{x:,}")


#                     display_df.reset_index(drop=True, inplace=True)
#                     display_df.index = display_df.index + 1
#                     st.dataframe(display_df, use_container_width=True)


#                     # Grand totals
#                     total_df = pd.DataFrame([totals])
#                     total_df.insert(0, "branch", "TOTAL")

#                     # Format numbers nicely
#                     formatted_df = total_df.copy()
#                     formatted_df["buyer_count"]     = formatted_df["buyer_count"].map("{:,.0f}".format)
#                     formatted_df["seller_count"]    = formatted_df["seller_count"].map("{:,.0f}".format)
#                     formatted_df["both_traders"]    = formatted_df["both_traders"].map("{:,.0f}".format)
#                     formatted_df["purchase_turnover"] = formatted_df["purchase_turnover"].map("Rs. {:,.0f}".format)
#                     formatted_df["sales_turnover"]    = formatted_df["sales_turnover"].map("Rs. {:,.0f}".format)
#                     formatted_df["total"]             = formatted_df["total"].map("Rs. {:,.0f}".format)

#                     formatted_df.rename(columns={
#                         "buyer_count": "Total Buyer",
#                         "seller_count": "Total Seller",
#                         "both_traders": "Both Traders",
#                         "purchase_turnover": "Purchase Turnover",
#                         "sales_turnover": "Sales Turnover",
#                         "total": "Total",
#                     }, inplace=True)

#                     st.markdown("---")
#                     st.subheader("➤ Summary Totals")
#                     # st.markdown("### ➤ Summary Totals", unsafe_allow_html=True)
#                     st.dataframe(
#                         formatted_df,
#                         use_container_width=True,
#                         hide_index=True,
#                         column_config={"branch": st.column_config.TextColumn("Branch")}
#                     )
#                 else:
#                     st.info("No 'branch' column found in data.")

#             elif view_mode == "Branch Piechart":
#                 st.subheader("Branch Turnover Contribution", anchor=False)
#                 if "branch" in df.columns and not display_df.empty:
#                     fig = px.pie(display_df, names="branch", values="total")
#                     st.plotly_chart(fig, use_container_width=True)
#                 else:
#                     st.info("No 'branch' column found in data.")

                




# if __name__ == "__main__":
#     Floorsheet().render_ui()