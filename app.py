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
    # hide ID in the UI for the members sheet while keeping df unchanged
    display_df = df.copy()
    if sheet == "members" and 'ID' in display_df.columns:
        display_df = display_df.drop(columns=['ID'])
    st.dataframe(display_df)
    # render top-10 members by Points below the table
    show_top_members_chart(df)
    # allow logging points for the displayed members sheet
    df = add_points_form(df)
    # allow adding a new member
    df = add_member(df)
    # allow creating an event attendance sheet entry
    create_event_form(df)


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


def save_attendance(df_attendance: pd.DataFrame, path: str = "data/members.xlsx", extra_sheets: dict = None) -> None:
    """Save the `event_attendance` sheet back to the Excel workbook.

    If the file exists, preserve other sheets and overwrite the `event_attendance` sheet.
    If the file or sheet does not exist, create it.
    """
    try:
        sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    except FileNotFoundError:
        sheets = {}

    sheets["event_attendance"] = df_attendance.copy()

    # Ensure any extra sheets provided by the caller are included (e.g., current `members` DataFrame)
    if extra_sheets:
        for k, v in extra_sheets.items():
            # overwrite or add the extra sheet with the provided DataFrame
            sheets[k] = v.copy()

    # Ensure directory exists
    dirpath = os.path.dirname(path) or "."
    os.makedirs(dirpath, exist_ok=True)

    tmp_name = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir=dirpath)
        tmp_name = tmp.name
        tmp.close()
        with pd.ExcelWriter(tmp_name, engine="openpyxl", mode="w") as writer:
            for name, df in sheets.items():
                df.to_excel(writer, sheet_name=name, index=False)

        os.replace(tmp_name, path)
    except PermissionError as e:
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
        # allow negative entries but warn; enforce an absolute cap to prevent extreme values
        pts = st.number_input("Points to Add", min_value=-9999, max_value=9999, step=1, value=1)
        submitted = st.form_submit_button("Log Points")

    if submitted:
        if not student_id or str(student_id).strip() == "":
            st.error("Student ID is required.")
            return df_members

        # warn on unusual point values but allow the operation to proceed
        if int(pts) < 0 or int(pts) > 9999:
            st.warning("Points value is outside the recommended range (0–9999). Proceeding anyway.")

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


