from datetime import date, timedelta
from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
from streamlit_autorefresh import st_autorefresh
from db import db
from utils import helper
from pages.BasePage import BasePage


@st.cache_data(ttl=600)
def _cached_kyc():
    rows = db.get_kyc()
    return pd.DataFrame(rows, columns=["Client Code", "Client Name", "Branch", "BOID"])


@st.cache_data(ttl=600)
def _cached_notable_clients():
    return db.get_notable_clients()


def _cached_notable_clients_with_turnover(from_date, to_date):
    return db.get_notable_clients_with_turnover(from_date, to_date)


class NotableClient(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"
        st.set_page_config("Notable Client", page_icon="⭐", layout="wide")
        st.header("⭐ Notable Clients", anchor=False)
        render_sidebar()

    def _add(self):
        kyc_df = _cached_kyc()
        code_to_name = dict(zip(kyc_df["Client Code"].astype(str), kyc_df["Client Name"].astype(str)))
        client_codes = kyc_df["Client Code"].astype(str).tolist()
        col1, col2 = st.columns(2)
        with col1:
            selected = st.selectbox("Client Code *", [""] + client_codes)
            client_type = st.selectbox("Client Type *", ["", "PEPS", "SPECIAL CLIENT"])
        with col2:
            auto_name = code_to_name.get(selected, "")
            client_name = st.text_input("Client Name *", value=auto_name, disabled=True).upper()
            reason = st.text_area("Reason *")
        if st.button("Add", icon="⭐"):
            if not selected:
                st.warning("Please select a client.", icon="⚠️")
                return
            if not client_type:
                st.warning("Please select a client type.", icon="⚠️")
                return
            if not reason.strip():
                pass
            db.insert_notable_client(
                client_code=selected.strip(),
                client_name=client_name.strip() or auto_name,
                reason=reason.strip(),
                noted_by=self.username,
                client_type=client_type,
            )
            _cached_kyc.clear()
            _cached_notable_clients.clear()
            st.success("Client added to notable list ✅")
            sleep(1)
            st.rerun()

    @st.dialog("Notable Client Details", width="large")
    def _detail_dialog(self, record):
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            col1.text_input("Branch", value=record.get("Branch", ""), disabled=True)
            col2.text_input("BOID", value=record.get("BOID", ""), disabled=True)
            col3.text_input("Noted By", value=record["Noted By"], disabled=True)
            col1.text_input("Noted At", value=record["Noted At"], disabled=True)
            if record.get("Updated By"):
                col2.text_input("Updated By", value=record["Updated By"], disabled=True)
                col3.text_input("Updated At", value=record["Updated At"], disabled=True)

        new_code = st.text_input("Client Code *", value=record["Client Code"]).upper()
        new_name = st.text_input("Client Name", value=record["Client Name"], disabled=True)
        new_client_type = st.selectbox("Client Type *", ["", "PEPS", "SPECIAL CLIENT"],
                                       index=["", "PEPS", "SPECIAL CLIENT"].index(record.get("Client Type", "") or ""))
        new_reason = st.text_area("Reason *", value=record["Reason"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update", type="primary", use_container_width=True):
                if not new_code.strip():
                    st.warning("Client Code is required.")
                    return
                if not new_client_type:
                    st.warning("Please select a client type.")
                    return
                if not new_reason.strip():
                    st.warning("Reason is required.")
                    return
                db.update_notable_client_by_id(record["ID"], reason=new_reason.strip(), updated_by=self.username, client_type=new_client_type)
                _cached_notable_clients.clear()
                st.success("Updated")
                sleep(0.5)
                st.rerun()
        with col2:
            if st.button("Delete", type="secondary", use_container_width=True):
                db.delete_notable_client(record["ID"])
                _cached_notable_clients.clear()
                st.success("Deleted")
                sleep(0.5)
                st.rerun()

    def _view_edit(self):
        st_autorefresh(interval=60_000, key="notable_client_refresh")
        yesterday = date.today() - timedelta(days=1)
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", value=yesterday)
        with col2:
            to_date = st.date_input("To Date", value=yesterday)
        if from_date > to_date:
            st.error("From Date cannot be later than To Date", icon="📢")
            st.stop()

        rows = _cached_notable_clients_with_turnover(from_date, to_date)
        if not rows:
            st.info("No notable clients found.", icon="ℹ️")
            return
        df = pd.DataFrame(
            [dict(r) for r in rows],
        )
        df.columns = [
            "ID", "Client Code", "Client Name", "Reason", "Noted By", "Noted At",
            "Updated At", "Updated By", "Client Type", "Branch", "BOID",
            "Buying Amount", "Selling Amount", "Total Amount"
        ]
        df["Noted At"] = pd.to_datetime(df["Noted At"]).dt.strftime("%Y-%m-%d %I:%M %p")
        if df["Updated At"].notna().any():
            df["Updated At"] = pd.to_datetime(df["Updated At"]).dt.strftime("%Y-%m-%d %I:%M %p")
        df["Buying Amount"] = pd.to_numeric(df["Buying Amount"], errors="coerce").fillna(0)
        df["Selling Amount"] = pd.to_numeric(df["Selling Amount"], errors="coerce").fillna(0)
        df["Total Amount"] = pd.to_numeric(df["Total Amount"], errors="coerce").fillna(0)
        display_df = df.drop(columns=["ID"])
        first_columns = [
            "Branch", "Client Code", "Client Name", "BOID",
            "Client Type", "Reason",
            "Buying Amount", "Selling Amount", "Total Amount"
        ]
        display_df = display_df[first_columns + [col for col in display_df.columns if col not in first_columns]]
        st.badge(f"Total: {len(df)}")
        selection = st.dataframe(
            display_df,
            use_container_width=True,
            key="notable_view",
            selection_mode="single-row",
            on_select="rerun",
            column_config={
                "Buying Amount": st.column_config.NumberColumn("Buying Amount", format="%.2f"),
                "Selling Amount": st.column_config.NumberColumn("Selling Amount", format="%.2f"),
                "Total Amount": st.column_config.NumberColumn("Total Amount", format="%.2f"),
            },
        )
        try:
            selected_rows = selection.selection.rows
        except (AttributeError, KeyError):
            selected_rows = []
        if selected_rows:
            idx = selected_rows[0]
            self._detail_dialog(df.iloc[idx])

    def render_page(self):
        mode = st.radio("Mode", ["Add", "View/Edit"], horizontal=True, index=0)
        with st.container(border=True):
            if mode == "Add":
                self._add()
            else:
                self._view_edit()


if __name__ == "__main__":
    NotableClient().render_page()
