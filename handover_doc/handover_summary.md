# Retention Tracker — Handover Summary

**File attached:** app.py

**1) What the app does (one paragraph)**

This Streamlit app loads a workbook (`data/members.xlsx`) and provides a lightweight members management dashboard. It shows leaderboards, charts, quick statistics, an "in danger" view for low-scoring members, and per-member profile pages. The UI allows adding members, logging points, and creating event attendance entries; saves are written back to the same Excel workbook. The app is intentionally simple, file-based (Excel) and targeted at small teams or classes where a spreadsheet backend is acceptable.


**2) Data structure: `members.xlsx` (expected sheets, columns, and types)**

The app reads/writes the workbook using pandas + openpyxl. The code expects the following sheets (case-sensitive names used in code):

- `members` (primary sheet) — expected columns:
  - `StudentID` (string) — unique identifier for a student; code treats it as string when matching but sometimes attempts numeric parsing to auto-generate IDs.
  - `Name` (string) — student display name.
  - `Points` (integer / numeric) — points balance; code coerces to numeric, treats NaN as 0 and clamps negatives to 0 for display.
  - `ID` (optional) — present in some files; code strips it for preview but doesn't depend on it.
  - Any additional columns are preserved when writing back, but UI displays and logic use only the columns above.

- `event_attendance` (optional) — expected columns:
  - `Event` (string) — event name.
  - `StudentID` (string) — StudentID referencing `members.StudentID` for attendance counts.

Notes:
- The app will read any other sheets present and preserve them when writing, but features depend on the two sheets above. If `members` is missing the app will show an error/info message.
- Column types are coerced at runtime: `Points` -> numeric (NaN -> 0), `StudentID` -> str for matching/counting.


**3) Three-tier architecture (functions grouped by tier and what each does)**

Data layer (I/O with the workbook)
- `load_data(path="data/members.xlsx")` — reads the entire workbook (`sheet_name=None`) via pandas and returns a dict of DataFrames; cached with `@st.cache_data`.
- `save_data(df_members, path="data/members.xlsx")` — rewrites the workbook preserving other sheets; writes `members` DataFrame to the workbook using a temporary file then `os.replace` for atomic replace; raises permission errors if the file is locked.
- `save_attendance(df_attendance, path="data/members.xlsx", extra_sheets=None)` — similar to `save_data` but updates/creates `event_attendance` and optionally includes `extra_sheets` (e.g., current `members`) so writes preserve other sheets.

Logic layer (pure data/transformations; minimal/no Streamlit calls)
- `sheet_names(data)` — returns list of sheet names from `load_data` result.
- `get_sheet(data, name)` — simple accessor returning a sheet DataFrame.
- `_clamp_points_series(points_series)` — coerce to numeric, fillna(0), cast to int and clip lower bound 0; used for safe display values.
- `compute_leaderboard(df_members, df_attendance=None)` — builds ranking DataFrame: clamps points, computes events attended (if `df_attendance` provided), sorts Desc by points then Name, assigns strict sequential ranks, returns DataFrame with `Rank, StudentID, Name, Points, EventsAttended`.
- `log_points(df_members, student_id, pts)` — pure operation that finds rows matching `StudentID` (string compare), coerces Points to numeric for matched rows, adds pts and updates the DataFrame (returns (df_members, True/False) indicating success).

Interface layer (Streamlit UI, pages, and forms)
- `show_top_members_chart(df)` — Altair bar chart of top-N members by Points.
- `show_leaderboard(df_members, df_attendance)` — UI page showing top-3 cards and a table for others (styled cards via injected CSS).
- `add_points_form(df_members)` — Streamlit form for logging points; on submit calls `log_points` and `save_data` and sets session flag.
- `add_member(df_members)` — Form to add a new member; validates inputs, auto-generates numeric StudentID when blank, appends row and calls `save_data`.
- `create_event_form(df_members)` — Form to create an event and append rows to `event_attendance` (calls `save_attendance` and preserves `members` sheet via `extra_sheets`).
- `show_in_danger_members(df_members)` — page showing members below `DANGER_THRESHOLD` with sad badges, cards and encouragement tips.
- `show_quick_stats(df_members)` — quick stats dashboard: cards for totals and averages, Altair histogram and top-10 bar chart.
- `show_member_profile(df_members, df_attendance)` — single-member admin-style profile view; select member (disambiguates duplicates by showing `Name — StudentID` label), shows points, computed rank, events attended, encouragement and admin notes (UI only).
- `show_dashboard()` — orchestrates sidebar navigation, loads data using `load_data()`, prepares `df_members` and `df_attendance`, and routes to the pages above.


**4) All current features and how to use them (step-by-step)**

Prerequisite: place `members.xlsx` at `data/members.xlsx` (or create it) with at least a `members` sheet containing the columns described above. Optionally add `event_attendance` sheet.

