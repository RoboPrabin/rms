import streamlit as st
import pandas as pd
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
import uuid


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

    def render_ui(self):
        mode = st.radio("Mode", ["Show RM Clients", "Tag RM", "Search Tagged Client"], horizontal=True, index=0)

        with st.spinner("Loading data . . . ."):
            if mode == "Show RM Clients":
                # Fetch RM list
                rm_df = pd.read_sql('SELECT id, "broCode", "fullName" FROM rm', self.conn)
                rm_df["display"] = rm_df["broCode"] + " - " + rm_df["fullName"]
                rm_df.sort_values(by='broCode', inplace=True)
                selected_rm = st.selectbox("Select RM", rm_df["display"].tolist())
                # print(selected_rm)

                if selected_rm:
                    rm_code = rm_df.loc[rm_df["display"] == selected_rm, "broCode"].values[0].strip()

                    # Correct query with proper quoting
                    query = """
                        SELECT "clientName", "clientCode", "assignBy", "assignAt"
                        FROM client_rm_map
                        WHERE "rmName" = %s
                    """
                    client_df = pd.read_sql(query, self.conn, params=[rm_code])
                    client_df.index = client_df.index + 1
                    if len(client_df) >=1 :
                        st.caption("Total Clients : " + str(len(client_df)))
                    client_df.drop(columns=['assignAt'], inplace=True)
                    client_df = client_df.map(lambda x: x.upper() if isinstance(x, str) else x)
                    client_df.sort_values(by='clientName', inplace=True)
                    client_df.reset_index(drop=True,inplace=True)
                    client_df.index = client_df.index + 1   
                    client_df.rename(columns={'clientName':'Client Name', 'clientCode':'Client Code', 'assignBy':'Assign By'}, inplace=True)
                    st.dataframe(client_df)
                    
            elif mode == "Tag RM":
                # Dropdown for Client
                client_df = pd.read_sql('SELECT id, clientfullname, clientmembercode FROM kyc', self.conn)
                client_df.sort_values(by='clientfullname', inplace=True)
                client_df["display"] = client_df["clientmembercode"] + " - " + client_df["clientfullname"]
                # client_df["display"].sort_values(by="clientfullname", inplace=True)
            
                selected_client = st.selectbox("Select Client", client_df["display"].tolist())

                # Dropdown for RM (broCode + fullName)
                rm_df = pd.read_sql('SELECT id, "broCode", "fullName" FROM rm', self.conn)
                rm_df.sort_values(by='broCode', inplace=True)
                rm_df["display"] = rm_df["broCode"] + " - " + rm_df["fullName"]
                selected_rm = st.selectbox("Select RM", rm_df["display"].tolist())

                if st.button("Assign client to RM"):
                    client_code = selected_client.split(" - ")[0].strip()
                    client_id = client_df.loc[client_df["clientmembercode"] == client_code, "id"].values[0]

                    rm_row = rm_df.loc[rm_df["display"] == selected_rm].iloc[0]
                    rm_id = rm_row["id"]
                    rm_brocode = rm_row["broCode"]
                    rm_fullname = rm_row["fullName"]

                    # Check if client already tagged
                    check_query = "SELECT \"rmName\" FROM client_rm_map WHERE \"clientCode\" = %s"
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
                            "DEV-TEST",
                            # self.username,
                        )

                        with self.conn.cursor() as cur:
                            cur.execute(insert_query, values)
                            self.conn.commit()

                        st.success(f"Client {client_code} successfully assigned to RM {rm_brocode} - {rm_fullname}.")

            else:
                # client_code = st.text_input("Enter client code", icon="🏷️").upper()

                # if client_code.strip():  # only run if something entered
                #     query = """
                #         SELECT "rmName", "rmFullName"
                #         FROM client_rm_map
                #         WHERE "clientCode" = %s
                #     """
                #     with self.conn.cursor() as cur:
                #         cur.execute(query, (client_code.strip(),))
                #         result = cur.fetchone()

                #     if result:
                #         rm_name, rm_fullname = result
                #         st.success(f"Client {client_code} is tagged to RM: {rm_name} - {rm_fullname}", icon='👍')
                #     else:
                #         st.warning(f"No RM assigned for client code {client_code}.", icon='⚠️')



                client_code = st.text_input("Enter client code", icon="🏷️").upper()

                if client_code.strip():  # only run if something entered
                    query = """
                        SELECT "clientCode", "clientName", "rmName", "rmFullName"
                        FROM client_rm_map
                        WHERE "clientCode" LIKE %s
                        ORDER BY "clientCode"
                    """
                    with self.conn.cursor() as cur:
                        # Add % for prefix search
                        cur.execute(query, (client_code.strip() + "%",))
                        results = cur.fetchall()

                    if results:
                        if len(results) == 1:
                            # Exactly one match
                            client_code_val, client_name_val, rm_name, rm_fullname = results[0]
                            st.success(
                                f"{client_code_val} [{client_name_val}] mapped to {rm_name} - {rm_fullname.upper()}",
                                icon="👍"
                            )
                        else:
                            # Multiple matches → show them in a table
                            st.info("Multiple matches found:")
                            match_df = pd.DataFrame(
                                results,
                                columns=["Client Code", "Client Name", "RM Name", "RM Full Name"]
                            )
                            match_df.index = match_df.index + 1
                            st.dataframe(match_df, use_container_width=True)
                    else:
                        st.warning(
                            f"No RM assigned for client code starting with {client_code}.",
                            icon="⚠️"
                        )
if __name__ == "__main__":
    RMTag().render_ui()