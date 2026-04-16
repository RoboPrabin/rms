import streamlit as st
import io
import pandas as pd
from db import db
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.custom_hotkey import activate_client_code_hotkey

from pages.BasePage import BasePage


@st.cache_data(ttl=120)
def get_all_kyc_info():
    rows = db.get_kyc()
    return pd.DataFrame(rows, columns=["CLIENT CODE", "CLIENT NAME", "BRANCH", "BOID"])


class TMSCode(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin(margin_top="-4rem")
        st.session_state.active_menu = "kyc"
        st.set_page_config(page_title="TMS Code", page_icon="🏷️", layout="wide")
        navigation.render_sidebar()
        st.title("🏷️ Find TMS Code", anchor=False)
        
    def process_kyc(self, df, kyc_data):
        df.columns = df.columns.str.upper()
        kyc_data.columns = kyc_data.columns.str.upper()
        df["BOID"] = df["BOID"].astype(str)
        kyc_data["BOID"] = kyc_data["BOID"].astype(str)
        
        result = df.merge(kyc_data[["BOID", "CLIENT CODE"]], on="BOID", how="left")
        result["CLIENT CODE"] = result["CLIENT CODE"].fillna("N/A")
        result.index += 1
        return result
    
    def process_branch(self, df, kyc_data):
        df.columns = df.columns.str.upper()
        kyc_data.columns = kyc_data.columns.str.upper()
        df["BOID"] = df["BOID"].astype(str)
        kyc_data["BOID"] = kyc_data["BOID"].astype(str)
        
        result = df.merge(kyc_data[["BOID", "BRANCH"]], on="BOID", how="left")
        result["BRANCH"] = result["BRANCH"].fillna("N/A")
        result.index += 1
        return result
    
    def download_excel(self, df, filename):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Result")
        return output.getvalue()
    
    def sample_file_download(self, filename, file_path):
        with open(file_path, "rb") as f:
            content = f.read()

        st.download_button(
            label="📥 Download Sample File",
            data=content,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    def main(self):
        option = st.radio("Find", ["Client Code", "Branch"], horizontal=True, key="tms_option")

        if "prev_tms_option" not in st.session_state:
            st.session_state.prev_tms_option = option
        
        if st.session_state.prev_tms_option != option:
            for key in ["tms_result", "branch_result"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.prev_tms_option = option

        if option == "Client Code":
            self.sample_file_download(
                "sample.xlsx",
                r"D:\Anjit\project\rms\data\sample.xlsx"
            )
            uploaded_file = st.file_uploader("Upload File", type=["csv", "xlsx"], key="kyc_upload")

            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                    df.index += 1

                    st.subheader("📊 Uploaded Data", anchor=False)
                    st.dataframe(df, width="stretch")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("🌐 Find TMS Code"):
                            kyc_data = get_all_kyc_info()
                            result = self.process_kyc(df, kyc_data)
                            st.session_state.tms_result = result
                            
                            found = (result["CLIENT CODE"] != "N/A").sum()
                            not_found = (result["CLIENT CODE"] == "N/A").sum()
                            st.success(f"✅ TMS Code found: {found}")
                            st.warning(f"⚠️ TMS code not found: {not_found}")

                    if "tms_result" in st.session_state:
                        with col2:
                            data = self.download_excel(st.session_state.tms_result, "tms_code_result.xlsx")
                            st.download_button("📥 Download Result", data, "tms_code_result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    
                    if "tms_result" in st.session_state:
                        with st.expander("Client Code Result Details", expanded=False):
                            st.subheader("📈 Matched Result", anchor=False)
                            st.dataframe(st.session_state.tms_result, width="stretch")

                except Exception as e:
                    st.error(f"Error processing file: {e}")
        
        if option == "Branch":
            uploaded_file = st.file_uploader("Upload Data", type=["csv", "xlsx"], key="branch_upload")

            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                    df.index += 1

                    st.subheader("📊 Uploaded Data", anchor=False)
                    st.dataframe(df, width="stretch")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("🌐 Find Branch Code", key="branch_btn"):
                            kyc_data = get_all_kyc_info()
                            result = self.process_branch(df, kyc_data)
                            st.session_state.branch_result = result
                            
                            found = (result["BRANCH"] != "N/A").sum()
                            not_found = (result["BRANCH"] == "N/A").sum()
                            st.success(f"✅ Branch found: {found}")
                            st.warning(f"⚠️ Branch not found: {not_found}")

                    if "branch_result" in st.session_state:
                        with col2:
                            data = self.download_excel(st.session_state.branch_result, "branch_result.xlsx")
                            st.download_button("📥 Download Result", data, "branch_result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    
                    if "branch_result" in st.session_state:
                        with st.expander("Branch Result Details", expanded=False):
                            st.subheader("📈 Matched Branch Result", anchor=False)
                            st.dataframe(st.session_state.branch_result, width="stretch")

                except Exception as e:
                    st.error(f"Error processing file: {e}")

if __name__ == "__main__":
    page = TMSCode()
    page.main()