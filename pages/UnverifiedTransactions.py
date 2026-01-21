import uuid
import re
from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import helper


@st.dialog("Confirm Deletion")
def confirm_delete_dialog(selected_indexes):
    st.warning("Do you want to delete the selected transaction(s)?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Yes, Delete"):
            # Remove rows safely (reverse order)
            for idx in sorted(selected_indexes, reverse=True):
                del st.session_state.transactions[idx]

            st.success("Selected transaction(s) deleted.")
            st.rerun()

    with col2:
        if st.button("❌ No"):
            st.info("Deletion cancelled.")
            st.rerun()


@st.dialog("Edit / Delete Transaction", width='medium')
def edit_delete_dialog(row):
    st.write("### Update Details")

    client_code = st.text_input(
        "Client Code",
        value=row.get("client_code", "")
    )
    receipt_no = st.text_input(
        "Receipt No",
        value=row.get("receipt_no", "")
    )
    bank_name = st.text_input(
        "Bank Name",
        value=row.get("bank_name", "")
    )

    # Placeholder for success messages (OUTSIDE columns)
    msg_box = st.empty()

    col1, spacer, col2 = st.columns([1, 4.3, 1])

    with col1:
        if st.button("✅ Update", use_container_width=True):
            db.update_unverified_transaction(
                description=row["description"],
                client_code=client_code,
                receipt_no=receipt_no,
                bank_name=bank_name
            )
            msg_box.success("Transaction updated successfully.", icon="✅")
            sleep(1)
            st.rerun()

    with col2:
        if st.button("🗑️ Delete", use_container_width=True):
            db.delete_unverified_transaction(row["description"])
            msg_box.success("Transaction deleted successfully.", icon="✅")
            sleep(1)
            st.rerun()



class UnverifiedTransactions:
    def __init__(self):
        
        # helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config(page_title="Unverified Transactions", page_icon="⚠️", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        st.header("⚠️ Unverified Transactions", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        self.session_ids = None

        # --- Initialize session state ---
        if "transactions" not in st.session_state:
            st.session_state.transactions = []




    def parse_transaction_input(self, raw_input):
        tokens = raw_input.split()
        transaction_date = " ".join(tokens[:3])

        numbers = re.findall(r'[\d,]+\.\d+|[-]', raw_input)
        if len(numbers) >= 3:
            withdraw, deposit, balance = numbers[-3:]
        else:
            withdraw, deposit, balance = "-", "-", "-"

        temp_str = raw_input.replace(transaction_date, "").strip()
        for num in numbers[-3:]:
            temp_str = temp_str.replace(num, "").strip()

        parts = temp_str.split("  ")
        if len(parts) >= 2:
            description, remarks = parts[0], parts[1]
        else:
            description, remarks = temp_str, ""

        return {
            "Transaction Date": transaction_date,
            "Description": description.strip(),
            "Remarks": remarks.strip(),
            "Withdraw": withdraw.strip(),
            "Deposit": deposit.strip(),
            "Balance (NPR)": balance.strip(),
            "Client Code": None,
            "Receipt No":None,
            "Bank Name":None
        }

    def add_transaction(self):
        raw_input = st.session_state.input_trans
        if raw_input.strip() != "":
            parsed_row = self.parse_transaction_input(raw_input)
            # Append to session
            st.session_state.transactions.append(parsed_row)
            # Clear transaction input only
            st.session_state.input_trans = ""


    def show_input_ui(self):
        st.text_input(
            "Enter transaction",
            key="input_trans",
            on_change=self.add_transaction  # ← this is the key fix
        )
        row_selected = False
        # --- Show table ---
        if st.session_state.transactions:
            df = pd.DataFrame(st.session_state.transactions)
            df.index = df.index + 1
            st.dataframe(df, key="entry_data", selection_mode='multi-row', on_select='rerun')
            # --- Read selected rows ---
            selection = st.session_state.get("entry_data", {}).get("selection", {})
            selected_rows = selection.get("rows", [])

            if selected_rows:
                row_selected = True
                st.info(f"{len(selected_rows)} row(s) selected")
                if st.button("🗑️ Delete Selected"):
                    # Convert displayed index → actual list index
                    actual_indexes = [i for i in selected_rows]
                    confirm_delete_dialog(actual_indexes)

            if not row_selected:
                # --- Save button ---
                if st.button("Submit", icon="💾"):
                    skipped = db.save_transactions_to_db(st.session_state.transactions, created_by=self.username)
                    st.success(f"{len(st.session_state.transactions) - len(skipped)} transactions saved to DB!", icon="✅")
                    st.session_state.transactions.clear()

                    if skipped:
                        st.warning(f"{len(skipped)} transactions skipped due to duplicate descriptions:", icon="📢")
                        df = pd.DataFrame(skipped)
                        df.index = df.index + 1
                        st.dataframe(df)
                        st.stop()

                    sleep(1)
                    st.rerun()


    def show_all_unverified_transactions(self):
        df = db.get_unverified_transactions()
        if df.empty:
            st.info(f"Unverified transactions not found.", icon="ℹ️")
            st.stop()
        # Keep description internally for DB ops
        raw_df = df.copy()

        df.drop(columns=['id'], inplace=True)
        df = df.rename(columns=helper.camel_to_title)
        df.columns = [col.replace("_", " ") for col in df.columns]
        df.index = df.index + 1

        st.badge(f"Total Unverified Transactions: {len(df)}", color="orange")

        st.dataframe(
            df,
            key="view_unverified_trans",
            selection_mode="single-row",
            on_select="rerun",
            width='stretch'
        )

        selection = st.session_state.get("view_unverified_trans", {}).get("selection", {})
        selected_rows = selection.get("rows", [])

        if selected_rows:
            selected_index = selected_rows[0]

            # Fetch raw row (zero-based index)
            selected_row = raw_df.iloc[selected_index].to_dict()

            edit_delete_dialog(selected_row)


    def render_page(self):
        mode = st.radio("Select Mode",['Add', 'View'], horizontal=True, index=0)
        if mode == 'Add':
            self.show_input_ui()
        else:
            self.show_all_unverified_transactions()



if __name__ == "__main__":
    UnverifiedTransactions().render_page()