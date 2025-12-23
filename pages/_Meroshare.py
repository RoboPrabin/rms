from time import sleep
import streamlit_bridge.app_state as app_state
from streamlit_bridge.navigation import render_sidebar
import pandas as pd
import streamlit as st
import sqlalchemy
from config import config
from utils import helper
from utils.custom_hotkey import activate_client_code_hotkey

class Meroshare:
    def __init__(self):
        st.set_page_config(page_title="Meroshare", layout="wide", page_icon="📝")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()

        activate_client_code_hotkey()
        helper.adjust_ui()
        render_sidebar()
        self.total_accounts = 0
        self.engine = sqlalchemy.create_engine(helper.get_holding_engine())
        if self.role in ["BRO", "ADMIN"]:
            st.title("📝 Add MeroShare Account", anchor=False)


    def show_input_fields(self):

        with st.form("submit_meroshare", clear_on_submit=True):
            # Input fields
            col1, col2 = st.columns(2)
            with col1:
                client_name = st.text_input("Client Name").title()
            with col2:
                dp = st.text_input("DP")
            
            col3, col4 = st.columns(2)
            with col3:
                username = st.text_input("Username", help="Username cannot be change, once added.").upper()
            with col4:
                password = st.text_input("Password", type="password")


            col5, col6 = st.columns(2)
            with col5:
                has_verified = st.selectbox("Has Verified Credentials", options=["-select-","Yes", "No"])
            with col6:
                category = st.text_input("Cateogry", value="CRED", disabled=True)

            submitted = st.form_submit_button("Submit")

            # Submit button
            if submitted:
                if not client_name or not dp or not username or not password:
                    st.warning("Please fill in all fields.")
                elif has_verified == "-select-":
                    st.warning("Please select a valid option for 'Has Verified Credentials'.")
                elif not dp.isdigit():
                    st.warning("DP should be a valid integer.")
                else:
                    verified_bool = has_verified == "Yes"
                    dp_int = int(dp)

                    try:
                        engine = sqlalchemy.create_engine(helper.get_holding_engine())
                        with engine.begin() as conn:
                            result = conn.execute(
                                sqlalchemy.text("SELECT 1 FROM meroshare_acc WHERE username = :username"),
                                {"username": username}
                            ).fetchone()

                            if result:
                                st.warning("Username already exists. Please use a different one.")
                            else:
                                # ✅ Insert new record
                                conn.execute(
                                    sqlalchemy.text("""
                                        INSERT INTO meroshare_acc (id,"clientName", category ,dp, username, password, "hasVerifiedCredentials", bro)
                                        VALUES (gen_random_uuid(), :cname , :category ,:dp,:username, :password, :verified, :bro)
                                    """),
                                    {
                                        "dp": dp_int,
                                        "cname":client_name,
                                        "category": category,
                                        "username": username,
                                        "password": password,
                                        "verified": verified_bool,
                                        "bro": self.username.upper()
                                    }
                                )
                                st.success("✅ MeroShare account info added successfully!")
                                sleep(1)
                                st.rerun()

                    except Exception as e:
                        st.error(f"❌ Failed to insert data: {e}")



    # @st.cache_data(helper.default_ttl())
    def load_data(self):
        if self.role in ["MANAGER", "ADMIN", "MANAGEMENT"]:
            df = pd.read_sql("SELECT * FROM meroshare_acc", self.engine)
        else:
            df = pd.read_sql(
                "SELECT * FROM meroshare_acc WHERE bro = %s",
                self.engine,
                params=(self.username.upper(),)
            )
        return df


    def load_and_display_data(self):
        try:
            # role = self.role
            df = self.load_data()
            # if self.role == "MANAGER":
            df.reset_index(drop=True, inplace=True)
            df.index = df.index + 1  
                
            df.drop(columns=['id'], inplace=True)
            column_order = ['bro','clientName', 'category','dp', 'username', 'password','hasVerifiedCredentials',  'password_expired', 'account_expired', 'demat_expired' ,'login_message']
            total_count = len(df)
            self.total_accounts = total_count 
            df = df[column_order]
            df.rename(columns=lambda x: helper.camel_to_title(x), inplace=True)
            df.rename(columns={"Login_Message":"Login Message", "Password_Expired":"Password Expired", "Account_Expired":"Account Expired", "Demat_Expired":"Demat Expired"}, inplace=True)
            # df.rename(columns={""})
            df.sort_values(by="Bro", inplace=True)


            if self.role != ["MANAGER", "MANAGEMENT"]:
                # st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown(f"<h3>👥 Total MeroShare Accounts : {total_count}</h3>", unsafe_allow_html=True)
            # elif self.role in ["MANAGER", "MANAGEMENT"]:
            #     st.title(f"👥 Total MeroShare Accounts : {total_count}", anchor=False)

            # print(df.columns)
            if df.empty:
                st.info("No MeroShare accounts registered yet.")
            else:
                search_query = st.text_input("Search Meroshare Account")

                if search_query:
                    df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]
                if self.role in ["MANAGER", "MANAGEMENT"]:
                    df.drop(columns=['Password'], inplace=True)
                
                
                st.dataframe(df, width='stretch')

                if self.role == ["BRO"]:
                    # 🔧 Add edit/delete controls per row
                    for i, row in df.iterrows():
                        with st.expander(f"🔧 Manage: {row['Client Name']}"):
                            st.write(f"DP: {row['Dp']}")
                            st.write(f"Verified: {row['Has Verified Credentials']}")

                            # 📝 Edit form
                            with st.form(f"edit_form_{i}"):
                                new_dp = st.text_input("DP", value=str(row['Dp']))
                                new_password = st.text_input("Password", value=row['Password'], type="password")
                                new_verified = st.selectbox(
                                    "Has Verified Credentials",
                                    ["Yes", "No"],
                                    index=0 if row['Has Verified Credentials'] else 1
                                )
                                submitted = st.form_submit_button("Update")
                                if submitted:
                                    try:
                                        with self.engine.begin() as conn:
                                            conn.execute(
                                                sqlalchemy.text("""
                                                    UPDATE meroshare_acc
                                                    SET dp = :dp, password = :password, "hasVerifiedCredentials" = :verified
                                                    WHERE username = :username
                                                """),
                                                {
                                                    "dp": int(new_dp),
                                                    "password": new_password,
                                                    "verified": new_verified == "Yes",
                                                    "username": row['Username']
                                                }
                                            )
                                        st.success("✅ Updated successfully!")
                                        df = self.load_data()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Update failed: {e}")

                            # 🗑️ Delete button
                            if st.button(f"Delete {row['Username']}", key=f"delete_{i}"):
                                try:
                                    with self.engine.begin() as conn:
                                        conn.execute(
                                            sqlalchemy.text("DELETE FROM meroshare_acc WHERE username = :username"),
                                            {"username": row['Username']}
                                        )
                                    st.success(f"🗑️ Deleted {row['Username']} successfully!")
                                    df = self.load_data()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Delete failed: {e}")

        except Exception as e:
            st.error(f"❌ Failed to load data: {e}")

    def render_meroshare_page(self):
        if self.role in ["MANAGER", "MANAGEMENT"]:
            self.load_and_display_data()
        else:
            self.show_input_fields()
            self.load_and_display_data()

if __name__ == "__main__":
    meroshare = Meroshare()
    meroshare.render_meroshare_page()