# Handover: Retention Tracker (Streamlit)

## 1. PROJECT SUMMARY

This is a minimal Streamlit application that loads member data from an Excel file (`data/members.xlsx`) and displays selected sheets. The app currently exposes a single dashboard entrypoint (`show_dashboard()`) which presents a sheet selector and renders the chosen sheet as a table. It is intentionally small so a new engineer or an AI assistant can extend it (upload, visualization, processing).

## 2. TECH STACK (exact versions from the dev environment)

- Python: 3.14.0
- streamlit: 1.54.0
- pandas: 2.3.3
- openpyxl: 3.1.5
- numpy: 2.4.2 (available in environment)
- pyarrow: 23.0.1 (available in environment)

The repository also includes `requirements.txt` (minimal runtime reqs):

- `streamlit>=1.0`
- `pandas`
- `openpyxl`

Install commands (exact):

```bash
python -m venv .venv
# PowerShell activate
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run command:

```bash
streamlit run app.py
```

## 3. FILE STRUCTURE

- [app.py](app.py): Single-file application. Contains three internal layers (Data, Logic, Interface) implemented as functions and the `show_dashboard()` interface entrypoint.
- [requirements.txt](requirements.txt): Minimal dependencies for the app.
- [README.md](README.md): Short run instructions (local dev).
- [.gitignore](.gitignore): Typical Python / venv / Streamlit ignores.
- [data/members.xlsx](data/members.xlsx): Excel data file with two sheets: `members` and `event_attendance`.
- [archive/app_v1.py](archive/app_v1.py): Older working version (do not edit).
- [archive/app_v2.py](archive/app_v2.py): Older working version (do not edit).
- [handover_doc/handover.md](handover_doc/handover.md): This document.

Notes: The `env/` virtual environment is present in the workspace but should not be checked into source control; it is ignored via `.gitignore`.

## 4. DATA STRUCTURES

Source Excel: `data/members.xlsx` contains two sheets and the exact column names and types (in the current dataset):

- Sheet `members`:
  - `StudentID`: integer (pandas dtype int64)
  - `Name`: string/object
  - `Points`: integer (pandas dtype int64)

- Sheet `event_attendance`:
  - `Event`: string/object
  - `StudentID`: integer (pandas dtype int64)

Exact variable names used in `app.py` (top-level functions and important runtime vars):

- Functions:
  - `load_data(path: str = "data/members.xlsx")`  # data layer
  - `sheet_names(data: Dict[str, pd.DataFrame])`   # logic layer
  - `get_sheet(data: Dict[str, pd.DataFrame], name: str)`  # logic layer
  - `show_dashboard()`  # interface layer (Streamlit entrypoint)

- Runtime variables inside `show_dashboard()`:
  - `data` (dict[str, DataFrame]) — the result of `load_data()`
  - `sheets` (list[str]) — list of sheet names from `sheet_names(data)`
  - `default_index` (int) — index of default selected sheet (prefers `members`)
  - `sheet` (str) — currently selected sheet name from `st.selectbox`
  - `df` (DataFrame) — DataFrame returned by `get_sheet(data, sheet)` and rendered via `st.dataframe`

There are no persistent global DataFrame variables (e.g., `df_members`) — data lives in the local `data`/`df` variables returned and used at runtime.

## 5. FEATURES IMPLEMENTED

1. Excel loader (all sheets)
   - Implemented by: `load_data(path)` (data layer)
   - Behavior: uses `pandas.read_excel(..., sheet_name=None, engine='openpyxl')` to return a dict of DataFrames.
   - Constraints / decisions: expects `data/members.xlsx` to exist. No upload fallback implemented.

2. Sheet listing and selection
   - Implemented by: `sheet_names(data)` (logic) + `st.selectbox` inside `show_dashboard()` (interface)
   - Behavior: shows available sheet names; defaults to sheet named `members` if present.

3. Sheet display
   - Implemented by: `get_sheet(data, name)` (logic) + `st.dataframe(df)` inside `show_dashboard()` (interface)
   - Behavior: renders the chosen sheet as a table.

4. Encapsulation into 3 internal layers (Data, Logic, Interface)
   - Implemented by: function separation inside `app.py`. The interface layer (`show_dashboard`) only calls Streamlit functions and the defined data/logic functions.

## 6. BUGS FIXED (this session)

- Consolidated and refactored code so the Streamlit UI is separated from data I/O. Previously the UI and data loader were mixed directly in the top-level of `app.py`; now:
  - `load_data()` performs only data I/O and does not call Streamlit.
  - `show_dashboard()` performs only Streamlit UI actions and calls the data/logic functions.
- Adjusted default Excel path from `members.xlsx` (project root) to `data/members.xlsx` to match the repository layout. This avoids a common file-not-found error if the Excel file is kept under `data/`.

There were no other functional bugs discovered and fixed in this session beyond the refactor and path correction.

## 7. DECISIONS MADE

- Single-file policy: All code was kept inside `app.py` (per request). This keeps onboarding simple (one entry point) and avoids cross-file imports for now.
- Minimal surface area: The app intentionally implements only reading and displaying sheets. I did not add upload widgets, persistence, visualizations, or business logic because the user asked for a minimal loader and a clear layer separation. These can be added later.
- Use `openpyxl` engine: Chosen for `.xlsx` compatibility and because it is already available in the environment.
- Default sheet selection: If present, `members` is chosen by default for convenience.

Decisions explicitly NOT built (and why):

- No file upload fallback UI: The app currently errors if `data/members.xlsx` is missing. I avoided adding upload UI to keep the interface minimal and to follow the user's instruction to keep functionality in `app.py` only.
- No data validation / strict typing: The app currently renders raw DataFrames without validation or casting. This keeps the loader simple; validation is a recommended next step.

## 8. RUN COMMANDS (exact)

1. Create virtual environment and activate (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install requirements:

```powershell
pip install -r requirements.txt
```

3. Run the Streamlit app:

```powershell
streamlit run app.py
```

If you prefer to run in CMD, use the `activate.bat` script instead of the PowerShell activation above.

## 9. NEXT STEPS

Planned/Recommended work that was not implemented in this session:

1. Add an upload widget fallback so users can supply `members.xlsx` via the browser when the file is not present.
2. Implement basic data validation/typing and helper functions in the logic layer (e.g., `df_members = get_sheet(data,'members')` then validate types and missing values).
3. Add small visualizations (member points distribution, attendance per event) inside `show_dashboard()` using `st.bar_chart` / `st.line_chart`.
4. Add unit tests for `sheet_names()` and `get_sheet()`.
5. Add `README.md` expansion and a `requirements.txt` with pinned versions (e.g., `streamlit==1.54.0`, `pandas==2.3.3`, `openpyxl==3.1.5`) if deterministic installs are required.
6. (Optional) Create a `Dockerfile` for container deployment or push the repo to GitHub and enable Streamlit Community Cloud deploy.

