# Handover: Retention Tracker (Streamlit) — v3

## 1. PROJECT SUMMARY

Retention Tracker is a small Streamlit dashboard that loads member and event attendance data from an Excel workbook (`data/members.xlsx`) and provides quick data inspection and lightweight admin operations. The app displays selected sheets, a top-members bar chart, and includes forms to log points for an existing member, add new members, and create event attendance entries. Changes are persisted back to the same Excel workbook.

## 2. TECH STACK (exact)

- Python: 3.14.0 (development environment)
- streamlit==1.54.0
- pandas==2.3.3
- openpyxl==3.1.5
- numpy==2.4.2
- pyarrow==23.0.1
- altair==6.0.0

Note: `requirements.txt` originally lists runtime dependencies (`streamlit`, `pandas`, `openpyxl`); `altair==6.0.0` was added/used for charts.

## 3. FILE STRUCTURE

- `app.py` — single-file Streamlit application containing three logical layers:
  - Data layer: `load_data`, `save_data`, `save_attendance`.
  - Logic layer: `sheet_names`, `get_sheet`, `log_points`.
  - Interface layer: `show_dashboard`, `show_top_members_chart`, `add_points_form`, `add_member`, `create_event_form`.
  Entry point: `if __name__ == "__main__": show_dashboard()`.

- `requirements.txt` — minimal runtime deps (streamlit, pandas, openpyxl).
- `README.md` — run instructions (short).
- `data/` — runtime data folder.
  - `data/members.xlsx` — Excel workbook used by the app (sheets: `members`, `event_attendance`).
- `archive/` — older `app_v1.py`, `app_v2.py`, `app_v3.py` (reference; not edited).
- `handover_doc/` — handover markdown files.
  - `handover_v1.md`, `handover_v2.md`, `handover_v3.md` (this file).
- `env/` — local Python virtual environment (gitignored normally).
- `__pycache__/` — python bytecode cache.

## 4. DATA STRUCTURES

Excel workbook: `data/members.xlsx` — sheets used by the app:

- Sheet `members` (expected exact column names and typical types used by the app):
  - `StudentID` — stored/treated as string in-app but often numeric in file (pandas dtype object when mixed); unique identifier for students (exact-match comparisons use stringified values).
  - `Name` — string/object (member full name)
  - `Points` — integer (pandas stores as numeric; app coerces to int when needed)

- Sheet `event_attendance`:
  - `Event` — string/object
  - `StudentID` — string/integer (matches `members.StudentID` values)

Exact variable / function names in `app.py` (runtime names and notable locals):

- Data layer functions/variables:
  - `load_data(path: str = "data/members.xlsx")` — returns Dict[str, pd.DataFrame]
  - `save_data(df_members: pd.DataFrame, path: str = "data/members.xlsx")`
  - `save_attendance(df_attendance: pd.DataFrame, path: str = "data/members.xlsx", extra_sheets: dict = None)`

- Logic layer:
  - `sheet_names(data: Dict[str, pd.DataFrame]) -> List[str]`
  - `get_sheet(data: Dict[str, pd.DataFrame], name: str) -> pd.DataFrame`
  - `log_points(df_members: pd.DataFrame, student_id: str, pts: int) -> (pd.DataFrame, bool)`

- Interface layer & runtime variables (in `show_dashboard()`):
  - `data` (dict[str, pd.DataFrame]) — result of `load_data()`
  - `sheets` (list[str]) — result of `sheet_names(data)`
  - `default_index` (int) — index chosen for selectbox default
  - `sheet` (str) — selected sheet name
  - `df` (DataFrame) — DataFrame returned by `get_sheet(data, sheet)`
  - `display_df` (DataFrame) — copy of `df` used for UI display (used to drop `StudentID` from members view)

