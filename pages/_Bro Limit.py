from decimal import Decimal
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from utils import helper
from navigation import render_sidebar
from app_state import current_user
# 🔧 BRO Limit Manager Class
class BroLimitManager:
    def __init__(self):
        # helper.hide_login_page()
        st.set_page_config(page_title="Bro Limit", layout='wide', page_icon="🧑‍🦱")
        helper.adjust_ui()
        render_sidebar()
        self.engine = create_engine(helper.get_holding_engine())

    def _query(self, sql, params=None):
        try:
            return pd.read_sql(text(sql), con=self.engine, params=params)
        except Exception as e:
            st.error(f"Query error: {e}")
            return pd.DataFrame()
        
    @st.cache_data(ttl=helper.default_ttl())
    def get_bro_codes(_self):
        df = _self._query('SELECT "broCode" FROM bro_limit ORDER BY "broCode"')
        return df["broCode"].tolist()

    
    @st.cache_data(ttl=helper.default_ttl())
    def get_login_bro_code(_self, username: str):
        return _self._query('SELECT "clientCode", "clientName" FROM client_summary WHERE bro = :username', {"username": username})
        # return self._query('SELECT "clientCode", "clientName" FROM client_summary WHERE TRIM(bro) = :username', {"username": username})

    def update_total_limit(self, bro_code: str, new_limit: float):
        try:
            with self.engine.begin() as conn:
                conn.execute(text('UPDATE bro_limit SET "totalLimit" = :limit WHERE "broCode" = :code'),
                             {"limit": new_limit, "code": bro_code})
            st.success(f"Total limit updated for {bro_code}")
        except Exception as e:
            st.error(f"Error updating totalLimit: {e}")

    def update_provided_limit(self, client_code: str, bro_code: str, used_limit: float):
        try:
            with self.engine.begin() as conn:
                used_limit_decimal = float(str(used_limit))

                current_used = conn.execute(
                    text('SELECT "usedLimit" FROM bro_limit WHERE "broCode" = :code'),
                    {"code": bro_code}
                ).scalar() or 0.00

                current_assigned = conn.execute(
                    text('SELECT "assignedLimit" FROM client_summary WHERE "clientCode" = :code'),
                    {"code": client_code}
                ).scalar() or 0.00

                conn.execute(
                    text('UPDATE bro_limit SET "usedLimit" = :used WHERE "broCode" = :code'),
                    {"used": float(current_used) + used_limit_decimal, "code": bro_code}
                )
                conn.execute(
                    text('UPDATE client_summary SET "assignedLimit" = :used WHERE "clientCode" = :code'),
                    {"used": float(current_assigned) + used_limit_decimal, "code": client_code}
                )

            st.success(f"Used limit updated successfully: +{used_limit}")
        except Exception as e:
            st.error(f"Error updating usedLimit: {e}")

    # @st.cache_data(ttl=helper.default_ttl())
    def fetch_all_limits(_self):
        return _self._query('SELECT "broCode", name, "totalLimit", "usedLimit", "availableLimit" FROM bro_limit ORDER BY "broCode"')

    def fetch_login_user_limits(_self, username: str):
        return _self._query("""
            SELECT "broCode", name, "totalLimit", "usedLimit", "availableLimit"
            FROM bro_limit WHERE "broCode" = :username
        """, {"username": username})

    def client_summary(_self, username: str):
        df = _self._query("SELECT * FROM client_summary WHERE bro = :username", {"username": username})
        df.reset_index(drop=True, inplace=True)
        df = df.round(2)
        df = helper.format_negative_numbers(df)
        df.index += 1
        return df
    
    def _execute(self, sql, params=None):
        try:
            with self.engine.begin() as conn:
                conn.execute(text(sql), params or {})
        except Exception as e:
            st.error(f"Execution error: {e}")



    def check_if_new_un_cred_client_exists(self):
        check_sql = """
            SELECT 1 FROM client_summary WHERE "clientCode" = :clientCode LIMIT 1
        """
        result = self._query(check_sql, {"clientCode": client_code})
        return result
    
    def add_new_client_in_client_summary_table(self, bro, client_name, client_code, assigned_limit):

        # Step 2: Insert new client
        insert_sql = """
            INSERT INTO client_summary (
                bro, "clientName", "clientCode",
                "currentMarketValue", "profitLossAmount", "profitLossPercentage",
                "ledgerValue", "assignedLimit", category
            ) VALUES (
                :bro, :clientName, :clientCode,
                0.00, 0.00, 0.00,
                0.00, :assignedLimit, 'UN_CRED'
            )
        """
        self._execute(insert_sql, {
            "bro": bro,
            "clientName": client_name,
            "clientCode": client_code,
            "assignedLimit": assigned_limit
        })

    

