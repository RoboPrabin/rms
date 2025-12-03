import streamlit as st
import pandas as pd
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
import uuid
from sqlalchemy import text
from utils import helper
from sqlalchemy import create_engine


class RMTag:
    def __init__(self):
        st.set_page_config(page_title="RM Tag", page_icon="🏷️", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()
        st.title("🏷️ RM Tag", anchor=False)
        self.conn = db.get_connection()
        self.holding_engine = helper.get_holding_engine()

    # ---------------------------
    # Utility functions
    # ---------------------------
    def get_rm_list(self, only_self=False):
        engine = self.holding_engine  # use your cached SQLAlchemy engine
        if only_self and self.role == "BRO":
            rm_code = self.username.upper()
            query = 'SELECT id, "username", "full_name" FROM app_user WHERE "username" = %s'
            return pd.read_sql(query, engine, params=(rm_code,))
        else:
            query = 'SELECT id, "username", "full_name" FROM app_user'
            return pd.read_sql(query, engine)

    def get_client_list(self):
        engine = self.holding_engine
        query = 'SELECT id, clientfullname, clientmembercode FROM kyc'
        return pd.read_sql(query, engine)
    
    
    # ---------------------------
    # Mode handlers
    # ---------------------------
    def show_rm_clients(self):
        rm_df = self.get_rm_list(only_self=True)
        rm_df["display"] = rm_df["username"] + " - " + rm_df["full_name"]
        rm_df.sort_values(by="username", inplace=True)

        selected_rm = st.selectbox("Select RM", rm_df["display"].tolist())
        if not selected_rm:
            return

        rm_code = rm_df.loc[rm_df["display"] == selected_rm, "username"].values[0].strip()
        

        engine = create_engine(self.holding_engine)

        query = """
            SELECT "clientName", "clientCode", "assignBy", "assignAt"
            FROM client_rm_map
            WHERE "rmName" = %s
        """
        client_df = pd.read_sql(query, engine, params=(rm_code,))



        # query = """
        #     SELECT "clientName", "clientCode", "assignBy", "assignAt"
        #     FROM client_rm_map
        #     WHERE "rmName" = %s
        # """
        # client_df = pd.read_sql(query, self.conn, params=[rm_code])


        client_df.index = client_df.index + 1

        if len(client_df) >= 1:
            st.caption(f"Total Clients : {len(client_df)}")

        client_df.drop(columns=["assignAt"], inplace=True)
        client_df = client_df.map(lambda x: x.upper() if isinstance(x, str) else x)
        client_df.sort_values(by="clientName", inplace=True)
        client_df.reset_index(drop=True, inplace=True)
        client_df.index = client_df.index + 1
        client_df.rename(
            columns={"clientName": "Client Name", "clientCode": "Client Code", "assignBy": "Assign By"},
            inplace=True,
        )
        if len(client_df)==0:
            st.info("No clients are tagged on this rm.", icon="ℹ️")
            return
        st.dataframe(client_df)

    def tag_rm(self):
        client_df = self.get_client_list()
        client_df.sort_values(by="clientfullname", inplace=True)
        client_df["display"] = client_df["clientmembercode"] + " - " + client_df["clientfullname"]

        selected_client = st.selectbox("Select Client", client_df["display"].tolist())
        rm_df = self.get_rm_list(only_self=True)
        rm_df.sort_values(by="username", inplace=True)
        rm_df["display"] = rm_df["username"] + " - " + rm_df["full_name"]

        selected_rm = st.selectbox("Select RM", rm_df["display"].tolist())

        if st.button("Assign client to RM"):
            client_code = selected_client.split(" - ")[0].strip()
            client_id = client_df.loc[client_df["clientmembercode"] == client_code, "id"].values[0]

            rm_row = rm_df.loc[rm_df["display"] == selected_rm].iloc[0]
            rm_id = rm_row["id"]
            rm_brocode = rm_row["username"]
            rm_fullname = rm_row["full_name"]

            # Check if client already tagged
            check_query = 'SELECT "rmName" FROM client_rm_map WHERE "clientCode" = %s'
            with self.conn.cursor() as cur:
                cur.execute(check_query, (client_code,))
                existing = cur.fetchall()

            if existing:
                current_rm = existing[0][0]
                st.warning(f"Client {client_code} is already tagged to RM: {current_rm}")
            else:
                insert_query = """
                    INSERT INTO client_rm_map
                    (id, "rmName", "rmFullName", "clientName", "clientCode", "assignBy", "assignAt")
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                values = (
                    str(uuid.uuid4()),
                    rm_brocode,
                    rm_fullname,
                    client_df.loc[client_df["clientmembercode"] == client_code, "clientfullname"].values[0],
                    client_code,
                    self.username,  # use current user instead of hardcoded DEV-TEST
                )

                with self.conn.cursor() as cur:
                    cur.execute(insert_query, values)
                    self.conn.commit()

                st.success(f"Client {client_code} successfully assigned to RM {rm_brocode} - {rm_fullname}.")

    def search_tagged_client(self):
        client_code = st.text_input("Enter client code", icon="🏷️").upper()
        if not client_code.strip():
            return

        query = """
            SELECT "clientCode", "clientName", "rmName", "rmFullName"
            FROM client_rm_map
            WHERE "clientCode" LIKE %s
            ORDER BY "clientCode"
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (client_code.strip() + "%",))
            results = cur.fetchall()

        if results:
            if len(results) == 1:
                client_code_val, client_name_val, rm_name, rm_fullname = results[0]
                st.success(
                    f"{client_code_val} [{client_name_val}] mapped to {rm_name} - {rm_fullname.upper()}",
                    icon="👍",
                )
            else:
                st.info("Multiple matches found:")
                match_df = pd.DataFrame(
                    results, columns=["Client Code", "Client Name", "RM Name", "RM Full Name"]
                )
                match_df.index = match_df.index + 1
                st.dataframe(match_df, use_container_width=True)
        else:
            st.warning(f"No RM assigned for client code starting with {client_code}.", icon="⚠️")

    # ---------------------------
    # Main UI
    # ---------------------------
    def render_ui(self):
        mode = st.radio("Mode", ["Show RM Clients", "Tag RM", "Search Tagged Client"], horizontal=True, index=0)
        with st.spinner("Loading data . . . ."):
            if mode == "Show RM Clients":
                self.show_rm_clients()
            elif mode == "Tag RM":
                self.tag_rm()
            else:
                self.search_tagged_client()


if __name__ == "__main__":
    RMTag().render_ui()