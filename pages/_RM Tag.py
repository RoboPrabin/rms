from time import sleep
import uuid
from datetime import datetime
from io import BytesIO
from time import sleep
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

    @st.cache_data(ttl=6000)
    def get_client_list(_self):
        engine = _self.holding_engine
        query = 'SELECT id, clientfullname, clientmembercode FROM kyc'
        return pd.read_sql(query, engine)
    

    @st.cache_data(ttl=6000)
    def get_rm_client_map(_self, rm_code):
        engine = create_engine(_self.holding_engine)

        query = """
            SELECT "clientName", "clientCode", "assignBy", "assignAt"
            FROM client_rm_map
            WHERE "rmName" = %s
        """
        client_df = pd.read_sql(query, engine, params=(rm_code,))
        return client_df
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
        
        client_df = self.get_rm_client_map(rm_code=rm_code)
        



        # query = """
        #     SELECT "clientName", "clientCode", "assignBy", "assignAt"
        #     FROM client_rm_map
        #     WHERE "rmName" = %s
        # """
        # client_df = pd.read_sql(query, self.conn, params=[rm_code])


        client_df.index = client_df.index + 1

        if len(client_df) >= 1:
            st.badge(f"Total Clients : {len(client_df)}", color="green")

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
        mode = st.radio("Mode", ["Show RM Clients", "Tag RM", "Search Tagged Client", "Bulk Tag", "Bulk Transfer"], horizontal=True, index=3)
        with st.spinner("Loading data . . . ."):
            if mode == "Show RM Clients":
                self.show_rm_clients()
            elif mode == "Tag RM":
                self.tag_rm()
            elif mode == "Search Tagged Client":
                self.search_tagged_client()
            elif mode == "Bulk Tag":
                self.show_bulk_tag_ui()
            else:
                self.show_bulk_transfer_ui()


    def show_bulk_transfer_ui(self):
        rm_df = self.get_rm_list(only_self=True)
        rm_df["display"] = rm_df["username"] + " - " + rm_df["full_name"]
        rm_df.sort_values(by="username", inplace=True)

        col1, col2, col3= st.columns(3)
        with col1:
            from_selected_rm = st.selectbox("From RM", rm_df["display"].tolist())
            if not from_selected_rm:
                return
        with col2:
            to_selected_rm = st.selectbox("To RM", rm_df["display"].tolist())
            if not to_selected_rm:
                return
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # 👈 alignment spacer
            transfer_button = st.button("Transfer All Clients", icon="➡️")

        from_rm_code = rm_df.loc[rm_df["display"] == from_selected_rm, "username"].values[0].strip()
        to_rm_code = rm_df.loc[rm_df["display"] == to_selected_rm, "username"].values[0].strip()
        to_rm_full_name = rm_df.loc[rm_df["display"] == to_selected_rm, "full_name"].values[0].strip()
        if transfer_button:
            if from_rm_code.strip() == to_rm_code.strip():
                st.error(f"[Invalid Operation] You cannot transfer client to same RM, please choose different RM Code.", icon="🚨")
                st.stop()
            else:
                rows_effected = db.transfer_bulk_clients(from_rm=from_rm_code, to_rm=to_rm_code, to_rm_full_name=to_rm_full_name)
                if rows_effected == 0:
                    st.warning(f"{rows_effected} rows effected. There were no clients on RM '{from_rm_code}' to transfer.", icon="⚠️")
                    st.stop()
                else:
                    st.success("Clients transferred successfully.", icon="✅")
                    sleep(1)
                    st.rerun()

    def show_bulk_tag_ui(self):
        st.subheader("🗃️ Bulk Clients Tag", anchor=False)

        # -----------------------------------------
        # Session state flags
        # -----------------------------------------
        if "bulk_tag_done" not in st.session_state:
            st.session_state.bulk_tag_done = False

        if "bulk_tag_count" not in st.session_state:
            st.session_state.bulk_tag_count = 0

        # -----------------------------------------
        # After processing: show success and stop
        # -----------------------------------------
        if st.session_state.bulk_tag_done:
            st.success(f"✅ Bulk tagging completed. Inserted {st.session_state.bulk_tag_count} rows.")

            # Reset flags for next run
            st.session_state.bulk_tag_done = False
            st.session_state.bulk_tag_count = 0

            st.stop()

        # -----------------------------------------
        # Sample file download
        # -----------------------------------------
        st.markdown("Upload an Excel file using the exact sample format.")

        sample_df = pd.DataFrame({
            "clientCode": ["C001", "C002"],
            "clientName": ["John Doe", "John Doe"],
            "rmName": ["UMESH", "YUBARAJ"]
        })

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            sample_df.to_excel(writer, index=False, sheet_name="Sample")

        st.download_button(
            label="📥 Download Sample Excel",
            data=buffer.getvalue(),
            file_name="bulk_tag_sample.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # -----------------------------------------
        # File uploader (NO session_state key)
        # -----------------------------------------
        uploaded_file = st.file_uploader(
            "Upload your filled Excel file",
            type=["xlsx"]
        )

        if uploaded_file is None:
            return

        # -----------------------------------------
        # Validate file
        # -----------------------------------------
        df = pd.read_excel(uploaded_file)

        valid, msg = self.validate_bulk_tag_file(df)
        if not valid:
            st.error(msg)
            return

        st.success("✅ File validated successfully")
        st.badge(f"Total clients to get tagged: {len(df)}")

        df.reset_index(inplace=True, drop=True)
        df.index = df.index + 1
        st.dataframe(df)

        # -----------------------------------------
        # Process button
        # -----------------------------------------
        if st.button("Process Bulk Tag"):
            with st.spinner("Processing..."):
                updated = db.process_bulk_tag(df, assign_by=self.username)

            # Store result
            st.session_state.bulk_tag_done = True
            st.session_state.bulk_tag_count = updated

            st.rerun()

    def validate_bulk_tag_file(self, df: pd.DataFrame):
        expected_cols = ["clientCode", "clientName", "rmName"]

        # Check exact match
        if list(df.columns) != expected_cols:
            return False, f"Invalid columns. Expected: {expected_cols}, Got: {list(df.columns)}"

        # Check empty values
        if df.isnull().any().any():
            return False, "File contains empty values. Please fix and upload again."

        return True, "OK"




if __name__ == "__main__":
    RMTag().render_ui()