def add_member(df_members: pd.DataFrame) -> pd.DataFrame:
    """Show a form to add a new member.

    - Validates non-blank `Student ID` and `Name` inputs.
    - Optional `Base Points` (default 0).
    - Checks for duplicate `StudentID` in the provided DataFrame and shows a specific error.
    - On success: appends the new member row to `df_members`, calls `save_data`, clears cache, and shows success message.
    - Returns the (possibly updated) DataFrame.
    """
    st.subheader("Add New Member")

    with st.form("add_member_form"):
        student_id = st.text_input("Student ID", value="")
        name = st.text_input("Name", value="")
        base_points = st.number_input("Base Points (optional)", min_value=0, max_value=9999, step=1, value=0)
        submitted = st.form_submit_button("Add Member")

    if submitted:
        # sanitize and validate required fields (no logic functions called here)
        student_id = str(student_id).strip()
        name = str(name).strip()
        try:
            base_points_int = int(base_points)
        except Exception:
            st.error("Base Points must be an integer.")
            return df_members

        # If StudentID left blank, auto-generate a new unique numeric ID
        if student_id == "":
            generated_id = None
            try:
                if df_members is not None and 'StudentID' in df_members.columns:
                    # attempt to parse existing IDs as integers and pick max+1
                    nums = pd.to_numeric(df_members['StudentID'], errors='coerce')
                    if nums.notna().any():
                        max_id = int(nums.max())
                        generated_id = str(max_id + 1)
                    else:
                        # fallback to simple incremental ID based on row count
                        generated_id = str(len(df_members) + 1)
                else:
                    generated_id = "1"
            except Exception:
                generated_id = "1"

            student_id = generated_id
            st.info(f"Assigned Student ID {student_id}.")
        if name == "":
            st.error("Name is required.")
            return df_members

        # base points edge cases
        # warn on base points edge cases but allow creation to proceed
        if base_points_int < 0 or base_points_int > 9999:
            st.warning("Base Points is outside the recommended range (0–9999). The member will be created with this value.")

        # additional simple edge checks
        if "\n" in student_id or "\r" in student_id:
            st.error("Student ID must not contain newlines.")
            return df_members
        if len(student_id) > 100:
            st.error("Student ID is too long (max 100 characters).")
            return df_members
        if len(name) > 200:
            st.error("Name is too long (max 200 characters).")
            return df_members

        # check duplicate StudentID (exact match)
        if df_members is not None and 'StudentID' in df_members.columns:
            dup_mask = df_members['StudentID'].astype(str) == student_id
            if dup_mask.any():
                st.error(f"Student ID '{student_id}' already exists.")
                return df_members

        # append new row
        new_row = {
            'StudentID': student_id,
            'Name': name,
            'Points': base_points_int,
        }

        try:
            new_df = pd.concat([df_members, pd.DataFrame([new_row])], ignore_index=True)
        except Exception:
            # fallback: if df_members is None or concat fails, create new DataFrame
            new_df = pd.DataFrame([new_row])

        # persist and instruct user to refresh
        try:
            save_data(new_df)
            try:
                st.cache_data.clear()
            except Exception:
                pass
            st.success("Member added successfully. Click 'Refresh Data' to update the table.")
            # set flag so dashboard can show persistent message if needed
            st.session_state["points_logged_success"] = False
            st.session_state["member_added_success"] = True
        except Exception as e:
            st.error(f"Failed to save new member: {e}")
            return df_members

        return new_df

    return df_members


def create_event_form(df_members: pd.DataFrame) -> None:
    """Show a form to create a new event attendance entries.

    - Reads existing `event_attendance` from the workbook (if present).
    - Presents `Event Name` and `Attendees` (multiselect of member Names).
    - On submit: resolves Names to StudentIDs, appends rows to attendance, calls `save_attendance`, and shows success.
    """
    st.subheader("Create Event")

    # Build attendee choices from df_members
    names = []
    if df_members is not None and 'Name' in df_members.columns:
        names = df_members['Name'].dropna().astype(str).tolist()

    with st.form("create_event_form"):
        event_name = st.text_input("Event Name", value="")
        attendees = st.multiselect("Attendees", options=names)
        submitted = st.form_submit_button("Create Event")

    if not submitted:
        return

    event_name = str(event_name).strip()
    if event_name == "":
        st.error("Event Name is required.")
        return

    if not attendees:
        st.error("Select at least one attendee.")
        return

    # Resolve selected Names to StudentIDs (allow duplicates: multiple students with same name)
    rows = []
    for name in attendees:
        matches = df_members[df_members['Name'].astype(str) == str(name)]
        if matches.empty:
            # No matching student; skip or report — we will skip and continue
            continue
        for sid in matches['StudentID'].tolist():
            rows.append({'Event': event_name, 'StudentID': sid})

    if not rows:
        st.error("No valid StudentIDs resolved for selected attendees.")
        return

    # Load existing attendance sheet if present
    path = "data/members.xlsx"
    try:
        existing = pd.read_excel(path, sheet_name='event_attendance', engine='openpyxl')
    except Exception:
        existing = pd.DataFrame(columns=['Event', 'StudentID'])

    try:
        new_att = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    except Exception:
        new_att = pd.DataFrame(rows)

    try:
        # pass current members DF to ensure members sheet is preserved when writing
        save_attendance(new_att, extra_sheets={'members': df_members})
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.success("Event created successfully.")
    except Exception as e:
        st.error(f"Failed to save attendance: {e}")


if __name__ == "__main__":
    show_dashboard()



