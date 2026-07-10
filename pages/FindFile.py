from time import sleep
from io import BytesIO
import pandas as pd
import streamlit as st
import streamlit_bridge.navigation as navigation
from db import db
from utils import helper
from pages.BasePage import BasePage


class FindFile(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "kyc"
        st.set_page_config("Find File", layout='wide')
        navigation.render_sidebar()
        st.header("Find File", anchor=False)

    def show_search(self):
        st.markdown("### Search Records")
        df = db.get_all_find_file()
        if df.empty:
            st.info("No records found.")
            return

        search = st.text_input("Search by client code").strip()
        if search:
            matches = df[df["clientcode"].str.contains(search, case=False, na=False)]
            if matches.empty:
                st.warning("No matching records found.")
                return
            for _, row in matches.iterrows():
                st.success(f"Client code: {row['clientcode']}, Client name: {row['clientname']}, Filename: {row['filename']}")

    def show_view_edit(self):
        st.markdown("### View / Edit Records")
        df = db.get_all_find_file()
        if df.empty:
            st.info("No records available.")
            return

        col1, col2 = st.columns([1, 2])
        with col1:
            filter_by = st.selectbox("Filter by", ["", "clientcode", "filename"], index=0)
        with col2:
            search_val = ""
            if filter_by == "clientcode":
                search_val = st.text_input("Enter client code").strip()
            elif filter_by == "filename":
                options = sorted(df["filename"].dropna().unique())
                search_val = st.selectbox("Select filename", [""] + list(options))

        mask = pd.Series([True] * len(df))
        if search_val:
            mask = df[filter_by] == search_val
        df_filtered = df[mask]

        df_display = df_filtered.drop(columns=["id"])
        selected = st.dataframe(
            df_display,
            use_container_width=True,
            selection_mode="single-row",
            hide_index=True,
            on_select="rerun"
        )

        rows = selected.get("selection", {}).get("rows", [])
        if not rows:
            return

        selected_row = df_filtered.iloc[rows[0]]
        self.edit_dialog(selected_row)

    @st.dialog("Edit Record")
    def edit_dialog(self, row):
        with st.form("edit_find_file_form"):
            clientname = st.text_input("Client Name", value=row["clientname"])
            clientcode = st.text_input("Client Code", value=row["clientcode"])
            filename = st.text_input("Filename", value=row["filename"])

            if st.form_submit_button("Update"):
                if not all([clientname, clientcode, filename]):
                    st.error("All fields are required.")
                else:
                    ok = db.update_find_file(row["id"], clientname, clientcode, filename)
                    if ok:
                        st.success("Record updated successfully!")
                        sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed to update record.")

        st.markdown("---")
        st.subheader("Delete Record")
        if st.checkbox("I confirm deletion"):
            if st.button("Delete", type="primary"):
                ok = db.delete_find_file(row["id"])
                if ok:
                    st.success("Record deleted successfully!")
                    sleep(0.5)
                    st.rerun()
                else:
                    st.error("Failed to delete record.")

    def show_upload(self):
        st.markdown("### Upload File")
        st.markdown("Upload an Excel file with columns: **clientname**, **clientcode**, **filename**.")

        sample_df = pd.DataFrame({
            "clientname": ["John Doe", "Jane Smith"],
            "clientcode": ["C001", "C002"],
            "filename": ["doc1.pdf", "doc2.pdf"],
        })
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            sample_df.to_excel(writer, index=False, sheet_name="FindFile")
        st.download_button(
            label="Download Sample Excel",
            data=buffer.getvalue(),
            file_name="find_file_sample.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        uploaded_file = st.file_uploader("Upload your filled Excel file", type=["xlsx", "xls", "csv"])
        if uploaded_file is None:
            return

        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        expected = {"clientname", "clientcode", "filename"}
        if not expected.issubset(set(df.columns.str.lower())):
            st.error(f"Invalid columns. Expected: {expected}, Got: {set(df.columns)}")
            return

        df.columns = df.columns.str.lower()
        if df.isnull().any().any():
            st.error("File contains empty values.")
            return

        st.success("File validated successfully")
        st.badge(f"Total rows to insert: {len(df)}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("Insert Records"):
            with st.spinner("Processing..."):
                inserted = db.insert_find_file(df, self.username)
            st.success(f"Inserted {inserted} records successfully!")
            sleep(1)
            st.rerun()

    def render_page(self):
        tab = st.radio(
            "Select mode",
            ["Search", "View / Edit", "Upload File"],
            horizontal=True
        )
        st.markdown("---")
        if tab == "Search":
            self.show_search()
        elif tab == "View / Edit":
            self.show_view_edit()
        else:
            self.show_upload()


if __name__ == "__main__":
    FindFile().render_page()