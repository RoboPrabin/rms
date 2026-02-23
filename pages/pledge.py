from db import db
from time import sleep
import streamlit as st
import pandas as pd
import sqlalchemy
import io
from utils import auth_utils, page_url
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
import psycopg2
from datetime import date, datetime
import nepali_datetime


# ==============================
# Pledge App Initialization
# ==============================
class Pledge:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = ""
        st.set_page_config(page_title="Pledge", page_icon="🛅", layout="wide")
        user = auth_utils.ensure_logged_in()
        self.username = user['username']
        self.role = user['role']
        self.branch = user['branch']
        activate_client_code_hotkey()
        navigation.render_sidebar()
        st.header("🛅 Pledge Management", anchor=False)


# ==============================
# Database Connection
# ==============================
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port="5432",
        database="project",
        user="postgres",
        password="admin"
    )


INSERT_SQL = """
INSERT INTO pledge_data (
    "Date",
    "Registration No",
    "Pledgor BO ID (client)",
    "Pledgor BO ID NAME",
    "Pledgee BO ID(Bank)",
    "Pledgee BO ID NAME",
    "BRANCH",
    "No of Script",
    "RELEASE SEQUENCE",
    "set up",
    "Acceptance",
    "Total Amount",
    "REMARKS"
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""


# ==============================
# Manual Add Section
# ==============================
def render_add_section():
    st.subheader("Pledge Entry Form", anchor=False)

    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            entry_date = st.date_input("Date: BS", value=date.today())
            nepali_date_obj = nepali_datetime.date.from_datetime_date(
                entry_date.date() if isinstance(entry_date, datetime) else entry_date
            )

            # Text fields → empty if blank
            reg_no = st.text_input("Registration No.") or ""
            pledgor_bo_id = st.text_input("Pledgor BO ID (Client)") or ""
            pledgor_name = st.text_input("Pledgor BO ID Name") or ""
            pledgee_bo_id = st.text_input("Pledgee BO ID (Bank)") or ""
            pledgee_name = st.text_input("Pledgee BO ID Name") or ""
            remarks = st.text_area("Remarks") or ""

        with col2:
            nepali_date_str = nepali_date_obj.strftime("%Y-%m-%d")
            date_bs = st.date_input("Date: AD (Auto Converted)", value=nepali_date_str, disabled=True)
            branch = st.text_input("Branch") or ""

            # Numeric fields → empty string if zero
            no_of_script = st.number_input("No of Script", min_value=0, step=1)
            no_of_script = str(no_of_script) if no_of_script != 0 else ""

            release_sequence = st.text_input("Release Sequence", value="N/A") or ""
            setup = st.text_input("Set up", value="N/A") or ""

            acceptance = st.number_input("Acceptance", min_value=0, step=1)
            acceptance = str(acceptance) if acceptance != 0 else ""

            total_amount = st.number_input("Total Amount", min_value=0.0, format="%.2f")
            total_amount = str(total_amount) if total_amount != 0.0 else ""

    if st.button("Submit"):
        insert_data((
            date_bs,
            reg_no,
            pledgor_bo_id,
            pledgor_name,
            pledgee_bo_id,
            pledgee_name,
            branch,
            no_of_script,
            release_sequence,
            setup,
            acceptance,
            total_amount,
            remarks
        ))


# ==============================
# Excel Upload Section
# ==============================
def render_upload_section():
    st.subheader("Upload Pledge Excel File")

    uploaded_file = st.file_uploader("Choose Excel file", type=["xlsx", "xls"])
    if not uploaded_file:
        return

    df = pd.read_excel(uploaded_file)

    if df.empty:
        st.warning("Excel file is empty.")
        return

    if "S.N" in df.columns:
        df = df.drop(columns=["S.N"])

    st.dataframe(df, hide_index=True)

    if st.button("Upload to Database", icon="📤"):
        try:
            df = map_excel_columns(df)
            
            if df is None or df.empty:
                st.warning("No valid data to upload after mapping.")
                return

            data = list(df.itertuples(index=False, name=None))

            with get_connection() as conn:
                conn.cursor().executemany(INSERT_SQL, data)
                conn.commit()

            st.success("Excel data uploaded successfully.")
            st.balloons()

        except Exception as e:
            st.error(f"Upload failed: {e}")



def map_excel_columns(df):
    # Rename to match DB columns
    df = df.rename(columns={
        "Date": "Date",
        "Registration No.": "Registration No",
        "Pledgor BO ID (client)": "Pledgor BO ID (client)",
        "Pledgor BO ID NAME.": "Pledgor BO ID NAME",
        "Pledgee BO ID(bank)": "Pledgee BO ID(Bank)",
        "Pledgee BO ID NAME": "Pledgee BO ID NAME",
        "BRANCH": "BRANCH",
        "No of Script": "No of Script",
        "RELEASE SEQUENCE": "RELEASE SEQUENCE",
        "set up": "set up",
        "Acceptance": "Acceptance",
        "Total Amount": "Total Amount",
        "REMARKS": "REMARKS",
    })

    # Reorder columns
    df = df[
        [
            "Date",
            "Registration No",
            "Pledgor BO ID (client)",
            "Pledgor BO ID NAME",
            "Pledgee BO ID(Bank)",
            "Pledgee BO ID NAME",
            "BRANCH",
            "No of Script",
            "RELEASE SEQUENCE",
            "set up",
            "Acceptance",
            "Total Amount",
            "REMARKS",
        ]
    ]
    return df



# ==============================
# View Table Section
# ==============================
def render_view_section():
    st.subheader("Pledge Data")

    try:
        # Fetch data from DB
        with get_connection() as conn:
            df = pd.read_sql('SELECT * FROM pledge_data ORDER BY "id" DESC', conn)

        if df.empty:
            st.info("No pledge records found.")
            return

        # Search box
        search_query = st.text_input(
            "🔍 Search",
            placeholder="Search reg no, name, branch, remarks..."
        ).strip().lower()

        df_display = df

        if search_query:
            df_lower = df_display.astype(str).apply(lambda x: x.str.lower())
            mask = df_lower.apply(
                lambda row: row.str.contains(search_query).any(), axis=1
            )
            df_display = df_display[mask]

        # --- TABLE ---
        event = st.dataframe(
            df_display.drop(columns=["id"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="pledge_table"
        )

        # Detect selected row
        selected_rows = event.selection.rows if event else []

        if selected_rows:
            selected_row = df_display.iloc[selected_rows[0]]
            selected_id = selected_row["id"]

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✏️ Edit Record"):
                    open_edit_dialog(selected_row)

            with col2:
                if st.button("🗑️ Delete Record"):
                    open_delete_dialog(selected_id)

    except Exception as e:
        st.error(f"Error loading data: {e}")


# ------------------ EDIT DIALOG ------------------

@st.dialog("✏️ Edit Pledge Record",width="medium")
def open_edit_dialog(row):

    st.caption(f"Editing Record ID: {row['id']}")

    editable_cols = [c for c in row.index if c != "id"]

    with st.form("edit_form"):

        updated_data = {}

        # Split fields into 2-column grid
        cols = st.columns(2)

        for i, col in enumerate(editable_cols):
            with cols[i % 2]:
                updated_data[col] = st.text_input(
                    label=col.replace("_", " ").title(),
                    value=str(row[col]) if pd.notna(row[col]) else "",
                )

        st.divider()

        col1, col2 = st.columns([1, 1])

        save = col1.form_submit_button(
            "💾 Save Changes",
            use_container_width=True,
            type="primary",
        )

        cancel = col2.form_submit_button(
            "❌ Cancel",
            use_container_width=True,
        )

        if cancel:
            st.rerun()

        if save:
            try:
                set_clause = ", ".join([f'"{c}" = %s' for c in updated_data])
                values = list(updated_data.values()) + [row["id"]]

                query = f"""
                    UPDATE pledge_data
                    SET {set_clause}
                    WHERE id = %s
                """

                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(query, values)
                        conn.commit()

                st.success("✅ Record updated successfully!")
                st.rerun()

            except Exception as e:
                st.error(f"Update failed: {e}")



# ------------------ DELETE DIALOG ------------------

# ------------------ DELETE DIALOG ------------------

@st.dialog("🗑️ Delete Record")
def open_delete_dialog(record_id):

    st.warning("⚠️ This action cannot be undone.")
    st.write(f"Are you sure you want to delete record ID **{record_id}**?")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        confirm = st.button(
            "🗑️ Yes, Delete",
            use_container_width=True,
            type="primary",
        )

    with col2:
        cancel = st.button(
            "Cancel",
            use_container_width=True,
        )

    if cancel:
        st.rerun()

    if confirm:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM pledge_data WHERE id = %s",
                        (record_id,),
                    )
                    conn.commit()

            st.success("✅ Record deleted successfully!")
            st.rerun()

        except Exception as e:
            st.error(f"Delete failed: {e}")




# ==============================
# Database Insert Helper
# ==============================
def insert_data(data_tuple):
    try:
        with get_connection() as conn:
            conn.cursor().execute(INSERT_SQL, data_tuple)
            conn.commit()

        st.success("Record inserted successfully.")
        st.balloons()

    except Exception as e:
        st.error(f"Insert failed: {e}")


# ==============================
# Main Controller
# ==============================
def main():
    Pledge()

    option = st.radio(
        "Choose an option:",
        ["Add", "Upload file", "View table"],
        horizontal=True
    )

    if option == "Add":
        render_add_section()
    elif option == "Upload file":
        render_upload_section()
    elif option == "View table":
        render_view_section()


# ==============================
# Entry Point
# ==============================
if __name__ == "__main__":
    main()
