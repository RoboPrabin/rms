from st_aggrid import AgGrid, ColumnsAutoSizeMode, GridOptionsBuilder, GridUpdateMode, JsCode
from db import db
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from nepali_datetime import date as nepali_date

from utils import helper
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
pd.set_option("styler.render.max_elements", 374688)  # or set to a big number like 1000000

class CostBenefit:

    def __init__(self):
        # helper.eliminate_top_padding()
        helper.eliminate_top_margin(margin_top="-8rem")
        st.session_state.active_menu = "business"
        st.set_page_config("Cost Benefit", page_icon="🌱", layout="wide")

        # --- Dates ---
        self.today_date = datetime.now().date()
        self.today_np_date = nepali_date.today()

        # --- Auth ---
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()

        self.username, self.role, self.branch = app_state.get_current_user_info()
        activate_client_code_hotkey()
        navigation.render_sidebar()

        # --- DB ---
        self.engine = helper.get_holding_engine()

        # --- Date selection ---
        yesterday = self.today_date
        st.title("🌱 Cost Benefit", anchor=False)
        # self.selected_date = st.date_input(
        #     "Select Business date",
        #     value=yesterday,
        #     width=400
        # )
        # self.week_day = self.selected_date.strftime("%A")
        # if 'cbr' not in st.session_state:
        #     st.session_state['cbr'] = db.get_cost_benefit_data()
        

    def render_page(self):
        df_cbr :pd.DataFrame = st.session_state['cbr']
        df_cbr.reset_index(inplace=True, drop=True)
        df_cbr.index = df_cbr.index + 1 
        print(df_cbr.columns)
        st.dataframe(df_cbr)

    def uat_page(self):

        # --- Sample column groups ---
        periods = {
            "15 Days": "",
            "1 Month": ".1",
            "3 Months": ".2"
        }

        metrics = [
            'Total Turnover', 'Total Commission', "Today's Due Amount",
            'Average Utilization Fund', 'Fund Utilized Days', 'Net Commission',
            'Opportunity Cost', 'Return in %', 'Client Zone'
        ]

        # --- Original df ---
        df = st.session_state['cbr']

        # --- Melt the df for each period ---
        dfs = []
        for period_name, suffix in periods.items():
            cols = ['Bro', 'Client Name', 'Client Code', 'Branch'] + [m + suffix for m in metrics] + ['uploaded_at']
            temp = df[cols].copy()
            temp.columns = ['Bro', 'Client Name', 'Client Code', 'Branch'] + metrics + ['uploaded_at']
            temp['Period'] = period_name
            dfs.append(temp)

        # --- Combine all periods into a single df ---
        df_long = pd.concat(dfs, ignore_index=True)

        # --- Now you can filter by period ---
        selected_period = st.selectbox("Select Period", list(periods.keys()))
        df_to_show = df_long[df_long['Period'] == selected_period]
        df_to_show.reset_index(inplace=True, drop=True)
        df_to_show.index = df_to_show.index + 1
        st.dataframe(df_to_show)

    def uat_page_one(self):

        df = st.session_state['cbr']

        # --- Period mapping for renaming columns ---
        periods = {
            "15 Days": "",
            "1 Month": ".1",
            "3 Months": ".2"
        }

        metrics = [
            'Total Turnover', 'Total Commission', "Today's Due Amount",
            'Average Utilization Fund', 'Fund Utilized Days', 'Net Commission',
            'Opportunity Cost', 'Return in %', 'Client Zone'
        ]

        # Create new column names like "15 Days - Total Turnover"
        new_columns = {}
        for period_name, suffix in periods.items():
            for metric in metrics:
                old_col = metric + suffix
                new_col = f"{period_name} - {metric}"
                new_columns[old_col] = new_col

        # Keep base columns
        base_cols = ['Bro', 'Client Name', 'Client Code', 'Branch', 'uploaded_at']

        # Rename metric columns
        df_renamed = df[base_cols + list(new_columns.keys())].rename(columns=new_columns)

        # Display in Streamlit
        st.title("Cost Benefit - All Periods")
        st.dataframe(df_renamed)

    def uat_color_row(self):
        df = st.session_state['cbr']

        # --- Period mapping for renaming columns ---
        periods = {
            "15 Days": "",
            "1 Month": ".1",
            "3 Months": ".2"
        }

        metrics = [
            'Total Turnover', 'Total Commission', "Today's Due Amount",
            'Average Utilization Fund', 'Fund Utilized Days', 'Net Commission',
            'Opportunity Cost', 'Return in %', 'Client Zone'
        ]

        # Create new column names like "15 Days - Total Turnover"
        new_columns = {}
        for period_name, suffix in periods.items():
            for metric in metrics:
                old_col = metric + suffix
                new_col = f"{period_name} - {metric}"
                new_columns[old_col] = new_col

        # Keep base columns
        base_cols = ['Bro', 'Client Name', 'Client Code', 'Branch', 'uploaded_at']

        # Rename metric columns
        df_renamed = df[base_cols + list(new_columns.keys())].rename(columns=new_columns)

        # --- Coloring function ---
        def color_period_rows(row):
            colors = pd.Series("", index=row.index)  # default: no color

            for period_name in periods.keys():
                zone_col = f"{period_name} - Client Zone"
                # Check the zone and set color
                if row[zone_col] == "GREEN LIST":
                    colors[[col for col in row.index if col.startswith(period_name)]] = "background-color: lightgreen"
                elif row[zone_col] == "RED LIST":
                    colors[[col for col in row.index if col.startswith(period_name)]] = "background-color: salmon"
                elif row[zone_col] == "gray":
                    colors[[col for col in row.index if col.startswith(period_name)]] = "background-color: lightgray"
                # else: leave as is (no color)
            return colors

        # --- Display with styling ---
        st.title("Cost Benefit - Colored by Client Zone")
        st.dataframe(df_renamed.style.apply(color_period_rows, axis=1))

    def uat_with_grid(self):
        df: pd.DataFrame = st.session_state['cbr']

        periods = {
            "15 Days": "",
            "1 Month": ".1",
            "3 Months": ".2"
        }

        metrics = [
            'Total Turnover', 'Total Commission', "Today's Due Amount",
            'Average Utilization Fund', 'Fund Utilized Days', 'Net Commission',
            'Opportunity Cost', 'Return in %', 'Client Zone'
        ]

        # Rename columns
        new_columns = {}
        for period_name, suffix in periods.items():
            for metric in metrics:
                old_col = metric + suffix
                new_col = f"{period_name} - {metric}"
                new_columns[old_col] = new_col

        base_cols = ['Bro', 'Client Name', 'Client Code', 'Branch']
        df_renamed = df[base_cols + list(new_columns.keys())].rename(columns=new_columns)

        # Build grid options
        gb = GridOptionsBuilder.from_dataframe(df_renamed)

        # Fixed JS for cell styling (works for all periods)
        js_code = """
        function(params) {
            let zone = params.data['Client Zone'];  // fallback
            let style = {
                border: '1px solid black',
                padding: '6px',
                whiteSpace: 'normal'
            };
            if (params.colDef.field.includes('15 Days')) {
                zone = params.data['15 Days - Client Zone'];
            } else if (params.colDef.field.includes('1 Month')) {
                zone = params.data['1 Month - Client Zone'];
            } else if (params.colDef.field.includes('3 Months')) {
                zone = params.data['3 Months - Client Zone'];
            }
            if (zone === 'GREEN LIST') style.backgroundColor = 'lightgreen';
            else if (zone === 'RED LIST') style.backgroundColor = 'salmon';
            else if (zone === 'gray') style.backgroundColor = 'lightgray';
            return style;
        }
        """

        # Configure columns with wider widths
        for col in df_renamed.columns:
            if col in base_cols:
                gb.configure_column(
                    col,
                    cellStyle=JsCode("function(params){return {border:'1px solid black', padding:'6px', whiteSpace:'normal'};}"),
                    width=180,          # wider base columns
                    minWidth=160,
                    wrapText=True
                )
            else:
                gb.configure_column(
                    col,
                    cellStyle=JsCode(js_code),
                    width=220,          # much wider for metric columns
                    minWidth=220,
                    wrapText=True,
                    autoHeight=True     # auto-adjust row height for wrapped text
                )

        # Enable copy-paste & range selection
        gb.configure_grid_options(
            enableRangeSelection=True,
            enableClipboard=True,
            suppressRowClickSelection=True,  # prevents row selection interfering
            headerHeight=60,
            wrapHeaderText=True,
            defaultColDef={
                'resizable': True,       # user can resize columns
                'sortable': True,
                'filter': True
            }
        )

        # Add this JS for header background
        header_js = """
        function(params) {
            let bg = 'white';
            if (params.column.colId.includes('15 Days')) bg = '#ffff99';  // yellow
            else if (params.column.colId.includes('1 Month')) bg = '#add8e6';  // blue
            else if (params.column.colId.includes('3 Months')) bg = '#ffb6c1';  // pink
            return { 'backgroundColor': bg, 'padding': '8px' };
        }
        """

        gb.configure_default_column(
            headerCellStyle=JsCode(header_js),
            resizable=True,
            sortable=True,
            filter=True
        )

        grid_options = gb.build()

        AgGrid(
            df_renamed,
            gridOptions=grid_options,
            height=600,
            update_mode=GridUpdateMode.NO_UPDATE,
            allow_unsafe_jscode=True,
            fit_columns_on_grid_load=False,  # keep your custom widths
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS  # important!
        )


    def display_page(self):
        st.markdown("<br>", unsafe_allow_html=True)
        date_str = db.get_cbr_created_date()
        if date_str is None:
            st.warning(f"Cost Benefit report not generated yet.", icon="📢")
            st.stop()
            
        formatted_date = date_str.strftime('%Y-%m-%d %I:%M:%S %p')
        st.info(f"Cost benefit report has been generated on {formatted_date}", icon="📢")
        st.markdown("<br>", unsafe_allow_html=True)
        # file_path = r"D:\Project-2025\JV\MHN DEMAT_TMS 208_83.xlsx"# full path to your file
        file_path = db.get_cbr_filename()
        file_name = f"Cost_Benefit_Report_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        
        # Open file in binary mode
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        # Streamlit download button
        st.download_button(
            label="Download Excel File",
            data=file_bytes,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        # option = st.radio("Select option", ['Download Report', 'View Report'], horizontal=True)
        # if option == "Download Report":
        # else:
            # pass


if __name__ == "__main__":
    # CostBenefit().render_page()
    # CostBenefit().uat_page()
    # CostBenefit().uat_page_one()
    # CostBenefit().uat_color_row()
    # CostBenefit().uat_with_grid()
    CostBenefit().display_page()