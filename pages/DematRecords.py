
from datetime import date
from nepali_datetime import date as nepali_date
from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import helper
from decimal import Decimal, InvalidOperation





def get_renew_values():
    return {
        "ALL": 1700,
        "BO OPEN": 200,
        "LIFETIME BO": 1000,
        "LIFETIME MEROSHARE": 500
    }

class DematRecords:
    def __init__(self):
        # helper.eliminate_top_padding()
        st.session_state.active_menu = "kyc"
        st.set_page_config(page_title="Demat Records", page_icon="🧾", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        st.header("🧾 Demat Records", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        if 'bro_data' not in st.session_state:
            self.app_users = db.get_all_app_user()
            self.all_user_options = [
                f"{user['username']} - {user['full_name']}"
                for user in sorted(self.app_users, key=lambda u: u["username"].lower())
            ]


    def entry_ui(self):
        # ---------- Defaults ----------
        defaults = {
            "client_name": "",
            "boid": "",
            "tsl_number": "",
            "renew_type": [],
            "gateway": "",
            "rm_name": "N/A",
            "payment_amount": "",
            "eng_date": date.today(),
            "nep_date": helper.convert_ad_to_bs(date.today().strftime("%Y-%m-%d")),
            "remarks":"",
            "client_code":""
        }

        # ---------- Initialize session state ----------
        for key, value in defaults.items():
            st.session_state.setdefault(key, value)

        # ---------- Reset logic ----------
        if st.session_state.get("reset_form", False):
            for key in defaults:
                st.session_state[key] = defaults[key]
            st.session_state["reset_form"] = False

        container = st.container(border=True)
        with container:
            col1, col2 = st.columns(2)

            # ---------- Widgets ----------
            # ---------- Calculate Payment Amount ----------
            renew_values = get_renew_values()
            total_payment = sum(renew_values.get(rt, 0) for rt in st.session_state.renew_type)
            st.session_state.payment_amount = str(total_payment)

            # ---------- Convert eng_date to nep_date ----------
            st.session_state.nep_date = helper.convert_ad_to_bs(st.session_state.eng_date.strftime("%Y-%m-%d"))
            with col1:
                st.text_input("Client Name", key="client_name")
                st.text_input("TSL-Number", key="tsl_number")
                st.text_input("Payment Amount", key="payment_amount", disabled=True)
                st.selectbox("Gateway", helper.get_demat_gateways(), key="gateway")
                st.date_input("Created Date (A.D.)", key="eng_date", min_value=date(1920,1,1), max_value=date.today(), disabled=True)
                remarks = st.text_input("Remarks (Optional)", key="remarks")
                bo_to_bo= st.checkbox("Is BO-TO-BO")
            with col2:
                st.text_input("Client Code (TMS)", key="client_code")
                st.text_input("BOID", key="boid")
                st.multiselect(
                    "Renew Type",
                    get_renew_values(),
                    key="renew_type"
                )
                st.selectbox("BRO", ["N/A"] + self.all_user_options, key="rm_name")
                st.text_input("Created Date (B.S.)", key="nep_date", value=defaults['nep_date'], disabled=True)
                st.text_input("Open By", value=self.username, disabled=True)
                st.markdown("<br>", unsafe_allow_html=True)
                # st.write(bo_to_bo)
            # ---------- Submit ----------
            if st.button("ᯓ➤ Submit"):
                errors = []

                # Client Name
                if not st.session_state.client_name.strip():
                    errors.append("Client Name is required")
                # BOID
                boid_value = st.session_state.boid.strip()
                if not boid_value:
                    errors.append("BOID is required")
                elif not boid_value.isdigit():
                    errors.append("BOID must contain only numbers")
                elif len(boid_value) != 16:
                    errors.append("BOID must be exactly 16 digits")
                # elif not boid_value.startswith("13011400"):  # or "12011400" if that is correct
                #     errors.append("BOID must start with 13011400")

                # TSL Number
                if not st.session_state.tsl_number.strip():
                    errors.append("TSL Number is required")

                # Gateway
                if not st.session_state.gateway.strip():
                    errors.append("Gateway is required")

                # BRO
                if st.session_state.rm_name == "N/A":
                    errors.append("Please select a valid BRO")

                # Payment Amount
                try:
                    payment_amount_decimal = Decimal(st.session_state.payment_amount)
                    if payment_amount_decimal <= 0:
                        errors.append("Payment Amount must be greater than 0")
                except (InvalidOperation, TypeError):
                    errors.append("Payment Amount must be a valid number")

                if errors:
                    for err in errors:
                        st.error(err)
                    return

                # ---------- Insert to DB ----------
                record_id = db.insert_demat_record(
                    client_name=st.session_state.client_name.upper(),
                    boid=st.session_state.boid,
                    tsl_number=st.session_state.tsl_number,
                    payment_amount=payment_amount_decimal,
                    gateway=st.session_state.gateway,
                    renew_type=",".join(st.session_state.renew_type),
                    rm_name=st.session_state.rm_name.split("-")[0].strip(),
                    open_by=self.username,
                    created_at_bs=st.session_state.nep_date,
                    remarks=remarks,
                    bo_to_bo=bo_to_bo,
                    client_code= st.session_state.client_code

                )

                if record_id:
                    st.success(f"Record saved successfully.")
                    # st.success(f"Record saved successfully (ID: {record_id})")
                    sleep(1)
                    # ---------- Reset form safely ----------
                    st.session_state["reset_form"] = True
                    st.rerun()
                else:
                    st.warning("BOID already exists.", icon="⚠️")


    def view_records(self):
        df = db.fetch_demat_records_with_branch_df()
    
        # Kathmandu sees everything, others see only their branch
        if self.branch != "KATHMANDU":
            df = df[df["Branch"] == self.branch]
        


        # print(df.columns)
        # Filter
        branches = ["All"] + df["Branch"].dropna().unique().tolist()
        created_at = ["All"] + df["created_at_bs"].dropna().unique().tolist()
        col1, col2 = st.columns(2)
        with col1:
            filter_by_branch = st.selectbox("Filter by Branch", branches)
        with col2:
            filter_by_created_at = st.selectbox("Filter by Created Date", created_at)

        if filter_by_branch != "All":
            df = df[df["Branch"] == filter_by_branch]

        df.drop(columns=['id', 'created_at', 'updated_at', 'updated_by'], inplace=True, errors="ignore")
        df = df.rename(columns=helper.camel_to_title)
        df.index = df.index + 1

        st.badge(f"Total: {len(df)}", color='green')

        # ---------- Dataframe with selection ----------
        st.dataframe(
            df,
            selection_mode='single-row',
            width='stretch',
            key='demat_record',
            on_select='rerun'
        )

        # Get the selected row index from session_state
        # selected_indices = st.session_state.get("demat_record", {}).get("selected_rows", [])

        selection = st.session_state.get("demat_record", {}).get("selection", {})
        selected_rows = selection.get("rows", [])

        if selected_rows:
            selected_index = selected_rows[0]

            # Fetch raw row (zero-based index)
            selected_row = df.iloc[selected_index].to_dict()

            self.edit_record_dialog(selected_row)



    @st.dialog("Edit / Delete Demat Records", width='medium')
    def edit_record_dialog(self, selected_row):
        """
        Opens a dialog to edit a selected demat record.
        `selected_row` should be a dict or pandas row.
        """
        if selected_row is None:
            st.info("Select a row to edit first.")
            return

        # record_id = selected_row["Id"]

        # ---------- Open Dialog ----------
        col1, col2 = st.columns(2)

        with col1:
            client_name = st.text_input("Client Name", value=selected_row["Client Name"])
            tsl_number = st.text_input("TSL Number", value=selected_row["Tsl Number"])
            selected_gateway = selected_row["Gateway"]
            options = helper.get_demat_gateways()
            gateway = st.selectbox("Gateway",options,index=options.index(selected_gateway))
            bro_options = ["N/A"] + self.all_user_options
            rm_value = selected_row.get("Rm Name", "N/A").strip()
            username_to_option = {user["username"]: f"{user['username']} - {user['full_name']}"for user in self.app_users}
            rm_value_mapped = username_to_option.get(rm_value, "N/A")
            bro_options_clean = [opt.strip() for opt in bro_options]
            rm_index = (bro_options_clean.index(rm_value_mapped) if rm_value_mapped in bro_options_clean else 0)
            rm_name = st.selectbox("BRO",bro_options,index=rm_index)
            st.text_input("Open By", value=selected_row["Open By"], disabled=True)
        with col2:
            client_code = st.text_input("Client Code", value=selected_row["Client Code"])
            boid = st.text_input("BOID", value=selected_row["Boid"], disabled=True)
            renew_type_list = selected_row['Renew Type'].split(",")  # → ["BO OPEN", "LIFETIME MEROSHARE"]
            renew_type = st.multiselect(
                "Renew Type",
                options=list(get_renew_values().keys()),
                default=renew_type_list
            )


            # Calculate payment amount based on selected renew types
            renew_values = get_renew_values()
            total_payment = sum(renew_values[rt] for rt in renew_type)

            payment_amount = st.text_input(
                "Payment Amount",
                value=str(total_payment),  # must be string
                disabled=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            is_bo_to_bo_val = selected_row['Is Bo To Bo']
            bo_to_bo = st.checkbox("Is BO-To-BO", value=is_bo_to_bo_val)

        col1, spcr, col2 = st.columns([1,4.1,1])
        with col1:
            update_btn = st.button("Update", icon="🔄")
        with col2:
            delete_btn = st.button("Delete", icon="🗑️")

        if update_btn:
            errors = []

            # ---------- Validation ----------
            if not client_name.strip():
                errors.append("Client Name is required")

            if not boid.strip():
                errors.append("BOID is required")
            elif not boid.isdigit() or len(boid) != 16:
                errors.append("BOID must be exactly 16 digits and numeric")

            if not tsl_number.strip():
                errors.append("TSL Number is required")

            try:
                payment_amount_decimal = Decimal(payment_amount)
                if payment_amount_decimal <= 0:
                    errors.append("Payment Amount must be greater than 0")
            except:
                errors.append("Payment Amount must be a valid number")

            if not gateway.strip():
                errors.append("Gateway is required")

            if rm_name == "N/A":
                errors.append("Please select a valid BRO")

            if errors:
                for err in errors:
                    st.error(err)
                return

            # ---------- Call DB Update ----------
            success = db.update_demat_record(
                # record_id,
                client_name=client_name,
                boid=boid,
                tsl_number=tsl_number,
                payment_amount=payment_amount_decimal,
                gateway=gateway,
                renew_type=",".join(renew_type),
                # renew_type=str(renew_type),
                rm_name=rm_name.split("-")[0].strip(),
                updated_by=self.username,
                bo_to_bo=bo_to_bo,
                client_code=client_code
            )

            if success:
                st.success("Record updated successfully!")
                sleep(1)
                st.rerun()
            else:
                st.error(f"Something went wrong. Please contact IT.")
                st.stop()

        if delete_btn:
            status = db.delete_demat_records(boid=boid)
            if status:
                st.success(f"Record with boid '{boid}' deleted successfully.")
                sleep(1)
                st.rerun()
            else:
                st.error(f"Something went wrong. Please contact IT.")
    
    def render_page(self):
        mode = st.radio("Mode", ['Entry', 'View/Edit'], horizontal=True)
        if mode == "Entry":
            self.entry_ui()
        else:
            self.view_records()

if __name__ == "__main__":
    DematRecords().render_page()