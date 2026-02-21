# app_v2.py
# This version of the app is refactored to follow a clean architecture approach, separating concerns into data, logic, and interface layers. The data loading and processing functions are decoupled from the Streamlit UI code, making it easier to maintain and test each layer independently.

import streamlit as st
import pandas as pd
from typing import Dict, List


# ----------------
# Data layer
# ----------------
@st.cache_data
def load_data(path: str = "data/members.xlsx") -> Dict[str, pd.DataFrame]:
    """Load all sheets from an Excel file and return a dict of DataFrames.

    This function belongs to the data layer and does not call Streamlit UI functions.
    """
    return pd.read_excel(path, sheet_name=None, engine="openpyxl")


# ----------------
# Logic layer
# ----------------
def sheet_names(data: Dict[str, pd.DataFrame]) -> List[str]:
    """Return sorted list of sheet names from loaded Excel data."""
    return list(data.keys()) if data is not None else []


def get_sheet(data: Dict[str, pd.DataFrame], name: str) -> pd.DataFrame:
    """Return the DataFrame for the requested sheet name."""
    return data[name]


# ----------------
# Interface layer
# ----------------
def show_dashboard() -> None:
    """Streamlit interface: presents controls and displays DataFrames.

    This function is the interface layer and should only call Streamlit functions
    and the data/logic layer functions defined above.
    """
    st.set_page_config(page_title="Members Loader", layout="centered")
    st.title("Members — Excel Loader")

    st.write("Load `members.xlsx` and choose a sheet to display")

    try:
        data = load_data()
    except FileNotFoundError:
        st.error("`members.xlsx` not found. Place it in the project root or upload it.")
        return
    except Exception as e:
        st.error(f"Failed to load Excel file: {e}")
        return

    sheets = sheet_names(data)
    if not sheets:
        st.info("No sheets found in the Excel file.")
        return

    default_index = sheets.index("members") if "members" in sheets else 0
    sheet = st.selectbox("Select sheet", sheets, index=default_index)

    # display selected sheet using only Streamlit display functions
    df = get_sheet(data, sheet)
    st.dataframe(df)


if __name__ == "__main__":
    show_dashboard()



