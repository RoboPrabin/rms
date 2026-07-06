from datetime import date, datetime
from io import BytesIO
from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
from db import db
from sqlalchemy import create_engine
from utils import helper
from decimal import Decimal, InvalidOperation
from pages.BasePage import BasePage
import streamlit.components.v1 as components




@st.cache_data(ttl=300)
def fetch_demat_records_with_branch_df_cached():
    return db.fetch_demat_records_with_branch_df()

@st.cache_data(ttl=300)
def fetch_tms_records_with_branch_df_cached():
    return db.fetch_tms_records_with_branch_df()



def get_renew_values():
    return {
        "ALL": 1700,
        "BO OPEN": 200,
        "LIFETIME BO": 1000,
        "LIFETIME MEROSHARE": 500,
        "FREE":0
    }

class DematRecords(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin(margin_top="-4rem")
        st.session_state.active_menu = "kyc"
        st.set_page_config(page_title="TMS and Demat Records", page_icon="🧾", layout="wide")
       
        col1, col2 = st.columns(2)
        with col1:
            st.header("🧾 TMS and Demat Records", anchor=False)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("‎", icon="🧹", help="Clear Cache. This operation shows latest updated data."):
                st.cache_data.clear()
                st.rerun()

        render_sidebar()
        try:
            self.holding_engine = create_engine(helper.get_holding_engine())
        except Exception:
            self.holding_engine = None
        if 'bro_data' not in st.session_state:
            try:
                self.app_users = db.get_all_app_user() or []
            except Exception:
                self.app_users = []
            self.all_user_options = [
                f"{user['username']} - {user['full_name']}"
                for user in sorted(self.app_users, key=lambda u: u["username"].lower())
            ]
            self._username_to_option = {
                user["username"]: (user["username"] if user["username"] == "SELF"
                                else f"{user['username']} - {user['full_name']}")
                for user in [{"username": "SELF", "full_name": "SELF"}] + self.app_users
            }


    def entry_ui(self):
        defaults = {
            "client_name": "",
            "boid": "",
            "tsl_number": "",
            "renew_type": [],
            "gateway": "",
            "rm_name": "N/A",
            "payment_amount": "",
            "eng_date": date.today(),
            "remarks": "",
            "client_code": ""
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
            try:
                st.session_state.nep_date = helper.convert_ad_to_bs(
                    st.session_state.eng_date.strftime("%Y-%m-%d")
                ) or helper.convert_ad_to_bs(date.today().strftime("%Y-%m-%d"))
            except Exception:
                st.session_state.nep_date = helper.convert_ad_to_bs(date.today().strftime("%Y-%m-%d"))
            with col1:
                st.text_input("Client Name", key="client_name")
                st.text_input("TSL-Number", key="tsl_number")
                st.text_input("Payment Amount", key="payment_amount", disabled=True)
                st.selectbox("Gateway", helper.get_demat_gateways(), key="gateway")
                st.date_input("Created Date (A.D.)", key="eng_date", min_value=date(1920,1,1), max_value=date.today())
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
                st.selectbox("BRO", ["N/A", "SELF"] + self.all_user_options, key="rm_name")
                st.text_input("Created Date (B.S.)   -  (Auto-Generate)", key="nep_date")
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
                    if payment_amount_decimal < 0:
                        errors.append("Payment Amount must be 0 or greater than 0")
                except (InvalidOperation, TypeError):
                    errors.append("Payment Amount must be a valid number")

                if errors:
                    for err in errors:
                        st.error(err)
                    return

                # ---------- Insert to DB ----------
                try:
                    record_id = db.insert_demat_record(
                        client_name=st.session_state.client_name.upper(),
                        boid=st.session_state.boid,
                        tsl_number=st.session_state.tsl_number,
                        payment_amount=payment_amount_decimal,
                        gateway=st.session_state.gateway,
                        renew_type=",".join(st.session_state.renew_type),
                        rm_name=st.session_state.rm_name.split("-")[0].strip() if st.session_state.rm_name else "",
                        open_by=self.username,
                        created_at_bs=st.session_state.nep_date,
                        remarks=remarks,
                        bo_to_bo=bo_to_bo,
                        client_code=st.session_state.client_code
                    )
                except Exception as e:
                    st.error(f"Failed to save record: {e}")
                    return

                if record_id:
                    st.success("Record saved successfully.")
                    sleep(1)
                    st.session_state["reset_form"] = True
                    st.rerun()
                else:
                    st.warning("BOID already exists.", icon="⚠️")


    def tms_entry_ui(self):
        defaults = {
            "tms_client_code": "",
            "tms_client_name": "",
            "tms_boid": "",
            "tms_eng_date": date.today(),
            "tms_branch": self.branch or "KATHMANDU",
            "tms_account_type": "NEW",
        }

        for key, value in defaults.items():
            st.session_state.setdefault(key, value)

        if st.session_state.get("tms_reset_form", False):
            for key in defaults:
                st.session_state[key] = defaults[key]
            st.session_state["tms_reset_form"] = False

        try:
            tms_nep_date = helper.convert_ad_to_bs(
                st.session_state.tms_eng_date.strftime("%Y-%m-%d")
            ) or helper.convert_ad_to_bs(date.today().strftime("%Y-%m-%d"))
        except Exception:
            tms_nep_date = helper.convert_ad_to_bs(date.today().strftime("%Y-%m-%d"))

        tms_account_open_date = st.session_state.get("tms_account_open_date")
        if tms_account_open_date:
            try:
                tms_account_open_nep = helper.convert_ad_to_bs(
                    tms_account_open_date.strftime("%Y-%m-%d")
                ) or ""
            except Exception:
                tms_account_open_nep = ""
        else:
            tms_account_open_nep = ""

        container = st.container(border=True)
        with container:
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Client Code (TMS)", key="tms_client_code")
                st.text_input("Client Name", key="tms_client_name")
                st.date_input("Created Date (A.D.)", key="tms_eng_date", min_value=date(1920,1,1), max_value=date.today())
                st.selectbox("Branch", helper.get_work_locations(), key="tms_branch")
                st.selectbox("BRO", ["N/A", "SELF"] + self.all_user_options, key="tms_rm_name")
                
            with col2:
                st.text_input("BOID", key="tms_boid")
                st.text_input("Created Date (B.S.)", value=tms_nep_date, disabled=True)
                st.selectbox("Account Type", ["NEW", "Update"], key="tms_account_type")
                st.text_input("Open By", value=self.username, disabled=True, key="tms_open_by")
                st.date_input("Account Opening Date", value=None, key="tms_account_open_date", min_value=date(1920,1,1), max_value=date.today())

            if st.button("ᯓ➤ Submit", key="tms_submit"):
                errors = []

                tms_client_code_val = st.session_state.tms_client_code.strip()
                if not tms_client_code_val:
                    errors.append("Client Code is required")
                elif not tms_client_code_val.isdigit():
                    errors.append("Client Code must contain only numbers")
                tms_client_name_val = st.session_state.tms_client_name.strip()
                if not tms_client_name_val:
                    errors.append("Client Name is required")
                elif not tms_client_name_val.replace(" ", "").isalpha():
                    errors.append("Client Name must contain only alphabets")
                boid_value = st.session_state.tms_boid.strip()
                if not boid_value:
                    errors.append("BOID is required")
                elif not boid_value.isdigit():
                    errors.append("BOID must contain only numbers")
                elif len(boid_value) != 16:
                    errors.append("BOID must be exactly 16 digits")
                if not tms_nep_date:
                    errors.append("Created Date (B.S.) conversion failed")
                if st.session_state.tms_rm_name == "N/A":
                    errors.append("Please select a valid BRO")
                if not st.session_state.get("tms_branch"):
                    errors.append("Branch is required")
                if not st.session_state.get("tms_account_type"):
                    errors.append("Account Type is required")

                if errors:
                    for err in errors:
                        st.error(err)
                    return

                try:
                    tms_account_open_date_val = st.session_state.tms_account_open_date
                    account_opening_date_str = tms_account_open_date_val.strftime("%Y-%m-%d") if tms_account_open_date_val else ""

                    record_id = db.insert_tms_record(
                        client_code=st.session_state.tms_client_code,
                        client_name=st.session_state.tms_client_name.upper(),
                        boid=st.session_state.tms_boid,
                        created_at_bs=tms_nep_date,
                        opened_by=self.username,
                        rm_name=st.session_state.tms_rm_name.split("-")[0].strip() if st.session_state.tms_rm_name else "",
                        bro=st.session_state.tms_rm_name.split("-")[0].strip() if st.session_state.tms_rm_name else "",
                        account_opening_date=account_opening_date_str,
                        branch=self.branch,
                        account_type=st.session_state.tms_account_type
                    )
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                        st.warning("Client Code already exists.", icon="⚠️")
                    else:
                        st.error(f"Failed to save: {e}")
                    return

                if record_id:
                    st.success("Record saved successfully.")
                    sleep(1)
                    st.session_state["tms_reset_form"] = True
                    st.rerun()

    def view_records(self):
        df = fetch_demat_records_with_branch_df_cached()

        if self.branch != "KATHMANDU":
            df = df[df["Branch"] == self.branch]

        if df.empty:
            st.warning("Records not found.", icon="⚠️")
            st.stop()

        filtered_df = df.copy()

        filter_options = {
            "Branch": "Branch",
            "Open By": "open_by",
            "RM Name": "rm_name",
            "Gateway": "gateway",
            "Created At Bs": "created_at_bs"
        }

        col1, col2 = st.columns(2)

        with col1:
            selected_filter_label = st.selectbox(
                "Filter By",
                ["All"] + list(filter_options.keys()),
                index=0
            )

        if selected_filter_label != "All":
            selected_filter_column = filter_options[selected_filter_label]

            with col2:
                filter_values = (
                    filtered_df[selected_filter_column]
                    .replace({None: "None"})
                    .fillna("None")
                    .astype(str)
                    .sort_values()
                    .unique()
                    .tolist()
                )

                selected_filter_value = st.selectbox(
                    f"Select {selected_filter_label}",
                    ["All"] + filter_values,
                    index=0
                )

            if selected_filter_value != "All":
                if selected_filter_value == "None":
                    filtered_df = filtered_df[filtered_df[selected_filter_column].isna()]
                else:
                    filtered_df = filtered_df[
                        filtered_df[selected_filter_column].astype(str) == selected_filter_value
                    ]

        filtered_df = filtered_df.drop(
            columns=["id", "created_at", "updated_at", "updated_by"],
            errors="ignore"
        )

        filtered_df = filtered_df.rename(columns=helper.camel_to_title)
        filtered_df.index = filtered_df.index + 1

        st.badge(f"Total: {len(filtered_df):,}", color="green")

        st.dataframe(
            filtered_df,
            selection_mode="single-row",
            width="stretch",
            key="demat_record",
            on_select="rerun",
            hide_index=True
        )

        selection = st.session_state.get("demat_record", {}).get("selection", {})
        selected_rows = selection.get("rows", [])

        if selected_rows:
            try:
                selected_index = selected_rows[0]
                selected_row = filtered_df.loc[selected_index].to_dict()
                self.edit_record_dialog(selected_row)
            except (IndexError, KeyError) as e:
                st.error(f"Error selecting row: {e}")


    def view_tms_records(self):
        df = fetch_tms_records_with_branch_df_cached()

        if self.branch != "KATHMANDU":
            df = df[df["Branch"] == self.branch]

        if df.empty:
            st.warning("Records not found.", icon="⚠️")
            st.stop()

        filtered_df = df.copy()

        filter_options = {
            "Branch": "Branch",
            "Client Code": "client_code",
            "Opened By": "opened_by",
            "RM Name": "rm_name",
            "Created At Bs": "created_at_bs"
        }

        col1, col2 = st.columns(2)

        with col1:
            selected_filter_label = st.selectbox(
                "Filter By",
                ["All"] + list(filter_options.keys()),
                index=0,
                key="tms_filter"
            )

        if selected_filter_label != "All":
            selected_filter_column = filter_options[selected_filter_label]

            with col2:
                filter_values = (
                    filtered_df[selected_filter_column]
                    .replace({None: "None"})
                    .fillna("None")
                    .astype(str)
                    .sort_values()
                    .unique()
                    .tolist()
                )

                selected_filter_value = st.selectbox(
                    f"Select {selected_filter_label}",
                    ["All"] + filter_values,
                    index=0,
                    key="tms_filter_val"
                )

            if selected_filter_value != "All":
                if selected_filter_value == "None":
                    filtered_df = filtered_df[filtered_df[selected_filter_column].isna()]
                else:
                    filtered_df = filtered_df[
                        filtered_df[selected_filter_column].astype(str) == selected_filter_value
                    ]

        filtered_df = filtered_df.drop(columns=["bro", "id", "created_at", "updated_at", "updated_by"], errors="ignore")
        filtered_df = filtered_df.rename(columns=helper.camel_to_title)
        filtered_df.rename(columns={"Rm Name": "Bro"}, inplace=True)
        cols = filtered_df.columns.tolist()
        if "Created At Bs" in cols:
            cols.remove("Created At Bs")
            cols.insert(0, "Created At Bs")
        filtered_df = filtered_df[cols]
        filtered_df.index = filtered_df.index + 1

        st.badge(f"Total: {len(filtered_df):,}", color="green")

        st.dataframe(
            filtered_df,
            selection_mode="single-row",
            width="stretch",
            key="tms_record",
            on_select="rerun",
            hide_index=True
        )

        selection = st.session_state.get("tms_record", {}).get("selection", {})
        selected_rows = selection.get("rows", [])

        if selected_rows:
            try:
                selected_index = selected_rows[0]
                selected_row = filtered_df.loc[selected_index].to_dict()
                self.edit_tms_record_dialog(selected_row)
            except (IndexError, KeyError) as e:
                st.error(f"Error selecting row: {e}")


    def view_branch_summary(self):
        dp_df = db.fetch_demat_records_with_branch_df()
        tms_df = db.fetch_tms_records_with_branch_df()

        all_dates = set()
        if not dp_df.empty:
            all_dates.update(dp_df["created_at_bs"].dropna().unique())
        if not tms_df.empty:
            all_dates.update(tms_df["created_at_bs"].dropna().unique())

        today_bs = helper.convert_ad_to_bs(date.today().strftime("%Y-%m-%d"))
        sorted_dates = sorted(all_dates, reverse=True)
        date_options = ["All"] + sorted_dates
        default_idx = 0
        if today_bs in sorted_dates:
            default_idx = sorted_dates.index(today_bs) + 1

        selected_date = st.selectbox("Filter by Date (B.S.)", date_options, index=default_idx, key="summary_date_filter")

        if not dp_df.empty:
            dp_df = dp_df if selected_date == "All" else dp_df[dp_df["created_at_bs"] == selected_date]
        if not tms_df.empty:
            tms_df = tms_df if selected_date == "All" else tms_df[tms_df["created_at_bs"] == selected_date]

        all_branches = helper.get_work_locations()
        base = pd.DataFrame({"Branch": all_branches})

        dp_summary = dp_df[dp_df["boid"].astype(str).str.startswith("130114")].groupby("Branch").size().reset_index(name="DP Open") if not dp_df.empty else pd.DataFrame(columns=["Branch", "DP Open"])
        tms_summary = tms_df.groupby("Branch").size().reset_index(name="TMS Open") if not tms_df.empty else pd.DataFrame(columns=["Branch", "TMS Open"])

        summary = base.merge(dp_summary, on="Branch", how="left").merge(tms_summary, on="Branch", how="left")
        summary = summary.fillna(0)
        summary["DP Open"] = summary["DP Open"].astype(int)
        summary["TMS Open"] = summary["TMS Open"].astype(int)
        summary["Total Account Open"] = summary["DP Open"] + summary["TMS Open"]
        summary = summary.sort_values("Total Account Open", ascending=False).reset_index(drop=True)

        code_to_name = helper.get_branch_code_mapping()
        name_to_code = {v: k for k, v in code_to_name.items()}
        summary["Branch"] = summary["Branch"].map(name_to_code).fillna(summary["Branch"])

        total_row = pd.DataFrame([{
            "Branch": "TOTAL",
            "DP Open": summary["DP Open"].sum(),
            "TMS Open": summary["TMS Open"].sum(),
            "Total Account Open": summary["Total Account Open"].sum()
        }])
        summary = pd.concat([summary, total_row], ignore_index=True)

        st.badge(f"Total Branches: {len(summary) - 1:,}", color="green")
        summary.index += 1
        st.dataframe(summary, width="stretch", use_container_width=True)


    @st.dialog("Edit TMS Record", width='medium')
    def edit_tms_record_dialog(self, selected_row):
        if selected_row is None:
            st.info("Select a row to edit first.")
            return

        client_code = selected_row.get("Client Code", "")
        col1, col2 = st.columns(2)
        with col1:
            client_name = st.text_input("Client Name", value=selected_row.get("Client Name", ""))
            created_bs = st.text_input("Created Date (B.S.)", value=selected_row.get("Created At Bs", ""))
            branch_value = selected_row.get("Branch", "")
            branch_options = helper.get_work_locations()
            try:
                branch_idx = branch_options.index(branch_value)
            except ValueError:
                branch_idx = 0
            branch = st.selectbox("Branch", branch_options, index=branch_idx)
            rm_value = str(selected_row.get("Bro", "N/A")).strip()
            rm_value_mapped = self._username_to_option.get(rm_value, "N/A")
            bro_options = ["N/A", "SELF"] + self.all_user_options
            bro_options_clean = [opt.strip() for opt in bro_options]
            try:
                rm_index = bro_options_clean.index(rm_value_mapped)
            except ValueError:
                rm_index = 0
            rm_name = st.selectbox("Bro", bro_options, index=rm_index)
        with col2:
            boid = st.text_input("BOID", value=selected_row.get("Boid", ""), disabled=True)
            opened_by = st.text_input("Opened By", value=selected_row.get("Opened By", ""), key="tms_edit_opened")
            account_type_value = selected_row.get("Account Type", "NEW")
            account_type = st.selectbox("Account Type", ["NEW", "Update"], index=0 if account_type_value == "NEW" else 1)
            account_opening_date_str = selected_row.get("Account Opening Date", "")
            try:
                account_opening_date = datetime.strptime(account_opening_date_str, "%Y-%m-%d").date() if account_opening_date_str else None
            except (ValueError, TypeError):
                account_opening_date = None
            account_opening_date = st.date_input("Account Opening Date", value=account_opening_date, min_value=date(1920,1,1), max_value=date.today())
        col1, spcr, col2 = st.columns([1, 4.1, 1])
        with col1:
            update_btn = st.button("Update", icon="🔄")
        with col2:
            delete_btn = st.button("Delete", icon="🗑️")

        if update_btn:
            errors = []
            if not client_name.strip():
                errors.append("Client Name is required")
            if not boid or not boid.strip():
                errors.append("BOID is required")
            elif not boid.isdigit() or len(boid) != 16:
                errors.append("BOID must be exactly 16 digits and numeric")
            if not created_bs or not created_bs.strip():
                errors.append("Created Date (B.S.) is required")
            if rm_name == "N/A":
                errors.append("Please select a valid BRO")
            if not branch:
                errors.append("Branch is required")

            if errors:
                for err in errors:
                    st.error(err)
                return

            try:
                success = db.update_tms_record(
                    client_code=client_code,
                    client_name=client_name,
                    boid=boid,
                    created_at_bs=created_bs,
                    opened_by=opened_by,
                    rm_name=rm_name.split("-")[0].strip() if rm_name else "",
                    branch=branch,
                    account_type=account_type,
                    account_opening_date=account_opening_date.strftime("%Y-%m-%d") if account_opening_date else ""
                )
            except Exception as e:
                st.error(f"Failed to update: {e}")
                return

            if success:
                st.success("Record updated successfully!")
                st.cache_data.clear()
                sleep(1)
                st.rerun()
            else:
                st.error("Something went wrong. Please contact IT.")

        if delete_btn:
            conn = None
            try:
                conn = db.get_connection()
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM tms_record WHERE client_code = %s", (client_code,))
                    conn.commit()
                st.success(f"Record '{client_code}' deleted successfully.")
                st.cache_data.clear()
                sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")
            finally:
                if conn:
                    conn.close()


    @st.dialog("Edit / Delete TMS and Demat Records", width='medium')
    def edit_record_dialog(self, selected_row):
        if selected_row is None:
            st.info("Select a row to edit first.")
            return

        col1, col2 = st.columns(2)

        with col1:
            client_name = st.text_input("Client Name", value=selected_row.get("Client Name", ""))
            tsl_number = st.text_input("TSL Number", value=selected_row.get("Tsl Number", ""))
            selected_gateway = selected_row.get("Gateway", "")
            options = helper.get_demat_gateways()
            try:
                gw_index = options.index(selected_gateway)
            except ValueError:
                gw_index = 0
            gateway = st.selectbox("Gateway", options, index=gw_index)

            bro_options = ["N/A", "SELF"] + self.all_user_options
            rm_value = str(selected_row.get("Rm Name", "N/A")).strip()
            rm_value_mapped = self._username_to_option.get(rm_value, "N/A")
            bro_options_clean = [opt.strip() for opt in bro_options]
            try:
                rm_index = bro_options_clean.index(rm_value_mapped)
            except ValueError:
                rm_index = 0
            rm_name = st.selectbox("BRO", bro_options, index=rm_index)
            st.text_input("Open By", value=selected_row.get("Open By", ""), disabled=True)
        with col2:
            client_code = st.text_input("Client Code", value=selected_row.get("Client Code", ""))
            boid = st.text_input("BOID", value=selected_row.get("Boid", ""), disabled=True)
            renew_type_raw = selected_row.get("Renew Type", "")
            renew_type_list = str(renew_type_raw).split(",") if pd.notna(renew_type_raw) else []
            renew_type = st.multiselect(
                "Renew Type",
                options=list(get_renew_values().keys()),
                default=renew_type_list
            )

            renew_values = get_renew_values()
            total_payment = sum(renew_values[rt] for rt in renew_type)

            payment_amount = st.text_input(
                "Payment Amount",
                value=str(total_payment),
                disabled=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            is_bo_to_bo_val = selected_row.get("Is Bo To Bo", False)
            bo_to_bo = st.checkbox("Is BO-To-BO", value=is_bo_to_bo_val)

        col1, spcr, col2 = st.columns([1, 4.1, 1])
        with col1:
            update_btn = st.button("Update", icon="🔄")
        with col2:
            delete_btn = st.button("Delete", icon="🗑️")

        if update_btn:
            errors = []

            if not client_name.strip():
                errors.append("Client Name is required")

            if not boid or not boid.strip():
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

            try:
                success = db.update_demat_record(
                    client_name=client_name,
                    boid=boid,
                    tsl_number=tsl_number,
                    payment_amount=payment_amount_decimal,
                    gateway=gateway,
                    renew_type=",".join(renew_type),
                    rm_name=rm_name.split("-")[0].strip(),
                    updated_by=self.username,
                    bo_to_bo=bo_to_bo,
                    client_code=client_code
                )
            except Exception as e:
                st.error(f"Failed to update: {e}")
                return

            if success:
                st.success("Record updated successfully!")
                st.cache_data.clear()
                sleep(1)
                st.rerun()
            else:
                st.error("Something went wrong. Please contact IT.")

        if delete_btn:
            try:
                status = db.delete_demat_records(boid=boid)
            except Exception as e:
                st.error(f"Failed to delete: {e}")
                return
            if status:
                st.success(f"Record with boid '{boid}' deleted successfully.")
                st.cache_data.clear()
                sleep(1)
                st.rerun()
            else:
                st.error("Something went wrong. Please contact IT.")
    
    def render_page(self):
        mode = st.radio("Mode", ['Entry', 'View/Edit', 'File Upload', 'Bulk Update (Client Code)'], horizontal=True)

        if mode == "View/Edit":
            components.html(
                """
                <script>
                setTimeout(function() {
                    window.location.reload();
                }, 5000);
                </script>
                """,
                height=0,
            )
        if mode == "Entry":
            entry_tab = st.segmented_control("", ["DP Entry", "TMS Entry"], default="TMS Entry", key="entry_tab")
            if entry_tab == "DP Entry":
                self.entry_ui()
            else:
                self.tms_entry_ui()
        elif mode=='View/Edit':
            role = str(getattr(self, "role", "")).upper()
            can_view_report = role in ("ADMIN", "MANAGER")
            if can_view_report:
                view_tab1, view_tab2, view_tab3 = st.tabs(["DP Records", "TMS Records", "TMS and DP Report"])
                with view_tab1:
                    self.view_records()
                with view_tab2:
                    self.view_tms_records()
                with view_tab3:
                    self.view_branch_summary()
            else:
                view_tab1, view_tab2 = st.tabs(["DP Records", "TMS Records"])
                with view_tab1:
                    self.view_records()
                with view_tab2:
                    self.view_tms_records()
        elif mode == 'File Upload':
            self.file_upload()
        elif mode == 'Bulk Update (Client Code)':
            self.bulk_update_client_code()
    
    def bulk_update_client_code(self):
        st.caption("*Note: Make sure your file has BOID and CLIENT CODE columns.")

        uploaded_file = st.file_uploader(
            label="Upload file",
            type=["xlsx"],
            accept_multiple_files=False
        )

        if not uploaded_file:
            return

        try:
            df = pd.read_excel(uploaded_file, dtype=str)
        except Exception as e:
            st.error(f"Failed to read Excel file: {e}")
            return

        # Normalize column names to avoid silly user-side formatting drama
        df.columns = [str(col).strip().upper() for col in df.columns]

        required_columns = {"BOID", "CLIENT CODE"}
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            st.error(
                f"Required column(s) missing: {', '.join(sorted(missing_columns))}"
            )
            return

        working_df = df[["BOID", "CLIENT CODE"]].copy().fillna("")
        working_df = working_df.apply(lambda col: col.astype(str).str.strip())
        working_df = working_df.replace("nan", "")
        working_df["BOID"] = working_df["BOID"].str.replace(r"\.0$", "", regex=True)
        working_df["CLIENT CODE"] = working_df["CLIENT CODE"].str.replace(r"\.0$", "", regex=True)

        working_df = working_df[
            (working_df["BOID"] != "") | (working_df["CLIENT CODE"] != "")
        ].reset_index(drop=True)

        st.subheader("Review and edit uploaded data", anchor=False)
        st.badge(f"Total rows: {len(working_df):,.0f}", color='green')
        edited_df = st.data_editor(
            working_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="bulk_update_editor"
        )

        if st.button("Update Client Code", icon="🚀"):
            self._process_bulk_client_code_update(edited_df)

    def _process_bulk_client_code_update(self, edited_df: pd.DataFrame):
        if edited_df.empty:
            st.warning("No data available to update.")
            return

        # Clean edited data again before DB work
        df = edited_df.copy()
        df.columns = [str(col).strip().upper() for col in df.columns]
        df["BOID"] = df["BOID"].astype(str).str.strip()
        df["CLIENT CODE"] = df["CLIENT CODE"].astype(str).str.strip()

        # Remove completely blank rows
        df = df[
            (df["BOID"].ne("")) &
            (df["CLIENT CODE"].ne("")) &
            (~df["BOID"].str.lower().eq("nan")) &
            (~df["CLIENT CODE"].str.lower().eq("nan"))
        ].copy()

        if df.empty:
            st.warning("No valid rows found after cleaning the edited data.")
            return

        # Optional: de-duplicate by BOID, keeping last edited value
        df = df.drop_duplicates(subset=["BOID"], keep="last").reset_index(drop=True)

        conn = None
        cursor = None

        updated_rows = 0
        not_found_rows = []

        try:
            conn = db.get_connection()   # your psycopg2 connection
            cursor = conn.cursor()

            uploaded_boids = df["BOID"].tolist()

            # Fetch existing BOIDs once -> much faster than row-by-row select
            cursor.execute(
                """
                SELECT boid
                FROM demat_records
                WHERE boid = ANY(%s)
                """,
                (uploaded_boids,)
            )

            existing_boids = {str(row[0]).strip() for row in cursor.fetchall()}

            rows_to_update = []
            for _, row in df.iterrows():
                boid = row["BOID"]
                client_code = row["CLIENT CODE"]

                if boid in existing_boids:
                    rows_to_update.append((client_code, boid))
                else:
                    not_found_rows.append({
                        "BOID": boid,
                        "CLIENT CODE": client_code,
                        "REMARK": "BOID not found in demat_records"
                    })

            if rows_to_update:
                cursor.executemany(
                    """
                    UPDATE demat_records
                    SET client_code = %s
                    WHERE boid = %s
                    """,
                    rows_to_update
                )
                updated_rows = cursor.rowcount

            conn.commit()

            st.success(f"Update completed. Total updated rows: {updated_rows}")

            if not_found_rows:
                not_found_df = pd.DataFrame(not_found_rows)
                missing_count = len(not_found_rows)

                st.warning(f"{missing_count} BOID(s) were not found.")

                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    not_found_df.to_excel(writer, index=False, sheet_name="Not Found BOIDs")
                output.seek(0)

                file_name = f"missing_boids_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                st.download_button(
                    label=f"Download Missing BOIDs ({missing_count})",
                    data=output,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.dataframe(not_found_df, use_container_width=True, hide_index=True)
            else:
                st.info("All BOIDs were found and processed successfully.")

        except Exception as e:
            if conn:
                conn.rollback()
            st.error(f"Bulk update failed: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    
    def download_template(self):
        # Create empty DataFrame with required columns
        required_columns = ['DATE', 'BOID', 'NAME', 'CLIENT CODE', 'TSL', 
                        'AMOUNT', 'GATEWAY', 'RENEW TYPE', 'OPEN BY', 'BRO' ,'REMARKS']
        data = [['2082-09-25' ,'1301140000291235','SAPANA CHAND', '', 'TSL 17800','1200',	'CASH',	'BO OPEN,LIFETIME BO',	'SANGITA', 'SELF', ''],
                ['2082-09-26' ,'1301140000294543','BIPANA THAPA', '', 'TSL 17777','1700',	'CASH',	'ALL',	'SANGITA', 'UMESH', ''],
                ['2082-09-26' ,'1301140000294543','RAM ALI KHAN', '', 'TSL 17888','200',	'CASH',	'BO OPEN',	'SANGITA', 'UMESH', '']]
        df = pd.DataFrame(data=data,columns=required_columns)
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Template')
        except ImportError:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Template')
        data = output.getvalue()

        st.download_button(
            label="Download Sample File",
            data=data,
            file_name="sample_demat_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    def file_upload(self):
        REQUIRED_COLUMNS = ["BOID", "NAME", "TSL", "AMOUNT", "GATEWAY", "RENEW TYPE", "OPEN BY", "BRO"]
        GATEWAY_ALLOWED = ['CASH', 'QR', 'A/C DEBIT']
        RENEW_TYPE_ALLOWED = ['BO OPEN', 'LIFETIME BO', 'ALL', 'LIFETIME MEROSHARE', 'FREE']

        def is_renew_type_valid(cell_value: str) -> bool:
            # Split by comma, strip spaces
            values = [v.strip() for v in cell_value.split(',')]
            # Check all values are in allowed list
            return all(v in RENEW_TYPE_ALLOWED for v in values)
        
        self.download_template()

        if 'uploader_reset' not in st.session_state:
            st.session_state.uploader_reset = 0

        key = f"demat_uploader_{st.session_state.uploader_reset}"

        uploaded_file = st.file_uploader(
            "Upload Filled Template",
            type=".xlsx",
            key=key
        )

        if uploaded_file:
            st.divider()
            try:
                df = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"Failed to read Excel file: {e}")
                st.stop()
            st.write("Preview of Uploaded Data:")
            df.index = df.index + 1
            df['BRANCH'] = self.branch
            if 'OPEN BY' in df.columns:
                df['OPEN BY'] = df['OPEN BY'].astype(str).str.upper().str.strip()

            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                st.error(f"The following required columns are missing: {', '.join(missing_cols)}")
                st.stop()

            df_required = df[REQUIRED_COLUMNS].fillna("").astype(str).apply(lambda x: x.str.strip())
            empty_cells = df_required == ""
            rows_with_missing = empty_cells.any(axis=1)
            if rows_with_missing.any():
                st.error(f"Found {rows_with_missing.sum()} rows with empty required fields. Please fill them.")
                st.dataframe(df[rows_with_missing])
                st.stop()

            gateway_invalid = ~df_required['GATEWAY'].isin(GATEWAY_ALLOWED)
            if gateway_invalid.any():
                st.error(f"Found {gateway_invalid.sum()} rows with invalid GATEWAY. Allowed: {GATEWAY_ALLOWED}")
                st.dataframe(df[gateway_invalid])
                st.stop()

            renew_invalid = ~df_required['RENEW TYPE'].apply(is_renew_type_valid)
            if renew_invalid.any():
                st.error(f"Found {renew_invalid.sum()} rows with invalid RENEW TYPE values. Allowed: {RENEW_TYPE_ALLOWED}")
                st.dataframe(df[renew_invalid])
                st.stop()

            def validate_open_by(df_open_by):
                conn = db.get_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT username FROM app_user")
                        valid_users = {row[0] for row in cur.fetchall()}
                    df_open_by_clean = df_open_by.fillna("").astype(str).str.strip()
                    invalid_open_by = ~df_open_by_clean.isin(valid_users)
                    return invalid_open_by
                finally:
                    conn.close()

            open_by_invalid = validate_open_by(df_required['OPEN BY'])
            if open_by_invalid.any():
                st.error(f"Found {open_by_invalid.sum()} rows where 'OPEN BY' username is not registered in RMS. Please contact IT (9848094698).")
                st.dataframe(df[open_by_invalid])
                st.stop()

            if 'DATE' in df.columns:
                df['is_valid_bs'] = df['DATE'].apply(helper.is_valid_bs_date)
                invalid_count = (~df['is_valid_bs']).sum()
                if invalid_count > 0:
                    st.error(f"Found {invalid_count} invalid BS dates. Please correct them before submitting.")
                    st.dataframe(df[df['is_valid_bs'] == False])
                    st.stop()

            df = st.data_editor(df, num_rows="dynamic", hide_index=False)

            if st.button("ᯓ➤ Submit"):
                try:
                    inserted_count, skipped_count = db.dump_demat_records(df, self.username)
                except Exception as e:
                    st.error(f"Failed to import data: {e}")
                    st.stop()

                if inserted_count == 0 and skipped_count == 0:
                    st.error("No records were inserted or skipped. Check your data.")
                    st.stop()

                st.success(f"Data import completed! Inserted: {inserted_count}")
                if skipped_count > 0:
                    st.warning(f"Skipped (BOID exists): {skipped_count}")

                st.session_state.uploader_reset += 1
                sleep(2.5)
                st.rerun()



if __name__ == "__main__":
    DematRecords().render_page()