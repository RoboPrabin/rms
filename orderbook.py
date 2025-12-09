
# import streamlit as st
# import pandas as pd


# df = pd.read_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\open_and_completed.xlsx")

# st.dataframe(df, width='stretch')



from utils import helper
import streamlit as st
import pandas as pd

@st.cache_data(ttl=6000)
def load_order_book_data():
    df = pd.read_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\open_and_completed.xlsx")
    return df

st.set_page_config(layout='wide')
# Load your data

# df = pd.read_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\open_and_completed.xlsx")
df = load_order_book_data()
# Calculate amount column
# df["amount"] = df["orderQuantity"] * df["orderPrice"]

# Get unique activeStatus values
statuses = ["All"] + df["activeStatus"].dropna().unique().tolist()

# Horizontal buttons for activeStatus
selected_status = st.radio("Filter by Active Status:", options=statuses, horizontal=True)

# Filter dataframe
if selected_status == "All":
    filtered_df = df
else:
    filtered_df = df[df["activeStatus"] == selected_status]

# --- BUY and SELL totals ---
buy_total = filtered_df.loc[filtered_df["buyOrSell"] == "BUY", "amount"].sum()
sell_total = filtered_df.loc[filtered_df["buyOrSell"] == "SELL", "amount"].sum()

net_total = buy_total + sell_total

col1, col2 = st.columns(2)
# Show badges
with col1:
    st.badge(f"BUY Amount: {buy_total:,.2f}", color="red")
    st.badge(f"SELL Amount: {sell_total:,.2f}",color="green")
    st.badge(f"Net Amount: {net_total:,.2f}",color="orange")


# Show filtered dataframe
filtered_df = helper.format_dataframe(filtered_df)
filtered_df.reset_index(drop=True, inplace=True)
filtered_df.index = filtered_df.index + 1
st.dataframe(filtered_df, use_container_width=True)