- Form-scoped variables (examples):
  - `add_points_form`: `student_id` (str), `pts` (int)
  - `add_member`: `student_id` (str), `name` (str), `base_points` / `base_points_int` (int)
  - `create_event_form`: `event_name` (str), `attendees` (List[str]) — selected member `Name`s
  - Internal temporary names like `new_row`, `new_df`, `rows`, `new_att` used when constructing appended DataFrames.

## 5. FEATURES IMPLEMENTED

1) Excel loader (all sheets)
- Function: `load_data(path)`
- Behavior: uses `pandas.read_excel(path, sheet_name=None, engine='openpyxl')` to load all sheets and returns a dict keyed by sheet name. Cached with `@st.cache_data`.
- Constraint: Expects `data/members.xlsx` to exist (no upload fallback implemented).

2) Sheet listing and selection
- Functions: `sheet_names(data)` + `st.selectbox` inside `show_dashboard()`
- Behavior: displays available sheet names and defaults to `members` if present.

3) Sheet display (with StudentID hidden for members)
- Function: `get_sheet(data, name)` + UI in `show_dashboard()`
- Behavior: renders selected sheet via `st.dataframe`. For sheet `members` the `StudentID` column is removed from the displayed copy (keeps underlying DataFrame intact for logic).

4) Top-N members chart (descending)
- Function: `show_top_members_chart(df, top_n=10)`
- Behavior: extracts `Name` and `Points`, coerces `Points` to numeric, drops invalid rows, sorts descending, renders an Altair bar chart with explicit X-axis ordering.
- Constraint: Requires `Name` and `Points` columns.

5) Log Points form (per-member)
- Function: `add_points_form(df_members)` + backing logic `log_points`
- UI elements: `Student ID` (text), `Points to Add` (number, range -9999..9999 allowed), submit button.
- Behavior: Validates non-blank Student ID, warns for out-of-range point values (<0 or >9999) but allows them, calls `log_points` (which updates `Points` in-memory for exact StudentID matches) and then `save_data()` to persist changes. Shows instruction to click `Refresh Data` to refresh the display.
- Constraint: Uses exact string match on `StudentID`; shows error if ID not found.

6) Add Member form
- Function: `add_member(df_members)`
- UI elements: `Student ID` (text; optional — auto-generated if left blank), `Name` (text), `Base Points` (number, UI min 0 max 9999)
- Behavior: trims inputs, validates length/newline constraints, warns on base-points outside 0–9999 (but allows), auto-generates a numeric `StudentID` if blank (tries max(existing numeric IDs)+1), checks for duplicate IDs, appends new row to a new DataFrame, calls `save_data()` and instructs user to refresh.
- Constraint/Decision: `StudentID` duplicates are rejected; auto-generation prefers numeric sequences but will fall back to simple row-count-based ID.

7) Create Event form
- Function: `create_event_form(df_members)` + `save_attendance(df_attendance)`
- UI elements: `Event Name` (text), `Attendees` (multiselect of member `Name`s)
- Behavior: Validates event name and at least one attendee; resolves selected `Name`s to all matching `StudentID`s (handles possible duplicate names by resolving all matches), creates one attendance row per resolved StudentID with `Event` and `StudentID`, appends to existing `event_attendance` sheet (if present) via `pd.concat`, and calls `save_attendance()` to persist.
- Constraint: If a selected `Name` resolves to multiple `StudentID`s, all are added. If no StudentIDs resolved, the operation reports an error.

8) Save helpers with atomic writes
- Functions: `save_data`, `save_attendance`
- Behavior: Write to a temporary file in the `data/` directory, then atomically replace the original `members.xlsx`. `save_attendance` accepts `extra_sheets` to ensure other sheets (like `members`) are preserved when writing attendance.
- Constraint: If file is locked by Excel or another process, a clear PermissionError message is raised. Temporary files are cleaned up on error.

9) Manual Refresh UI
- The dashboard includes a `Refresh Data` button that clears the `load_data` cache and triggers Streamlit's normal rerun on widget interaction. Success messages instruct the user to click Refresh after a write so the displayed table updates.

## 6. BUGS FIXED (this session)

