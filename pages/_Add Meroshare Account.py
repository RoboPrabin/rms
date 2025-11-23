from app_state import current_user
from navigation import render_sidebar
import pandas as pd
import streamlit as st
import sqlalchemy
from config import config
from utils import helper

class Meroshare:
    def __init__(self):
        st.set_page_config(page_title="Meroshare", layout="wide", page_icon="✨")
        helper.adjust_ui()
        render_sidebar()
        st.title("📝 Add MeroShare Account", anchor=False)
        self.role = current_user()['role']
        self.engine = sqlalchemy.create_engine(helper.get_holding_engine())

    def show_input_fields(self):
        # Input fields
        client_name = st.text_input("Client Name", help="Username cannot be change, once added.").title()
        dp = st.text_input("DP")
        username = st.text_input("Username").upper()
        password = st.text_input("Password", type="password")
        has_verified = st.selectbox("Has Verified Credentials", options=["-select-","Yes", "No"])
        category = st.text_input("Cateogry", value="CRED", disabled=True)


        # Submit button
        if st.button("Submit"):
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
                                    "bro": self.loggedin_user['username'].upper()
                                }
                            )
                            st.success("✅ MeroShare account info added successfully!")
                            

                except Exception as e:
                    st.error(f"❌ Failed to insert data: {e}")



    # @st.cache_data(helper.default_ttl())
    def load_data(self):
        if self.role in ["MANAGER", "ADMIN"]:
            df = pd.read_sql("SELECT * FROM meroshare_acc", self.engine)
        else:
            df = pd.read_sql(
                "SELECT * FROM meroshare_acc WHERE bro = %s",
                self.engine,
                params=(self.loggedin_user['username'].upper(),)
            )
        return df
    

    def load_and_display_data(self):
        try:
            # role = self.role
            df = self.load_data()
            df.reset_index(drop=True, inplace=True)
            df.index = df.index + 1  
                
            df.drop(columns=['id'], inplace=True)
            column_order = ['clientName', 'category','dp', 'username', 'password','hasVerifiedCredentials', 'bro']
            total_count = len(df)
            df = df[column_order]
            df.rename(columns=lambda x: helper.camel_to_title(x), inplace=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(f"<h3>👥 Total MeroShare Accounts : {total_count}</h3>", unsafe_allow_html=True)

            if df.empty:
                st.info("No MeroShare accounts registered yet.")
            else:
                search_query = st.text_input("Search Meroshare Account")

                if search_query:
                    df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

                df.index += 1
                st.dataframe(df, width='stretch')
                # st.dataframe(df, width='stretch')

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
        self.show_input_fields()
        self.load_and_display_data()

if __name__ == "__main__":
    meroshare = Meroshare()
    meroshare.render_meroshare_page()