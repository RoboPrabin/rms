from time import sleep
from utils import helper
from io import BytesIO
from config import config
from db import db
import streamlit_bridge.app_state as app_state
import pandas as pd
import streamlit as st
import uuid
from sqlalchemy import create_engine, text
from utils import helper 
from streamlit_bridge.navigation import render_sidebar
from utils.custom_hotkey import activate_client_code_hotkey
import psycopg2
from datetime import datetime, timedelta
import pandas as pd


class BookClosure:
    def __init__(self):
        st.set_page_config("Book Closure", page_icon="📫", layout='wide')
        activate_client_code_hotkey()
        st.header("📫 Book Closure", anchor=False)

        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        render_sidebar()
        helper.adjust_ui()

    def next_working_day(self, date_value, holidays):
        date_value = date_value 
        while date_value in holidays:
            date_value += pd.Timedelta(days=1)
        return date_value
    

    def show_entry_form(self):
        holidays = db.get_holidays()

        # ✅ Toggle must be OUTSIDE the form
        need_edit = st.toggle("Edit T Dates")

        with st.form("Create Book Closure", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                script = st.text_input("Script", icon="📜").upper()
            with col2:
                start_date = st.date_input(label="Start Date")
            with col3:
                end_date = st.date_input(label="End Date")

            # ✅ Auto-calc T0, T1, T2
            if end_date:
                t0 = self.next_working_day(end_date + pd.Timedelta(days=1), holidays)
                t1 = self.next_working_day(t0 + pd.Timedelta(days=1), holidays)
                t2 = self.next_working_day(t1 + pd.Timedelta(days=1), holidays)
            else:
                t0 = t1 = t2 = None

            st.markdown("---")

            col4, col5, col6 = st.columns(3)
            with col4:
                trade_date_zero = st.date_input(
                    "T0 (Trade Date)",
                    value=t0,
                    disabled=not need_edit
                )
            with col5:
                trade_date_one = st.date_input(
                    "T1 (EDIS Date)",
                    value=t1,
                    disabled=not need_edit
                )
            with col6:
                trade_date_two = st.date_input(
                    "T2 (Settlement Date)",
                    value=t2,
                    disabled=not need_edit
                )

            submitted = st.form_submit_button("Submit")

            if submitted:
                fields = [
                    script,
                    start_date,
                    end_date,
                    trade_date_zero,
                    trade_date_one,
                    trade_date_two
                ]

                if not all(fields):
                    st.error("All fields are required.", icon="🚨")
                    st.stop()
                db.insert_book_closure(script=script, start_date=start_date, end_date=end_date, 
                                       t0=trade_date_zero, t1=trade_date_one, t2=trade_date_two, 
                                       created_by=self.username,
                                       updated_by=self.username)
                st.success("✅ Book Closure saved successfully!")


    def show_all_book_closure(self):
        df = db.get_all_book_closure()
        df.drop(columns=['id', 'created_at', 'updated_at'], inplace=True)
        df = helper.format_dataframe(df=df)
        df.rename(columns={"Start_Date": "Start Date", "End_Date":"End Date", "Created_By": "Created By", "Updated_By": "Updated By"}, inplace=True)
        df.index = df.index + 1
        if df.empty:
            st.info("No book closure records found.")
        else:
            search_term = st.text_input("Search Script").upper()
            if search_term:
                df = df[df['Script'].str.contains(search_term, na=False)]
                if df.empty:
                    st.warning(f"No records found for script containing '{search_term}'.")
                    return
            st.dataframe(df, use_container_width=True)
            if self.role in ["USER", "ADMIN"]:
                self.show_edit_function()


    def show_edit_function(self):
        st.divider()
        st.markdown("### ✏️ Edit Book Closure")

        df = db.get_all_book_closure()

        if df.empty:
            st.info("No records available to edit.")
            return

        # Keep original df for lookup
        df_original = df.copy()

        # Display only readable columns
        df_display = df_original.drop(columns=['id', 'created_at', 'updated_at'])
        df_display.index = df_display.index + 1

        # Select row to edit
        row_labels = [
            f"{row.script}"
            for _, row in df_display.iterrows()
        ]

        selected_label = st.selectbox("Select a record to edit", row_labels)

        if not selected_label:
            return

        # Identify selected row
        selected_index = row_labels.index(selected_label)
        selected_row = df_original.iloc[selected_index]

        st.markdown("---")
        st.subheader("Edit Selected Book Closure")

        with st.form("edit_book_closure_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                script = st.text_input("Script", value=selected_row["script"])
            with col2:
                start_date = st.date_input("Start Date", value=selected_row["start_date"])
            with col3:
                end_date = st.date_input("End Date", value=selected_row["end_date"])

            col4, col5, col6 = st.columns(3)
            with col4:
                t0 = st.date_input("T0 (Trade Date)", value=selected_row["t0"])
            with col5:
                t1 = st.date_input("T1 (EDIS Date)", value=selected_row["t1"])
            with col6:
                t2 = st.date_input("T2 (Settlement Date)", value=selected_row["t2"])

            update_btn = st.form_submit_button("Update")

            if update_btn:
                if not all([script, start_date, end_date, t0, t1, t2]):
                    st.error("All fields are required.", icon="🚨")
                    st.stop()

                success = db.update_book_closure(
                    id=selected_row["id"],
                    script=script,
                    start_date=start_date,
                    end_date=end_date,
                    t0=t0,
                    t1=t1,
                    t2=t2,
                    updated_by=self.username
                )

                if success:
                    st.success("✅ Book Closure updated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to update record.")
        
            # ✅ DELETE BUTTON (outside form)
        st.subheader("🗑️ Delete This Book Closure", anchor=False)

        delete_confirm = st.checkbox("I understand this action cannot be undone")

        if st.button("Delete", type="primary", disabled=not delete_confirm):
            success = db.delete_book_closure(selected_row["id"])

            if success:
                st.success("✅ Book Closure deleted successfully!")
                sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to delete record.")


    def show_holidays(self):
        st.subheader("🥳 Holidays", anchor=False)

        df = db.get_all_holidays()

        if df.empty:
            st.info("No holidays found.")
            return

        df.drop(columns=['id'], inplace=True)

        # ✅ Force entire column to datetime (fixes mixed types)
        df["holiday_date"] = pd.to_datetime(df["holiday_date"], errors="coerce")

        # ✅ Extract year safely
        df["Year"] = df["holiday_date"].dt.year

        # ✅ Convert to date for display
        df["holiday_date"] = df["holiday_date"].dt.date

        # ✅ Rename AFTER conversion
        df = df.rename(columns={
            "holiday_date": "Holiday Date",
            "holiday_description": "Holiday Description"
        })

        # Build dropdown
        years = sorted(df["Year"].unique().tolist())
        year_options = ["All"] + [str(y) for y in years]

        selected_year = st.selectbox("Filter by Year", year_options, index=0)

        if selected_year != "All":
            df = df[df["Year"] == int(selected_year)]

        df = df.drop(columns=["Year", "created_by", "created_at"])
        df.reset_index(inplace=True, drop=True)
        df.index = df.index + 1
        st.badge(f"Total holidays on year {selected_year} : {len(df)}", color='yellow')
        st.dataframe(df, use_container_width=True)

    def add_new_holiday(self):
        st.subheader("➕ Add New Holiday", anchor=False)

        with st.form("add_holiday_form"):
            col1, col2 = st.columns(2)

            with col1:
                holiday_date = st.date_input("Holiday Date")

            with col2:
                holiday_description = st.text_input("Holiday Description")

            submitted = st.form_submit_button("Add Holiday")

            if submitted:
                # ✅ Validation
                if not holiday_date or not holiday_description.strip():
                    st.error("All fields are required.", icon="🚨")
                    st.stop()

                # ✅ Duplicate check
                if db.holiday_exists(holiday_date):
                    st.error("Holiday already exists for this date.", icon="⚠️")
                    st.stop()

                # ✅ Insert into DB
                success = db.insert_holiday(
                    holiday_date=holiday_date,
                    holiday_description=holiday_description.strip(),
                    created_by=self.username
                )

                if success:
                    st.success("✅ Holiday added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add holiday.")


    @st.dialog("Master Password Required")
    def password_dialog(self):
        st.write("Enter master password to continue")

        pwd = st.text_input("Password", type="password")
        submit = st.button("Submit")

        if submit:
            if pwd == config.MASTER_PASSWORD:
                st.session_state["holiday_auth"] = True
                st.rerun()
            else:
                st.error("Incorrect password")

    def show_upload_ui(self):
        st.subheader("Upload Book Closure Script", anchor=False)

        # -----------------------------------------
        # Session state flags
        # -----------------------------------------
        if "book_upload_done" not in st.session_state:
            st.session_state.book_upload_done = False

        if "book_upload_count" not in st.session_state:
            st.session_state.book_upload_count = 0

        # -----------------------------------------
        # After processing: show success and stop
        # -----------------------------------------
        if st.session_state.book_upload_done:
            st.success(f"✅ Successfully inserted {st.session_state.book_upload_count} rows into book_closure.")

            # Reset flags
            st.session_state.book_upload_done = False
            st.session_state.book_upload_count = 0

            st.stop()

        # -----------------------------------------
        # Sample file download
        # -----------------------------------------
        st.markdown("Upload an Excel file using the exact sample format.")

        sample_df = pd.DataFrame({
            "Script": ["SCRIPT-1", "SCRIPT-2"],
            "Start Date": ["19-Dec-2025", "22-Dec-2025"],
            "End Date": ["19-Dec-2025", "22-Dec-2025"],
            # "t0": ["2025-01-06", "2025-02-06"],
            # "t1": ["2025-01-07", "2025-02-07"],
            # "t2": ["2025-01-08", "2025-02-08"]
        })

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            sample_df.to_excel(writer, index=False, sheet_name="Sample")

        st.download_button(
            label="📥 Download Sample Excel",
            data=buffer.getvalue(),
            file_name="book_closure_sample.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # -----------------------------------------
        # File uploader
        # -----------------------------------------
        uploaded_file = st.file_uploader(
            "Upload your filled Excel file",
            type=["xlsx"]
        )

        if uploaded_file is None:
            return

        # -----------------------------------------
        # Read & validate file
        # -----------------------------------------
        df = pd.read_excel(uploaded_file)

        expected_cols = ["Script", "Start Date", "End Date"]

        if list(df.columns) != expected_cols:
            st.error(f"Invalid columns. Expected: {expected_cols}, Got: {list(df.columns)}")
            return

        if df.isnull().any().any():
            st.error("File contains empty values. Please fix and upload again.")
            return

        st.success("✅ File validated successfully")
        st.badge(f"Total rows to insert: {len(df)}")

        df.reset_index(inplace=True, drop=True)
        df.index = df.index + 1
        st.dataframe(df)

        # -----------------------------------------
        # Process button
        # -----------------------------------------
        if st.button("Insert Into Book Closure", icon="⬇️"):
            with st.spinner("Processing..."):
                df.rename(columns={"Start Date": "start_date", "End Date": "end_date", "Script": "script"}, inplace=True)
                # After renaming
                df['end_date'] = pd.to_datetime(df['end_date'], format='%d-%b-%Y')

                # Fetch holidays
                conn = db.get_connection()
                cur = conn.cursor()
                cur.execute("SELECT holiday_date FROM holidays")
                rows = cur.fetchall()
                holidays = {datetime.strptime(row[0], '%Y-%m-%d').date() for row in rows}
                cur.close()
                conn.close()

                def next_business_days(end_date, n, holidays):
                    date = end_date.date()
                    count = 0
                    while count < n:
                        date += timedelta(days=1)
                        if date.weekday() != 5 and date not in holidays:  # Nepal: Sun-Fri business days
                            count += 1
                    return date

                df['t0'] = df['end_date'].apply(lambda d: next_business_days(d, 1, holidays))
                df['t1'] = df['end_date'].apply(lambda d: next_business_days(d, 2, holidays))
                df['t2'] = df['end_date'].apply(lambda d: next_business_days(d, 3, holidays))

                # Convert all to datetime first for consistent formatting
                df['end_date'] = pd.to_datetime(df['end_date'])
                df['t0'] = pd.to_datetime(df['t0'])
                df['t1'] = pd.to_datetime(df['t1'])
                df['t2'] = pd.to_datetime(df['t2'])

                # Now apply strftime
                df['end_date'] = df['end_date'].dt.strftime('%d-%b-%Y')
                df['t0'] = df['t0'].dt.strftime('%d-%b-%Y')
                df['t1'] = df['t1'].dt.strftime('%d-%b-%Y')
                df['t2'] = df['t2'].dt.strftime('%d-%b-%Y')

                # st.dataframe(df)
                inserted = db.insert_book_closure_from_file(df, username=self.username)

            st.session_state.book_upload_done = True
            st.session_state.book_upload_count = inserted

            st.rerun()


    
    
    def render_page(self):
        if self.role in ["USER", "ADMIN"]:
            mode = st.radio("Mode", ['Add Book Closure', 'View/Edit Book Closure', 'Add/View Holidays'], horizontal=True, index=0)
        else:
            mode = st.radio("Mode", ['View Book Closure'], horizontal=True, index=0)

        st.markdown("---")
        if mode == "Add Book Closure":
            mode2 = st.radio("Select Data Entry Mode", ["Upload File", "Manual Entry"], horizontal=True)
            if mode2 == "Manual Entry":
                self.show_entry_form()
            else:
                self.show_upload_ui()
        elif mode == 'View/Edit Book Closure' or mode == 'View Book Closure':
            self.show_all_book_closure()
        else:
            add_new_holiday = st.toggle("Add New Holiday")
            if add_new_holiday:
                col1, spacer, col2 = st.columns([2,0.1,2])
                with col1:
                    self.add_new_holiday()
                with col2:
                    self.show_holidays()
            else:
                self.show_holidays()

if __name__ == "__main__":
    BookClosure().render_page()