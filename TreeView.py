import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts

st.set_page_config(page_title="Org Chart", layout="wide")

st.title("🌳 Organizational Tree (Excel Driven)")

# ------------------ TREE BUILDER ------------------
def build_tree(df):
    nodes = {row['id']: {"name": row['name'], "children": []} for _, row in df.iterrows()}
    root = None

    for _, row in df.iterrows():
        node_id = row['id']
        parent_id = row['parent_id']

        if pd.isna(parent_id):
            root = nodes[node_id]
        else:
            nodes[int(parent_id)]["children"].append(nodes[node_id])

    return root


# ------------------ READ EXCEL ------------------
try:
    df = pd.read_excel(r"C:\Users\Prabin\Desktop\Book1.xlsx")
    org_tree = build_tree(df)
except Exception as e:
    st.error(f"Error loading Excel: {e}")
    st.stop()


# ------------------ ECHARTS CONFIG ------------------
options = {
    "tooltip": {"trigger": "item"},
    "series": [
        {
            "type": "tree",
            "data": [org_tree],  # <<< MOST IMPORTANT LINE
            "top": "2%",
            "left": "5%",
            "bottom": "2%",
            "right": "20%",
            "symbol": "circle",
            "symbolSize": 16,
            "label": {
                "position": "left",
                "verticalAlign": "middle",
                "align": "right",
                "fontSize": 14,
                "overflow": "break",
                "width": 200
            },
            "leaves": {
                "label": {
                    "position": "right",
                    "align": "left",
                    "overflow": "break",
                    "width": 200
                }
            },
            "expandAndCollapse": True,
            "initialTreeDepth": -1
        }
    ]
}


# ------------------ DISPLAY ------------------
st_echarts(options, height="700px")














# import streamlit as st
# from streamlit_echarts import st_echarts

# st.set_page_config(page_title="Organizational Tree", layout="wide")

# st.title("🌳 Organizational Structure")

# # Sample organizational tree
# org_tree = {
#     "name": "CEO",
#     "children": [
#         {
#             "name": "Operations Head",
#             "children": [
#                 {"name": "Logistics Manager"},
#                 {"name": "Inventory Manager"},
#             ],
#         },
#         {
#             "name": "Technology Head",
#             "children": [
#                 {"name": "Backend Team"},
#                 {"name": "Frontend Team"},
#                 {
#                     "name": "DevOps",
#                     "children": [
#                         {"name": "Cloud Engineer"},
#                         {"name": "Security Engineer"},
#                     ],
#                 },
#             ],
#         },
#         {
#             "name": "Finance Head",
#             "children": [
#                 {"name": "Accounts"},
#                 {"name": "Billing"},
#             ],
#         }
#     ],
# }

# options = {
#     "tooltip": {
#         "trigger": "item",
#         "triggerOn": "mousemove"
#     },
#     "series": [
#         {
#             "type": "tree",
#             "data": [org_tree],
#             "left": "2%",
#             "right": "2%",
#             "top": "10%",
#             "bottom": "10%",
#             "expandAndCollapse": True,
#             "symbol": "circle",
#             "symbolSize": 18,
#             "label": {
#                 "position": "left",
#                 "verticalAlign": "middle",
#                 "align": "right",
#                 "fontSize": 14
#             },
#             "leaves": {
#                 "label": {
#                     "position": "right",
#                     "verticalAlign": "middle",
#                     "align": "left"
#                 }
#             },
#             "initialTreeDepth": -1,  # Fully expanded
#             "animationDurationUpdate": 750,
#         }
#     ]
# }

# st_echarts(options, height="700px", width="80%")