1) NameError for `add_points_form`
- Problem: A call to `add_points_form` occurred before the function was defined (NameError). 
- Fix: Moved `if __name__ == "__main__": show_dashboard()` to file end so all helper functions are defined first.

2) Members sheet overwritten when saving attendance
- Problem: Writing `event_attendance` previously overwrote or replaced the `members` sheet.
- Fix: `save_attendance` now preserves existing workbook sheets and supports `extra_sheets` parameter; `create_event_form` passes current `members` DF via `extra_sheets={'members': df_members}` so `members` is preserved.

3) Partial-write/race and PermissionError handling
- Problem: Direct writing risked partial writes and unclear PermissionError.
- Fix: `save_data` and `save_attendance` write to a temp file then `os.replace` to atomically overwrite the Excel file. PermissionError is caught and re-raised with a clearer hint to close Excel or unlock the file.

4) Display refresh not immediate
- Problem: After saving, the UI did not show updated values until a manual page refresh.
- Fix: Implemented `st.cache_data.clear()` calls after saving and added a `Refresh Data` button to explicitly clear cache and rerun. Added session-state flags and user guidance messages.

5) Chart ordering
- Problem: Bars were not guaranteed left-to-right descending order.
- Fix: Implemented the chart with Altair and explicit X-axis sort using the top members ordering.

## 7. DECISIONS MADE

- Single-file policy: Kept the app in `app.py` to simplify onboarding and avoid cross-file imports.
- Layer separation: Implemented Data, Logic, and Interface layers as distinct functions within `app.py` to make future testing/refactor easier.
- Use `openpyxl` engine: Chosen for reliable `.xlsx` I/O.
- Use Altair for charting: Ensures deterministic sort and tooltips; `altair==6.0.0` required.
- Manual refresh UX: Chose a user-triggered `Refresh Data` button instead of automatic rerun to avoid surprises and compatibility issues with `st.experimental_rerun` across Streamlit versions.
- StudentID privacy: The `StudentID` column is hidden from the members table display for privacy while keeping it in the underlying DataFrame for logic.
- Auto-generated IDs: If the user leaves `Student ID` blank when adding a member, the app auto-generates a numeric ID (max existing numeric ID + 1 when possible). This reduces friction for quick adds.
- Warnings vs strict errors: For unusual points inputs (<0 or >9999) the app displays warnings and permits operations; duplicate IDs remain blocking errors.

Deliberately NOT built (and why):
- No file upload fallback: The app expects `data/members.xlsx` to be present. An upload widget was omitted to keep the UI minimal (recommended next step).
- No unit tests: Not added in this session; recommended to add tests for `log_points`, append behavior, and `save_*` functions.
- No advanced locking detection: The app reports PermissionError and suggests closing Excel; it does not attempt to programmatically release file handles.

## 8. RUN COMMANDS

1) Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2) Install dependencies (recommended):

```powershell
pip install -r requirements.txt
pip install altair==6.0.0
```

3) Run the Streamlit app:

```powershell
streamlit run app.py
```

Notes: If using CMD, activate the venv with `.\.venv\Scripts\activate.bat`.

## 9. NEXT STEPS

Suggested/Planned enhancements:

1. Add an upload widget fallback so users can upload `members.xlsx` via the browser if local file is missing.
2. Add unit tests for `sheet_names()`, `get_sheet()`, `log_points()`, and `add_member()` append behavior.
3. Add a small visual preview of `event_attendance` and a way to view/rollback recent writes.
4. Add a badge/indicator near `Refresh Data` when new writes are pending refresh (UX improvement).
5. Pin `altair==6.0.0` in `requirements.txt` for reproducible installs.
6. Add CI to run tests and a `Dockerfile` for containerized deployment if desired.

---

If you want, I can (a) add the upload fallback now, (b) add unit tests for `log_points` and `save_data`, or (c) update `requirements.txt` to pin `altair==6.0.0` and other versions. Let me know which to do next.
