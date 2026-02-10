from pandas.io.formats.style import Styler
import pandas as pd

def right_align_headers(styler: Styler) -> Styler:
    styler.set_table_styles(
        [
            {"selector": "th", "props": [("text-align", "right !important")]},
            {"selector": "thead th", "props": [("text-align", "right !important")]},
            {"selector": "thead tr th", "props": [("text-align", "right !important")]},
            {"selector": "th.col_heading", "props": [("text-align", "right !important")]},
            {"selector": "th.col_heading.level0", "props": [("text-align", "right !important")]},
        ],
        overwrite=True
    )
    return styler

def accounting_format(x):
    if pd.isna(x):
        return ""
    return f"({abs(x):,.2f})" if x < 0 else f"{x:,.2f}"

def highlight_negative(val):
    if pd.isna(val):
        return ""
    return "color: red;" if val < 0 else ""

def coerce_numeric_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=True)
                .replace("", "0")
                .astype(float)
            )
    return df