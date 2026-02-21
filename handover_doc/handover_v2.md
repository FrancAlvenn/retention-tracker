# Handover: Retention Tracker (Streamlit) — v2

## 1. PROJECT SUMMARY

This is a small Streamlit application that loads member data from an Excel file (`data/members.xlsx`) and displays selected sheets. The UI exposes a sheet selector and renders the chosen sheet as a table. Additionally, the dashboard now shows a bar chart of the top-10 members by `Points` (descending). The code is organized into three layers inside a single file: Data, Logic, and Interface.

## 2. TECH STACK (exact)

- Python: 3.14.0
- streamlit: 1.54.0
- pandas: 2.3.3
- openpyxl: 3.1.5
- numpy: 2.4.2
- pyarrow: 23.0.1
- altair: 6.0.0

Note: `requirements.txt` in the repo lists minimal runtime dependencies (`streamlit`, `pandas`, `openpyxl`). After the chart addition, add `altair==6.0.0` to your environment if it's not already installed.

## 3. FILE STRUCTURE

- `app.py`: Single-file Streamlit application; contains three internal layers (Data, Logic, Interface). Entry point is `show_dashboard()` and the file is runnable via `streamlit run app.py`.
- `requirements.txt`: Minimal runtime requirements for the app.
- `README.md`: Short run instructions (local dev).
- `data/` directory: Contains `members.xlsx` (source data used at runtime).
- `data/members.xlsx`: Excel workbook with two sheets: `members` and `event_attendance` (see Data Structures section).
- `archive/app_v1.py` and `archive/app_v2.py`: Older working versions (kept for reference; do not edit).
- `handover_doc/handover_v1.md`: Previous handover (v1).
- `handover_doc/handover_v2.md`: This document (v2).
- `env/`: Local Python virtual environment (present in this workspace but should be gitignored).
- `__pycache__/`: Python bytecode cache.

## 4. DATA STRUCTURES

Excel workbook: `data/members.xlsx` — sheets and exact columns/types used by the app:

- Sheet `members`:
  - `StudentID` — integer (pandas dtype int64)
  - `Name` — string/object
  - `Points` — integer (pandas dtype int64)

- Sheet `event_attendance`:
  - `Event` — string/object
  - `StudentID` — integer (pandas dtype int64)

Exact function and runtime variable names in `app.py`:

- Functions (top-level):
  - `load_data(path: str = "data/members.xlsx")`  # data layer — returns Dict[str, pd.DataFrame]
  - `sheet_names(data: Dict[str, pd.DataFrame])`   # logic layer — returns List[str]
  - `get_sheet(data: Dict[str, pd.DataFrame], name: str)`  # logic layer — returns a DataFrame
  - `show_top_members_chart(df: pd.DataFrame, top_n: int = 10)`  # interface helper — renders the top-N bar chart
  - `show_dashboard()`  # interface layer (Streamlit entrypoint)

- Runtime variables inside `show_dashboard()`:
  - `data` (dict[str, DataFrame]) — result of `load_data()`
  - `sheets` (list[str]) — result of `sheet_names(data)`
  - `default_index` (int) — preferred default selection index
  - `sheet` (str) — selected sheet name from `st.selectbox`
  - `df` (DataFrame) — DataFrame returned by `get_sheet(data, sheet)` and rendered via `st.dataframe`

- Variables inside `show_top_members_chart()`:
  - `top_n` (int) — number of members to show (default 10)
  - `top` (DataFrame) — local DataFrame computed from `df[['Name','Points']]`, cleaned and sorted

There are no global DataFrame variables persisted across calls.

## 5. FEATURES IMPLEMENTED

1. Excel loader (all sheets)
   - Function: `load_data(path)`
   - Behavior: uses `pandas.read_excel(path, sheet_name=None, engine='openpyxl')` and returns a dict of DataFrames keyed by sheet name. It is cached with `@st.cache_data`.
   - Constraint: Expects `data/members.xlsx` to exist (no upload fallback implemented).

2. Sheet listing and selection
   - Functions: `sheet_names(data)` + the `st.selectbox` call inside `show_dashboard()`
   - Behavior: displays available sheet names and defaults to the sheet named `members` if present.

