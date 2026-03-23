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
from utils import auth_utils, helper
from sqlalchemy import create_engine
from utils.custom_hotkey import activate_client_code_hotkey

from pages.BasePage import BasePage







@st.cache_data(ttl=120)
def get_all_kyc_info():
    rows = db.get_kyc()
    return rows

class RMTag(BasePage):
    def __init__(self):
        super().__init__()
        # helper.eliminate_top_padding()
        helper.eliminate_top_margin(margin_top="-4rem")
        st.session_state.active_menu = "rm"
        st.set_page_config(page_title="RM Tag", page_icon="🏷️", layout="wide")
        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']
        navigation.render_sidebar()
        st.title("🏷️ RM Tag", anchor=False)
        self.conn = db.get_connection()
        self.holding_engine = helper.get_holding_engine()
        activate_client_code_hotkey()


    


    # ---------------------------
    # Utility functions
    # ---------------------------
    @st.cache_data(ttl=120)
    def get_rm_list(_self, username: str ,only_self=False):
        engine = _self.holding_engine  
        if only_self and _self.role == "BRO":
            alias = helper.get_alias_name(username)
            query = 'SELECT id, alias, "full_name" FROM app_user WHERE alias = %s'
            return pd.read_sql(query, engine, params=(alias,))
        else:
            query = 'SELECT id, alias, "full_name" FROM app_user'
            return pd.read_sql(query, engine)

    @st.cache_data(ttl=120)
    def get_client_list(_self):
        engine = _self.holding_engine
        query = 'SELECT id, clientfullname, clientmembercode FROM kyc'
        return pd.read_sql(query, engine)
    

    @st.cache_data(ttl=120)
    def get_rm_client_map(_self, rm_code,  username: str):
        engine = create_engine(_self.holding_engine)

        query = """
            SELECT "clientName", "clientCode", "category" ,"assign_by", "assign_at"
            FROM client_rm_map
            WHERE "rmName" = %s
        """
        client_df = pd.read_sql(query, engine, params=(rm_code,))
        return client_df
    # ---------------------------
    # Mode handlers
    # ---------------------------
    def show_rm_clients(self):
        rm_df :pd.DataFrame = self.get_rm_list(only_self=True, username = self.username)
        rm_df["display"] = rm_df["alias"] + " - " + rm_df["full_name"]
        rm_df.sort_values(by="alias", inplace=True)

        selected_rm = st.selectbox("Select RM", rm_df["display"].tolist(), disabled=True if self.role == "BRO" else False)
        if not selected_rm:
            return

        rm_code = rm_df.loc[rm_df["display"] == selected_rm, "alias"].values[0].strip()
        client_df = self.get_rm_client_map(rm_code=rm_code, username = self.username)
        client_df.index = client_df.index + 1

        if len(client_df) >= 1:
            st.badge(f"Total Clients : {len(client_df)}", color="green")

        client_df.drop(columns=["assign_at"], inplace=True)
        client_df = client_df.map(lambda x: x.upper() if isinstance(x, str) else x)
        client_df.sort_values(by="clientName", inplace=True)
        client_df.reset_index(drop=True, inplace=True)
        client_df.index = client_df.index + 1
        client_df.rename(
            columns={"clientName": "Client Name", "clientCode": "Client Code", "assign_by": "Assign By", "category":"Category"},
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
        rm_df = self.get_rm_list(only_self=True, username = self.username)
        rm_df.sort_values(by="alias", inplace=True)
        rm_df["display"] = rm_df["alias"] + " - " + rm_df["full_name"]

        col1, col2 = st.columns(2)
        with col1:
            client_type = st.selectbox("Select Client Type", helper.default_category_list())
            client_type = client_type.split("(")[0].strip()
        with col2:
            selected_rm = st.selectbox("Select RM", rm_df["display"].tolist(), disabled=True if self.role == "BRO" else False)

        if st.button("Assign client to RM", icon="🙋🏻‍♂️"):
            client_code = selected_client.split(" - ")[0].strip()
            client_id = client_df.loc[client_df["clientmembercode"] == client_code, "id"].values[0]

            rm_row = rm_df.loc[rm_df["display"] == selected_rm].iloc[0]
            rm_id = rm_row["id"]
            rm_brocode = rm_row["alias"]
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
                    (id, "rmName", "rmFullName", "clientName", "clientCode", "assign_by", "assign_at")
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

                db.update_category_client_rm_map(client_code=client_code, new_category=client_type)
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
                    f"{rm_fullname.upper()}",
                    # f"{client_code_val} [{client_name_val}] mapped to {rm_name} - {rm_fullname.upper()}",
                    icon="➡️",
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

    def reset_transfer_state(self):
        st.session_state.transfer_done = False


    def transfer_from_file(self):

        if "transfer_done" not in st.session_state:
            st.session_state.transfer_done = False

        # -----------------------------------------
        # If transfer already done → show only success
        # -----------------------------------------
        if st.session_state.transfer_done:
            st.success("Client Transferred Successfully.", icon="✅")
            return

        st.markdown("Upload an Excel file using the exact sample format.")

        sample_df = pd.DataFrame({
            "SOURCE_RM": ["AASHISH", "UMESH"],
            "CLIENT_CODE": ["2025128767", "2024328709"],
            "DEST_RM": ["SAJAN", "YUBARAJ"]
        })

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            sample_df.to_excel(writer, index=False, sheet_name="Sample")

        st.download_button(
            label="📥 Download Sample Excel",
            data=buffer.getvalue(),
            file_name="client_transfer_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        uploaded_file = st.file_uploader(
            "Upload your filled Excel file",
            type=["xlsx"]
        )

        if uploaded_file is None:
            return

        df = pd.read_excel(uploaded_file)

        valid, msg = self.validate_transfer_rm_from_file(df)
        if not valid:
            st.error(msg)
            return

        st.success("✅ File validated successfully")
        st.badge(f"Total clients to get tagged: {len(df)}")

        df.reset_index(inplace=True, drop=True)
        df.index = df.index + 1
        st.dataframe(df)

        if st.button("Process Transfer"):
            with st.spinner("Processing..."):
                db.process_tranfer_from_file(df, assign_by=self.username)

            # ✅ mark transfer as done
            st.session_state.transfer_done = True
            st.rerun()

    # ---------------------------
    # Main UI
    # ---------------------------
    def render_ui(self):
        if self.role in ["BRO", "USER"]:
            mode = st.radio("Mode", ["Show RM Clients", "Tag RM", "Search Tagged Client"], horizontal=True, index=0)
        elif self.role in ["VIEWER"]:
            mode = st.radio("Mode", ["Show RM Clients", "Tag RM", "Search Tagged Client","Single Transfer"], horizontal=True, index=0)
        else:
            mode = st.radio("Mode", ["Show RM Clients", "Tag RM", "Search Tagged Client","Single Transfer" ,"Bulk Tag", "Bulk Transfer"], horizontal=True, index=0)

        with st.spinner("Loading data . . . ."):
            if mode == "Show RM Clients":
                self.show_rm_clients()
            elif mode == "Tag RM":
                self.tag_rm()
            elif mode == "Search Tagged Client":
                self.search_tagged_client()
            elif mode == "Bulk Tag":
                self.show_bulk_tag_ui()
            elif mode == "Single Transfer":
                view = st.radio("Transfer Mode", ["Manual Transfer", "Upload From File"], horizontal=True, index=0, on_change=self.reset_transfer_state)
                if view == "Upload From File":
                    self.transfer_from_file()
                else:
                    self.show_single_transfer_ui()
            else:
                self.show_bulk_transfer_ui()


    

    def show_single_transfer_ui(self):
        if 'client_options' not in st.session_state:
            rows = get_all_kyc_info()
            df = pd.DataFrame(rows, columns=['clientCode', 'clientName', "branch", "boid"])
            df.sort_values(by='clientName', inplace=True)
            
            def format_client(row):
                return f"{row['clientCode']} - {row['clientName']}"
            
            st.session_state.client_options = df.apply(format_client, axis=1).tolist()

        options = st.session_state.client_options
        col1, col2 = st.columns(2)
        with col1:
            selected_labels = st.multiselect("Choose clients", options, key="client_multiselect")

            # if not selected_labels:
            #     return

        # with st.form("transfer_form"):
        with col2:
            rm_df = self.get_rm_list(only_self=True, username = self.username)
            rm_df.sort_values(by="alias", inplace=True)
            rm_df["display"] = rm_df["alias"] + " - " + rm_df["full_name"]

            selected_rm_display = st.selectbox("Select RM", rm_df["display"].tolist())

            # submitted = st.form_submit_button("Transfer Now", icon="✈️")
            submitted = st.button("Transfer Now", icon="✈️")
            if submitted:
                if not selected_labels:
                    st.warning(f"Please select client to transfer.", icon="⚠️")
                    st.stop()
                selected_codes = [label.split(" - ")[0] for label in selected_labels]
                selected_rm = selected_rm_display.split(" - ")[0]
                assigned_by = self.username
                assigned_at = datetime.now()

                db.assign_clients_to_rm(
                    selected_codes=selected_codes,
                    rm_username=selected_rm,
                    assign_by=assigned_by,
                    assign_at=assigned_at,
                    updated_at=assigned_at,
                    updated_by=st.session_state.username
                )
                st.success("✅ Clients transferred successfully")
                # Optional: del st.session_state.client_options to refresh list next time
    
    
    
    
    # def show_single_transfer_ui(self):
    #     if 'client_options' not in st.session_state:
    #         rows = self.get_all_kyc_info()
    #         df = pd.DataFrame(rows, columns=['clientCode', 'clientName', "branch", "boid"])
    #         df.sort_values(by='clientName', inplace=True)
            
    #         def format_client(row):
    #             return f"{row['clientCode']} - {row['clientName']}"
            
    #         st.session_state.client_options = df.apply(format_client, axis=1).tolist()

    #     options = st.session_state.client_options
    #     selected_labels = st.multiselect("Choose clients", options, key="client_multiselect")

    #     if not selected_labels:
    #         return

    #     with st.form("transfer_form"):
    #         rm_df = self.get_rm_list(only_self=True)
    #         rm_df.sort_values(by="username", inplace=True)
    #         rm_df["display"] = rm_df["username"] + " - " + rm_df["full_name"]

    #         selected_rm_display = st.selectbox("Select RM", rm_df["display"].tolist())

    #         submitted = st.form_submit_button("Transfer Now", icon="✈️")
    #         if submitted:
    #             selected_codes = [label.split(" - ")[0] for label in selected_labels]
    #             selected_rm = selected_rm_display.split(" - ")[0]
    #             assigned_by = self.username
    #             assigned_at = datetime.now()

    #             db.assign_clients_to_rm(
    #                 selected_codes=selected_codes,
    #                 rm_username=selected_rm,
    #                 assign_by=assigned_by,
    #                 assign_at=assigned_at
    #             )
    #             st.success("✅ Clients transferred successfully")
    #             # Optional: del st.session_state.client_options to refresh list next time

                    

    def show_bulk_transfer_ui(self):
        rm_df = self.get_rm_list(only_self=True, username = self.username)
        rm_df["display"] = rm_df["alias"] + " - " + rm_df["full_name"]
        rm_df.sort_values(by="alias", inplace=True)

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

        from_rm_code = rm_df.loc[rm_df["display"] == from_selected_rm, "alias"].values[0].strip()
        to_rm_code = rm_df.loc[rm_df["display"] == to_selected_rm, "alias"].values[0].strip()
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
    
    def validate_transfer_rm_from_file(self, df: pd.DataFrame):
        expected_cols = ["SOURCE_RM", "CLIENT_CODE", "DEST_RM"]

        # Check exact match
        if list(df.columns) != expected_cols:
            return False, f"Invalid columns. Expected: {expected_cols}, Got: {list(df.columns)}"

        # Check empty values
        if df.isnull().any().any():
            return False, "File contains empty values. Please fix and upload again."

        return True, "OK"




if __name__ == "__main__":
    RMTag().render_ui()