# 🔌 Instantiate manager
manager = BroLimitManager()


# 🔐 Session info
role = current_user().get("role", "").upper()
username = current_user().get("username", "").upper()
print(f"Logged in as: {username} with role: {role}")
# 🧮 Admin/Manager View
if role in ['MANAGER', 'ADMIN']:
    st.title("🧮 Bro Limit Manager", anchor=False)

    bro_codes = manager.    get_bro_codes()
    selected_bro = st.selectbox("Select Bro Code", bro_codes)

    new_limit = st.number_input("Enter New Total Limit", min_value=0.0, step=0.01)
    if st.button("Update Limit"):
        manager.update_total_limit(selected_bro, new_limit)

    st.markdown("---")
    st.subheader("📊 Current BRO Limits")
    df = helper.format_dataframe(manager.fetch_all_limits())
    df.rename(columns={"Used Limit": "Assigned Limit"}, inplace=True)

    search_query = st.text_input("Search in table")

    if search_query:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

    df.index += 1
    st.dataframe(df, width='stretch')

else:
    # 👤 Individual BRO View
    st.title("🧮 Limit Manager", anchor=False)
    selected_type = st.radio(
    "Client Type",
    ["Cred Clients", "UnCred Clients"],
    horizontal=True,
    index=0  # Default selection: "Cred Clients"
    )
    if selected_type == "Cred Clients":
        # bro_code_df = manager.get_login_bro_code(username="N/A ")
        bro_code_df = manager.get_login_bro_code(username=username)
        if bro_code_df.empty:
            st.warning("No clients found for your BRO code.")
        else:
            client_options = bro_code_df["clientName"] + "  [" + bro_code_df["clientCode"] + "]"
            selected_client = st.selectbox("Select Client Code", client_options)
            client_code = selected_client.split("[")[-1].replace("]", "").strip()

            new_limit = st.number_input("Enter Limit", min_value=0.0, step=0.01)
            if st.button("Update Limit"):
                manager.update_provided_limit(client_code, username, new_limit)
    else:
        new_client = st.text_input("Enter Client Name").upper()
        new_client_code = st.text_input("Enter Client Code").upper()
        new_limit = st.number_input("Enter Limit", min_value=0.0, step=0.01)
        if st.button("Add Limit"):
            if new_client and new_client_code:
                bro = st.session_state['username'].upper()
                check_sql = """SELECT 1 FROM client_summary WHERE "clientCode" = :clientCode LIMIT 1"""
                result = manager._query(check_sql, {"clientCode": new_client_code})

                if not result.empty:
                    st.error(f"❌ Client Code '{new_client_code}' already exists.")
                else:
                    manager.add_new_client_in_client_summary_table(
                        bro=bro,
                        client_name=new_client,
                        client_code=new_client_code,
                        assigned_limit=new_limit
                    )
                    st.success(f"✅ Client '{new_client}' added with limit {new_limit}")
            else:
                st.error("⚠️ Please enter all fields.")




    st.markdown("---")
    st.subheader("📊 My Current Limit")
    df = helper.format_dataframe(manager.fetch_login_user_limits(username=username))
    df.index = df.index + 1
    st.dataframe(df, width='stretch')

    st.markdown("---")
    st.subheader("🍁 My Clients Summary")

    df = helper.format_dataframe(manager.client_summary(username=username))
    df.rename(columns={"Profit Loss Percentage": "Profit (Loss) Percentage", "Profit Loss Amount" : "Profit (Loss) Amount"}, inplace=True)
    st.dataframe(df, width='stretch')