3. Sheet display
   - Function: `get_sheet(data, name)` + `st.dataframe(df)` in `show_dashboard()`
   - Behavior: renders the selected sheet as a table (no additional validation beyond presence of sheet).

4. Top-10 members bar chart (descending order)
   - Function: `show_top_members_chart(df, top_n=10)`
   - Behavior: extracts `Name` and `Points` from the selected DataFrame, coerces `Points` to numeric, drops invalid rows, sorts by `Points` descending, takes top-N, and renders a bar chart using Altair. The chart shows `Name` on the x-axis and `Points` on the y-axis and is explicitly ordered left-to-right in descending Points.
   - Constraints/Notes: The function requires the DataFrame to contain `Name` and `Points` columns. If either is missing or no valid rows exist, the function displays an info message and returns.

## 6. BUGS FIXED (this session)

1. Separated UI and data I/O
   - Problem: Previous versions mixed Streamlit UI calls and data I/O.
   - Fix: Refactored `app.py` so `load_data()` performs only data I/O (no Streamlit calls) and `show_dashboard()` handles UI and calls the data/logic functions.

2. Default Excel path corrected
   - Problem: The app previously expected `members.xlsx` in the project root, which caused common FileNotFoundError when the workbook is stored under `data/`.
   - Fix: `load_data()` default path is `data/members.xlsx`.

3. Chart ordering fixed
   - Problem: Initial chart rendering used a generic `st.bar_chart` which did not guarantee left-to-right descending order.
   - Fix: Added `show_top_members_chart()` that uses Altair with an explicit x-axis sort to ensure bars are ordered descending by `Points`.

## 7. DECISIONS MADE

- Single-file policy: Kept the app contained in `app.py` to simplify onboarding and avoid cross-file imports. This keeps the application small and easy to inspect.
- Layer separation: Code is organized into Data, Logic, and Interface layers via functions. This makes unit testing and future refactor easier.
- Use `openpyxl` engine: Chosen for reliable `.xlsx` reading and because it is available in the dev environment.
- Use Altair for charting: Altair was added to ensure deterministic sorting and to provide tooltip control. If you prefer to avoid the dependency, the chart can be simplified to `st.bar_chart()` but sorting control will be more limited.
- Minimal surface area: Deliberately avoided adding file upload UI, extensive validation, or persistent state. These were left out to keep the implementation focused and minimal.

Deliberately NOT built (and why):

- No file upload fallback: The app currently fails with a helpful error message if `data/members.xlsx` is missing. This keeps the UI minimal; an upload widget is a recommended next step.
- No full data validation / typing: The app performs light coercion on `Points` but does not enforce a schema; this reduces complexity for the MVP.
- No unit tests: None were added in this session, but tests for the logic functions are recommended.

## 8. RUN COMMANDS

1. Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

2. Install dependencies (recommended):

```powershell
pip install -r requirements.txt
pip install altair==6.0.0
```

3. Run the Streamlit app:

```powershell
streamlit run app.py
```

If you prefer CMD instead of PowerShell, use `.\\.venv\\Scripts\\activate.bat` to activate.

## 9. NEXT STEPS

Planned or recommended enhancements:

1. Add an upload widget fallback to `show_dashboard()` so users can upload `members.xlsx` via the browser when the file is missing.
2. Add data validation and column-type enforcement for `members` sheet (explicit schema checks, better error messages).
3. Add unit tests for `sheet_names()` and `get_sheet()` and small tests for the `show_top_members_chart()` data-prep logic (e.g., ensure sorting and top-N behavior).
4. Add small visualizations: points distribution, attendance per event, etc., reusing the logic layer.
5. Optionally update `requirements.txt` to pin `altair==6.0.0` and other versions used here for reproducible installs.
6. Add a CI job to run tests and a `Dockerfile` for deployment if desired.

## APP CHANGES IN THIS SESSION

- `app.py`:
  - Added `show_top_members_chart(df: pd.DataFrame, top_n: int = 10)` that computes and renders the top-N members bar chart (Altair) and handles missing/invalid data gracefully.
  - Imported `altair as alt` and called `show_top_members_chart(df)` from `show_dashboard()` below `st.dataframe(df)` so the chart appears under the table.

---

If you want, I can also (a) add a small unit test for the chart's data-prep, (b) update `requirements.txt` to include `altair==6.0.0`, or (c) implement the upload fallback before you close this session.
