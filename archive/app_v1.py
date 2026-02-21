# app_v1.py
# This is a simple Streamlit app to load and display Excel sheets.


import streamlit as st
import pandas as pd

st.set_page_config(page_title="Members Loader", layout="centered")

st.title("Members — Excel Loader")


@st.cache_data
def load_data(path: str = "members.xlsx") -> dict:
    """Load all sheets from an Excel file and return a dict of DataFrames.

    Returns a dict mapping sheet name -> DataFrame.
    """
    # pandas will auto-detect engine; specify openpyxl if installed for .xlsx
    return pd.read_excel(path, sheet_name=None, engine="openpyxl")


st.write("Load `members.xlsx` and choose a sheet to display")
try:
    data = load_data()
    sheets = list(data.keys())
    if not sheets:
        st.info("No sheets found in the Excel file.")
    else:
        default_index = sheets.index("members") if "members" in sheets else 0
        sheet = st.selectbox("Select sheet", sheets, index=default_index)
        st.dataframe(data[sheet])
except FileNotFoundError:
    st.error("`members.xlsx` not found. Place it in the project root or upload it.")
except Exception as e:
    st.error(f"Failed to load Excel file: {e}")