When you run the app it shows a sidebar navigation with the following pages:

- Overview
  - Shows an Altair bar chart of top members by Points and a preview of the `members` sheet.

- Leaderboard
  - Shows Top-3 members as cards (gold/silver/bronze) and a table of other members with Rank, Name, Points, EventsAttended. Previously filter controls were removed; page shows full leaderboard. Use it to quickly see ranked members.

- In Danger Members
  - Highlights members with Points < `DANGER_THRESHOLD` (default 20). Shows three lowest cards with sad badges and a table of remaining low members. Encouragement tips are displayed below.

- Quick Stats
  - Shows big, emoji-styled stat cards: Total Members, Total Points, Average Points, Highest, Lowest. Shows a histogram (Points distribution) and Top-10 bar chart. Also shows members below the danger threshold.

- Member Profile
  - Select a member from a `selectbox` (Name — StudentID label). Shows a single profile card with emoji accent, Points, Rank (computed from `compute_leaderboard`), Events Attended (counts from `event_attendance`), randomized encouraging/congratulatory message, and an admin notes text area (UI-only, not persisted).

- Members
  - Select any sheet present in the workbook (defaults to `members`) and preview it in a DataFrame viewer (drops `ID` column for `members` preview if present).

- Log Points
  - Form to add points to a student by StudentID. On submit, the app updates the in-memory DataFrame, calls `save_data` to persist to Excel, and prompts to "Refresh Data".

- Add Member
  - Form to add a new member. Validates StudentID and Name, optionally auto-generates StudentID when left blank, and persists via `save_data`.

- Create Event
  - Form to create an event by selecting attendee names; resolves names to StudentIDs and appends rows to `event_attendance` (persisted via `save_attendance`).

Important UI notes:
- When saving to Excel, if the workbook is open in Excel the save may fail with a PermissionError and the app surfaces this with a helpful message.
- When changes are saved, you may need to click the app-level `Refresh Data` button to clear the cache and reload the workbook.


**5) Exact terminal command to run the app**

From the repository root (where `app.py` lives) run:

```bash
streamlit run app.py
```

(If you are using the included virtual environment in `env/`, first activate it.)

Optional setup commands (one-time):

```bash
# create/activate a venv (if you don't use the provided env/)
python -m venv env
# Windows PowerShell
env\Scripts\Activate.ps1
# install deps
pip install -r requirements.txt
# then run
streamlit run app.py
```


**6) Three features to add next (with which tier each belongs to)**

- Audit Log & Undo (Data + Logic): track every points modification / member create / event create in an `audit_log` sheet with timestamp, actor, diff; implement an undo operation for the last action. (Data/Logic tier)
- Authentication & Role-Based UI (Interface + Logic): add a simple login (username/password) and an admin role to protect add/edit/save operations; adjust UI to show/hide admin forms. (Interface + Logic tier)
- Export / Scheduled Reports (Interface + Data): add a "Generate report" option to export CSV/PDF summaries or an automated scheduled email/report job that writes to `reports/` or sends via SMTP. (Interface + Data tier)


**7) Known limitations or edge cases**

- Workbook locking: saving will fail with PermissionError if `data/members.xlsx` is open in Excel — user must close it.
- Concurrency: no optimistic locking — simultaneous writes from multiple users/processes will cause last-writer-wins and may corrupt data.
- StudentID data types: code treats `StudentID` as string for matching but sometimes attempts to generate numeric IDs by parsing existing IDs; mixed types may produce odd auto-generated IDs.
- Duplicate names: UI attempts to disambiguate by showing `Name — StudentID` when duplicates exist, but some pages (e.g. attendee selection by Name) could still resolve multiple matches and will append all matching StudentIDs; be careful with duplicate names.
- Cache behavior: `load_data` is cached via `@st.cache_data`; after saving, the app attempts to call `st.cache_data.clear()` in places but behavior may vary by Streamlit version — you may need to use the app "Refresh Data" button or restart the app to force a fresh read.
- Styling injection: custom CSS/JS that manipulates the Streamlit DOM is brittle — future Streamlit versions may change DOM structure or attributes (e.g., `data-testid`) and the injected scripts may stop working.
- No authentication or persistence for admin notes: notes in `show_member_profile` are UI-only and not saved to disk.
- Large datasets: the app is not optimized for very large member lists; Altair charts and DataFrame viewers may become slow with thousands of rows.
- Error handling: many operations wrap writes in broad try/except and display the exception to the UI; some parsing/edge errors may be swallowed or presented as generic failures.


——

Local file created in this repo:
- `handover_doc/handover_summary.md` (this file)

If you want, I can also:
- Add an example `data/members.xlsx` with sample rows so a fresh checkout can run the app immediately.
- Produce a short `README.md` with the run steps and dependency notes.


Prepared so you can paste into a fresh AI session and pick up where you left off.