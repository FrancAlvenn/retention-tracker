# app_v3.py
# This version of the app builds on the clean architecture approach of v2 and adds a new

import streamlit as st
import pandas as pd
import altair as alt
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


def show_top_members_chart(df: pd.DataFrame, top_n: int = 10) -> None:
    """Show a bar chart of the top N members by Points.

    The x-axis is `Name` (str) and the y-axis is `Points` (int).
    This function uses only Streamlit display functions and the provided DataFrame.
    """
    if df is None or 'Name' not in df.columns or 'Points' not in df.columns:
        st.info("Top members chart unavailable: requires 'Name' and 'Points' columns.")
        return

    top = df[['Name', 'Points']].copy()
    top['Points'] = pd.to_numeric(top['Points'], errors='coerce')
    top = top.dropna(subset=['Name', 'Points'])
    if top.empty:
        st.info("No valid 'Name'/'Points' data to display.")
        return

    top = top.sort_values('Points', ascending=False).head(top_n)
    top['Points'] = top['Points'].astype(int)

    st.subheader(f"Top {len(top)} Members by Points")
    # Use Altair and explicit sort so x-axis is rendered left-to-right in descending order
    chart = (
        alt.Chart(top.reset_index(drop=True))
        .mark_bar()
        .encode(
            x=alt.X('Name:N', sort=top['Name'].tolist(), title='Name'),
            y=alt.Y('Points:Q', title='Points'),
            tooltip=[alt.Tooltip('Name:N'), alt.Tooltip('Points:Q')],
        )
    )
    st.altair_chart(chart, use_container_width=True)


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
    # render top-10 members by Points below the table
    show_top_members_chart(df)


if __name__ == "__main__":
    show_dashboard()



