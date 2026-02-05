import uuid
from time import sleep
from db import db
from decimal import Decimal
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from utils import helper
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from utils.custom_hotkey import activate_client_code_hotkey
from pages.ClientLimit import ClientLimit
from config.config import credentials_tms_for_collateral_only
from api.tms import api_collateral



def get_client_list(bro):
    rows = db.get_table_rm_child_map_for_client_limit_by_bro(rm_name=bro)
    df = pd.DataFrame(rows, columns=['BRO','BROFullName','Client Name', 'Client Code', 'Category'])
    return df

cookies, session_id = db.get_tms_session()

def get_headers(referer:str ='https://tms48.nepsetms.com.np/tms/member/search/client-search',):
    return {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'host-session-id': session_id,
        'origin': 'https://tms48.nepsetms.com.np',
        'priority': 'u=1, i',
        'referer': referer,
        'request-owner': credentials_tms_for_collateral_only['server_id'],
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'x-xsrf-token': cookies['XSRF-TOKEN'],

    }




class BroLimitManager:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "rm"
        st.set_page_config(page_title="BRO Limit", layout='wide', page_icon="🧑‍🦱")
        # app_state.restore_state_from_query_params()
        # app_state.sync_query_params_from_session()
        # app_state.check_authenticaiton_state()
        app_state.enforce_authentication()
        app_state.sync_local_storage_to_session()
        self.username, self.role, self.branch = app_state.get_current_user_info()

        activate_client_code_hotkey()
        helper.adjust_ui()
        render_sidebar()
        self.engine = create_engine(helper.get_holding_engine())

    def _query(self, sql, params=None):
        try:
            return pd.read_sql(text(sql), con=self.engine, params=params)
        except Exception as e:
            st.error(f"Query error: {e}")
            return pd.DataFrame()
        
    # @st.cache_data(ttl=helper.default_ttl())
    def get_bro_codes(_self):
        df = _self._query("""SELECT username, full_name, role FROM app_user WHERE role = 'BRO' ORDER BY username""")
        df.sort_values(by="username", inplace=True)
        return df["username"] + " - " + df['full_name'].tolist()

    
    # @st.cache_data(ttl=helper.default_ttl())
    def get_login_bro_code(_self, username: str):
        return _self._query('SELECT "clientCode", "clientName" FROM client_rm_map WHERE "rmName" = :username', {"username": username})
        # return self._query('SELECT "clientCode", "clientName" FROM client_summary WHERE TRIM(bro) = :username', {"username": username})

    # def update_total_limit(self, bro_code: str, new_limit: float):
    #     try:
    #         with self.engine.begin() as conn:
    #             conn.execute(text('UPDATE bro_limit SET "totalLimit" = :limit WHERE "broCode" = :code'),
    #                          {"limit": new_limit, "code": bro_code})
    #         st.success(f"Limit updated for {bro_code}")
    #     except Exception as e:
    #         st.error(f"Error updating totalLimit: {e}")

    def update_total_limit(self, bro_name: str, bro_code: str, new_limit: float):
        try:
            with self.engine.begin() as conn:
                query = text("""
                    INSERT INTO bro_limit (id, name, "broCode", "totalLimit")
                    VALUES (:id, :name, :code, :limit)
                    ON CONFLICT ("broCode")
                    DO UPDATE SET 
                        "totalLimit" = EXCLUDED."totalLimit",
                        name = EXCLUDED.name;
                """)
                conn.execute(query, {
                    "id": uuid.uuid4(),       # UUID string passed from params
                    "name": bro_name,   # Name passed from params
                    "code": bro_code,
                    "limit": new_limit
                })
            st.success(f"Limit updated/inserted for {bro_code}")
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
        # return _self._query('SELECT "broCode", name, "totalLimit", "usedLimit", "availableLimit" FROM bro_limit ORDER BY "broCode"')
        return _self._query("""SELECT 
                    u.username, 
                    u."full_name", 
                    l."totalLimit"
                FROM app_user u
                JOIN bro_limit l ON u.username = l."broCode"
                WHERE u.role = 'BRO';   
            """)

    def fetch_login_user_limits(_self, username: str):
        return _self._query("""
            SELECT "broCode", name, "totalLimit"
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


    def tms_api(self, client_code, limit_amount):
        result = api_collateral.load_collateral_for_specific_client(headers=get_headers(), cookies=cookies, amount=limit_amount, 
            client_code=client_code, loaded_by=self.username.upper())
        if result.lower() == "success":
            banner = st.empty()
            banner.success(f"Client '{client_code}' with amount {limit_amount} updated successfully.", icon="✅")
            sleep(0.4)
            banner.empty()
        else:
            st.error(f"Something went wrong: {result}")
    
    def show_set_limit_ui(self, client):
        with st.expander(f"Set Limit on TMS: {client.upper()}", expanded=True):
            client_code = str(client).split("-")[0].strip()
            has_from_db = False
            category_from_db = db.get_category_client_rm_map(client_code=client_code)
            if category_from_db == None:
                set_category = helper.default_category_list()
            else:
                set_category = category_from_db
                has_from_db = True

            selected_category = st.selectbox("Category", set_category)


            if selected_category != "None":
                if not has_from_db:
                    if st.button("Update category", icon="🗂️"):
                        result = db.update_category_client_rm_map(client_code=client_code, new_category=selected_category)
                        if result == 1:
                            st.success(f"Category updated successfully.", icon="✅")
                            sleep(0.3)
                            st.rerun()
                            # limit_amount = st.number_input("Credit For Sale Limit")
                            # if st.button("Update Limit", icon="💷"):
                            #     self.tms_api(client_code=client_code, limit_amount=limit_amount)
                # elif has_from_db:
                #     limit_amount = st.number_input("Credit For Sale Limit")
                #     if st.button("Update Limit", icon="💷"):
                #         self.tms_api(client_code=client_code, limit_amount=limit_amount)
    
    def limiter(self):
        if 'client_map' not in st.session_state:
            st.session_state.client_map = get_client_list(bro=self.username)

        df = st.session_state.client_map
        df['Client Name'] = df['Client Name'].str.upper()
        # =====================
        # BRO DROPDOWN
        # =====================
        bro_map = (
            df[['BRO', 'BROFullName']]
            .drop_duplicates()
            .assign(display=lambda x: x['BRO'] + " - " + x['BROFullName'])
        )

        col1, col2 = st.columns(2)

        with col1:
            selected_bro = st.selectbox(
                "BRO",
                bro_map['BRO'],
                format_func=lambda bro: bro_map.loc[
                    bro_map['BRO'] == bro, 'display'
                ].values[0]
            )

        # =====================
        # FILTER CLIENTS BY BRO
        # =====================
        filtered_df = df[df['BRO'] == selected_bro]



        filtered_df = filtered_df.copy()

        filtered_df = filtered_df.sort_values(
            by="Client Name",
            ascending=True
        )

        filtered_df['Display'] = (
            filtered_df['Client Code'].astype(str)
            + " - "
            + filtered_df['Client Name']
        )

        options = filtered_df['Display'].tolist()


        st.badge(
            f"Total Mapped Clients: {len(filtered_df):,.0f}",
            color="green"
        )

        # =====================
        # CLIENT DROPDOWN
        # =====================
        with col2:
            selected_client = st.selectbox("Select Client", options)

        if selected_client != "None":
            self.show_set_limit_ui(client=selected_client)

    


manager = BroLimitManager()
if manager.role in ['MANAGER', 'ADMIN', 'MANAGEMENT']:
    st.title("🧮 BRO Limit Manager", anchor=False)
    col1, col2 = st.columns(2)
    bro_codes = manager.get_bro_codes()
    with col1:
        selected_bro = st.selectbox("Select BRO Code", bro_codes)
        st.write(selected_bro)
    with col2:
        new_limit = st.number_input("Limit for BRO", min_value=0, step=1)
    if st.button("Update Limit"):
        bro_code = selected_bro.split("-")[0].strip()
        bro_name = selected_bro.split("-")[1].strip()
        manager.update_total_limit(bro_code=bro_code, bro_name=bro_name, new_limit=new_limit)

    st.markdown("---")
    st.subheader("📊 Current BRO Limits", anchor=False)
    df = helper.format_dataframe(manager.fetch_all_limits())
    df.rename(columns={"Used Limit": "Assigned Limit"}, inplace=True)

    search_query = st.text_input("Search in table")

    if search_query:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

    df.index += 1
    st.dataframe(df, width='stretch')

else:
    # 👤 Individual BRO View
    st.title("🧮 Client Limit Manager", anchor=False)
    selected_type = st.radio(
    "Client Type",
    ["My Clients", 'Limiter'],
    # ["Cred Clients", "UnCred Clients"],
    horizontal=True,
    index=0
    )
    if selected_type == "My Clients":
        bro_code_df = manager.get_login_bro_code(username=manager.username)
        if bro_code_df.empty:
            st.warning("No clients found for your BRO code.")
        else:
            bro_code_df = bro_code_df.sort_values(by="clientName")
            client_options = bro_code_df["clientCode"] + " - " + bro_code_df["clientName"].str.upper()
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_client = st.selectbox("Select Client Code", client_options)
            client_code = selected_client.split("-")[0].strip()
            with col2:
                new_credit_limit = st.number_input("Credit Limit", min_value=0, step=1)
            with col3:
                trading_limit = st.number_input("Trading Limit", min_value=0, step=1)
            if st.button("Update Limit", icon="🔄️"):
                # manager.update_provided_limit(client_code, manager.username, new_limit)
                banner = st.empty()
                db.update_limits(client_code=client_code, credit_limit=new_credit_limit, trading_limit=trading_limit, updated_by=manager.username.upper())
                banner.success(f"Limit updated successfully.", icon="✅")
                sleep(1)
                banner.empty()
            
            st.markdown("---")
            st.subheader("📊 My Current Limit", anchor=False)
            df = helper.format_dataframe(manager.fetch_login_user_limits(username=manager.username))
            df.rename(columns={'Bro Code': 'BRO Code'}, inplace=True)
            df.index = df.index + 1
            st.dataframe(df, width='stretch')

            st.markdown("---")
            st.subheader("🍁 My Clients Summary", anchor=False)

            # df = helper.format_dataframe(manager.client_summary(username=manager.username))
            # df.rename(columns={"Profit Loss Percentage": "Profit (Loss) Percentage", "Profit Loss Amount" : "Profit (Loss) Amount"}, inplace=True)
            rows = db.get_clients_by_rm(rm_name=manager.username)
            df = pd.DataFrame(rows, columns=['Client Code', 'Client Name', 'Category', 'Credit Limit', 'Trading Limit'])
            df.sort_values(by="Client Name", inplace=True)
            df.reset_index(inplace=True, drop=True)
            df.index = df.index + 1
            df['Client Name'] = df['Client Name'].str.upper()
            st.badge(f"Total Clients: {len(df)}", color='green')
            st.dataframe(df, width='stretch')
                        
    
    elif selected_type == 'Limiter':
        manager.limiter()

    
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




   