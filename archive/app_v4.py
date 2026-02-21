# app_v4.py
# This version of the app builds on the clean architecture approach of v3 and adds a new

import streamlit as st
import pandas as pd
import altair as alt
import os
import tempfile
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

    # Refresh button: user-triggered reload of cached data
    if st.button("Refresh Data"):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        # clear the success flag so message won't persist after refresh
        st.session_state["points_logged_success"] = False
        # Streamlit reruns the script automatically on widget interaction,
        # so an explicit rerun call is not required here.

    # If we recently logged points, show a success message and instruction
    if st.session_state.get("points_logged_success", False):
        st.success("Points logged successfully. Click 'Refresh Data' to update the table.")

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
    # allow logging points for the displayed members sheet
    df = add_points_form(df)


# ----------------
# Logic: point logging (no Streamlit, no I/O)
# ----------------
def log_points(df_members: pd.DataFrame, student_id: str, pts: int):
    """Add `pts` to the matching student's Points value.

    Matches `StudentID` using exact string comparison. Returns (df_members, True)
    on success or (df_members, False) if no matching StudentID is found.
    This function performs no Streamlit calls and does not perform file I/O.
    """
    if df_members is None or 'StudentID' not in df_members.columns:
        return df_members, False

    mask = df_members['StudentID'].astype(str) == str(student_id)
    if not mask.any():
        return df_members, False

    # Safely coerce existing Points to numeric for the matched rows, treat NaN as 0
    existing = pd.to_numeric(df_members.loc[mask, 'Points'], errors='coerce').fillna(0).astype(int)
    df_members.loc[mask, 'Points'] = existing + int(pts)

    return df_members, True


# ----------------
# Data save helper
# ----------------
def save_data(df_members: pd.DataFrame, path: str = "data/members.xlsx") -> None:
    """Save the `members` sheet back to the Excel workbook.

    If the file exists, preserve other sheets and overwrite the `members` sheet.
    If the file does not exist, create a new workbook containing only `members`.
    """
    try:
        sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    except FileNotFoundError:
        sheets = {}

    sheets["members"] = df_members.copy()

    # Ensure directory exists
    dirpath = os.path.dirname(path) or "."
    os.makedirs(dirpath, exist_ok=True)

    # Write to a temporary file in the same directory then atomically replace.
    tmpf = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir=dirpath)
        tmp_name = tmp.name
        tmp.close()
        with pd.ExcelWriter(tmp_name, engine="openpyxl", mode="w") as writer:
            for name, df in sheets.items():
                df.to_excel(writer, sheet_name=name, index=False)

        # Atomic replace (will overwrite existing file)
        os.replace(tmp_name, path)
    except PermissionError as e:
        # Clean up tmp file if present
        try:
            if tmp_name and os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass
        raise PermissionError(
            f"Permission denied while saving '{path}'. The file may be open in Excel or locked by another process. Close any program using the file and try again. Original error: {e}"
        ) from e
    except Exception:
        try:
            if tmp_name and os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass
        raise


# ----------------
# Interface helper: points form
# ----------------
def add_points_form(df_members: pd.DataFrame) -> pd.DataFrame:
    """Show a Streamlit form to log points for a student.

    Behavior:
    - Displays a form with `Student ID` (text) and `Points to Add` (number).
    - On submit: validates input, calls `log_points`, and on success calls `save_data`.
    - Returns the (possibly updated) `df_members` DataFrame.
    """
    st.subheader("Log Points")

    with st.form("log_points_form"):
        student_id = st.text_input("Student ID", value="")
        pts = st.number_input("Points to Add", min_value=1, step=1, value=1)
        submitted = st.form_submit_button("Log Points")

    if submitted:
        if not student_id or str(student_id).strip() == "":
            st.error("Student ID is required.")
            return df_members

        df_members, ok = log_points(df_members, student_id, int(pts))
        if not ok:
            st.error("Student ID not found.")
            return df_members

        # persist changes and report success
        try:
            save_data(df_members)
            # clear cached data so load_data() reads the updated Excel on rerun
            try:
                st.cache_data.clear()
            except Exception:
                # older Streamlit versions may not expose clear(); ignore if unavailable
                pass
            # set a session flag so the UI can show a success message
            st.session_state["points_logged_success"] = True
            # instruct user to refresh manually instead of auto-rerun
            st.success("Points logged successfully. Click 'Refresh Data' to update the table.")
            return df_members
        except Exception as e:
            st.error(f"Failed to save data: {e}")
            return df_members

    return df_members


if __name__ == "__main__":
    show_dashboard()



