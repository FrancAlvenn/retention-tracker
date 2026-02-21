import streamlit as st
import pandas as pd
import altair as alt
import os
import tempfile
from typing import Dict, List
import random


# Danger threshold constant (points below this are considered "in danger")
DANGER_THRESHOLD = 20

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
# Leaderboard helpers & UI
# ----------------
def _clamp_points_series(points_series: pd.Series) -> pd.Series:
    """Return a copy of the series coerced to int and clamped to >= 0 for display.

    Does not modify the source DataFrame.
    """
    pts = pd.to_numeric(points_series, errors="coerce").fillna(0).astype(int)
    pts = pts.clip(lower=0)
    return pts


def compute_leaderboard(df_members: pd.DataFrame, df_attendance: pd.DataFrame = None) -> pd.DataFrame:
    """Compute ranking, clamp negative points to 0, and count events attended.

    Returns a DataFrame with columns: `Rank`, `StudentID`, `Name`, `Points`, `EventsAttended`.
    Ranking rules: sort by Points desc, then Name asc. Strict sequential ranks (1..N).
    """
    if df_members is None or 'StudentID' not in df_members.columns or 'Name' not in df_members.columns:
        return pd.DataFrame(columns=['Rank', 'StudentID', 'Name', 'Points', 'EventsAttended'])

    df = df_members.copy()
    # ensure Points numeric and clamp for display
    df['Points_display'] = _clamp_points_series(df.get('Points', pd.Series(0)))

    # compute events attended if attendance sheet provided
    if df_attendance is None or 'StudentID' not in (df_attendance.columns if df_attendance is not None else []):
        events_count = pd.Series(0, index=df.index)
    else:
        # count occurrences of StudentID in attendance; coerce to str for matching
        att = df_attendance.copy()
        att['StudentID'] = att['StudentID'].astype(str)
        counts = att['StudentID'].value_counts()
        events_count = df['StudentID'].astype(str).map(counts).fillna(0).astype(int)

    df['EventsAttended'] = events_count

    # sort by Points_display desc then Name asc (alphabetical)
    df = df.assign(Name_str=df['Name'].astype(str))
    df = df.sort_values(by=['Points_display', 'Name_str'], ascending=[False, True]).reset_index(drop=True)

    # assign strict sequential ranks
    df['Rank'] = (df.index + 1).astype(int)

    result = df[['Rank', 'StudentID', 'Name', 'Points_display', 'EventsAttended']].copy()
    result = result.rename(columns={'Points_display': 'Points'})
    return result


def show_leaderboard(df_members: pd.DataFrame, df_attendance: pd.DataFrame = None) -> None:
    """Render the leaderboard UI: filters, Top-3 cards and ranked table for 4+.

    This function is self-contained and uses Streamlit display calls. It expects
    `df_members` (may be None) and optional `df_attendance` DataFrame.
    """
    st.subheader("Leaderboard")

    # Container so calling code can place this on the right side via columns
    container = st.container()

    # Filters and refresh button removed — show full leaderboard

    lb = compute_leaderboard(df_members, df_attendance)
    if lb.empty:
        container.info("Leaderboard unavailable: ensure `members` sheet has `StudentID`, `Name`, and `Points`.")
        return

    # Inject card CSS for equal heights and hover animation
    css = """
    <style>
    .lt-card { padding:12px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.08); transition: transform .18s ease, box-shadow .18s ease; min-height:120px; display:flex; flex-direction:column; justify-content:center; }
    .lt-card--gold { background:#FFF4B1; }
    .lt-card--silver { background:#F0F0F0; }
    .lt-card--bronze { background:#F7F3F2; }
    .lt-card:hover { transform: translateY(-6px); box-shadow:0 8px 20px rgba(0,0,0,0.12); }
    </style>
    """
    container.markdown(css, unsafe_allow_html=True)

    # show full leaderboard (no filters)
    filtered = lb.copy()

    # Top 3 cards
    top3 = filtered.head(3).reset_index(drop=True)
    if not top3.empty:
        card_cols = container.columns(min(3, len(top3)))
        badges = ['🥇', '🥈', '🥉']
        crowns = ['👑', '', '']
        classes = ['lt-card lt-card--gold', 'lt-card lt-card--silver', 'lt-card lt-card--bronze']
        for i in range(len(top3)):
            row = top3.loc[i]
            with card_cols[i]:
                rank = row['Rank']
                name = row['Name']
                pts = int(row['Points'])
                badge = badges[i]
                crown = crowns[i]
                cls = classes[i] if i < len(classes) else 'lt-card'
                title_html = f"<div class='{cls}'>\n<h3 style='margin:0'>{badge} {crown} {name}</h3>\n<p style='margin:4px 0;font-weight:600'>{pts} pts</p>\n</div>"
                st.markdown(title_html, unsafe_allow_html=True)

    # Remaining members (4+)
    remaining = filtered[filtered['Rank'] >= 4].copy()
    if remaining.empty:
        container.info("Less than 4 members after filtering.")
        return

    # show styled table: Rank, Name, Points, Events Attended
    display = remaining[['Rank', 'Name', 'Points', 'EventsAttended']].copy()
    display = display.reset_index(drop=True)
    container.markdown("**Other Members**")
    container.dataframe(display, use_container_width=True)


def show_in_danger_members(df_members: pd.DataFrame) -> None:
    """Show members whose Points are below DANGER_THRESHOLD.

    - Reads `df_members` only
    - Coerces Points to numeric, clamps negatives to 0
    - Shows top-3 lowest as horizontal cards with sad badges
    - Shows remaining in a table with conditional styling
    - Displays encouragement tips below
    """
    st.subheader("In Danger Members")

    if df_members is None or 'Name' not in df_members.columns:
        st.info("No members data available.")
        return

    # Prepare DataFrame safely
    df = df_members.copy()
    df['Points_display'] = pd.to_numeric(df.get('Points', pd.Series(0)), errors='coerce').fillna(0).astype(int)
    df['Points_display'] = df['Points_display'].clip(lower=0)

    # Filter below threshold
    danger = df[df['Points_display'] < DANGER_THRESHOLD].copy()
    if danger.empty:
        st.success("No members under the danger threshold. Great job!")
        return

    # sort ascending (lowest first)
    danger = danger.sort_values('Points_display', ascending=True).reset_index(drop=True)

    # CSS for cards and table highlight
    css = """
    <style>
    .id-card { padding:12px; border-radius:10px; background:linear-gradient(180deg,#fff6f6,#fff0f0); box-shadow:0 4px 12px rgba(255,120,90,0.06); }
    .id-card h3 { margin:0 0 4px 0; }
    .id-card p { margin:0; font-weight:600; }
    .id-badges { font-size:20px; margin-right:6px }
    .id-table .stDataFrame tbody td { color:#b91c1c; }
    .encourage { padding:12px; border-radius:8px; background:#f0f9ff; margin-top:12px }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # Top 3 lowest as cards
    top3 = danger.head(3).reset_index(drop=True)
    badges = ['😢 Lowest', '😟 Second lowest', '😞 Third lowest']
    if not top3.empty:
        cols = st.columns(min(3, len(top3)))
        for i in range(len(top3)):
            row = top3.loc[i]
            with cols[i]:
                name = str(row.get('Name', ''))
                pts = int(row.get('Points_display', 0))
                html = f"<div class='id-card'><h3><span class='id-badges'>{badges[i]}</span>{name}</h3><p>{pts} pts</p></div>"
                st.markdown(html, unsafe_allow_html=True)

    # Remaining members under threshold (if any beyond top3)
    remaining = danger.iloc[3:].copy()
    if not remaining.empty:
        st.markdown("**Other Members Needing Attention**")
        # show Name and Points only with conditional styling
        display = remaining[['Name', 'Points_display']].copy()
        display = display.rename(columns={'Points_display': 'Points'})
        # render dataframe; color achieved via CSS above targeting td
        st.dataframe(display.reset_index(drop=True), use_container_width=True)

    # Encouragement tips
    st.markdown("**Encouragement Tips**")
    st.markdown("""
    <div class='encourage'>
    <ul>
      <li>Every point is progress — keep going 💪</li>
      <li>You're closer than you think ✨</li>
      <li>Consistency beats intensity 📈</li>
      <li>Small wins matter 🏆</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)


def show_quick_stats(df_members: pd.DataFrame) -> None:
    """Display high-level quick stats and charts for the members sheet.

    - Uses `df_members` only
    - Coerces Points to numeric and clamps negatives to 0 for display
    - Shows responsive stat cards and Altair charts (histogram + top 10 bar)
    """
    st.subheader("Quick Stats")

    if df_members is None or df_members.empty:
        st.info("No members data available to generate quick stats.")
        return

    # Prepare safe Points series
    pts_series = pd.to_numeric(df_members.get('Points', pd.Series(dtype='float')), errors='coerce').fillna(0)
    pts_clamped = pts_series.clip(lower=0)

    total_members = len(df_members)
    total_points = int(pts_clamped.sum())
    avg_points = float(pts_clamped.mean()) if total_members > 0 else 0.0
    max_points = int(pts_clamped.max()) if total_members > 0 else 0
    min_points = int(pts_clamped.min()) if total_members > 0 else 0
    below_danger = int((pts_clamped < DANGER_THRESHOLD).sum())

    # Stat cards CSS (reuses visual language) — bigger cards, emoji, 3-per-row layout
    css = """
    <style>
    .qs-card { padding:18px; border-radius:12px; color:#071133; min-height:140px; display:flex; flex-direction:column; justify-content:center; align-items:flex-start; box-shadow:0 10px 30px rgba(10,20,40,0.06); }
    .qs-card h2{ margin:0; font-size:18px; display:flex; align-items:center; gap:10px }
    .qs-emoji { font-size:26px; margin-right:6px }
    .qs-figure { font-weight:800; font-size:22px; margin-top:8px }
    @media (max-width: 640px) { .qs-card { min-height:120px; } }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # Build styled stats with emoji and color accents
    stats = [
        { 'label': 'Total Members', 'value': total_members, 'emoji': '👥', 'bg': 'linear-gradient(90deg,#E6F0FF,#D7EDFF)' },
        { 'label': 'Total Points', 'value': total_points, 'emoji': '🏆', 'bg': 'linear-gradient(90deg,#FFF4B1,#FFE0A3)' },
        { 'label': 'Avg Points', 'value': f"{avg_points:.1f}", 'emoji': '📊', 'bg': 'linear-gradient(90deg,#F3E8FF,#EAD6FF)' },
        { 'label': 'Highest Points', 'value': max_points, 'emoji': '🚀', 'bg': 'linear-gradient(90deg,#E6FFF2,#CFFFE6)' },
        { 'label': 'Lowest Points', 'value': min_points, 'emoji': '⚠️', 'bg': 'linear-gradient(90deg,#FFEFEF,#FFDCDC)' },
    ]

    # Render cards in rows of up to 3
    for i in range(0, len(stats), 3):
        row = stats[i:i+3]
        cols = st.columns([1]*len(row))
        for col, s in zip(cols, row):
            with col:
                html = (
                    f"<div class='qs-card' style='background:{s['bg']};margin-bottom:12px'>"
                    f"<h2><span class='qs-emoji'>{s['emoji']}</span>{s['label']}</h2>"
                    f"<div class='qs-figure'>{s['value']}</div>"
                    f"</div>"
                )
                st.markdown(html, unsafe_allow_html=True)

    # Additional small stat below cards
    st.markdown(f"**Members below {DANGER_THRESHOLD} pts:** {below_danger}")

    # Charts section
    st.markdown("---")
    st.subheader("Points Distribution")

    # Build DataFrame for charts
    chart_df = pd.DataFrame({
        'Name': df_members.get('Name', pd.Series(['']*len(df_members))).astype(str),
        'Points': pts_clamped
    })

    # Histogram (Altair)
    try:
        hist = alt.Chart(chart_df).mark_bar().encode(
            alt.X('Points:Q', bin=alt.Bin(maxbins=30), title='Points'),
            y=alt.Y('count()', title='Count'),
            tooltip=[alt.Tooltip('count()')]
        ).properties(width='container', height=250)
        st.altair_chart(hist, use_container_width=True)
    except Exception:
        st.info('Unable to render histogram.')

    # Top 10 members bar chart
    st.subheader("Top 10 Members by Points")
    try:
        top10 = chart_df.groupby('Name', as_index=False)['Points'].sum().sort_values('Points', ascending=False).head(10)
        bar = alt.Chart(top10).mark_bar().encode(
            x=alt.X('Name:N', sort=top10['Name'].tolist(), title='Name'),
            y=alt.Y('Points:Q', title='Points'),
            tooltip=[alt.Tooltip('Name:N'), alt.Tooltip('Points:Q')]
        ).properties(width='container', height=320)
        st.altair_chart(bar, use_container_width=True)
    except Exception:
        st.info('Unable to render top members chart.')

    # Points spread insight (min/avg/max)
    st.markdown("**Points spread**")
    st.write(f"Min: {min_points} — Avg: {avg_points:.1f} — Max: {max_points}")


def show_member_profile(df_members: pd.DataFrame, df_attendance: pd.DataFrame) -> None:
    """Admin-style member profile view.

    - Select member by Name (disambiguate duplicates with StudentID)
    - Show Name, StudentID, Points, Rank, Events Attended
    - Small encouragement message and optional admin notes (UI-only)
    """
    st.subheader("Member Profile")

    if df_members is None or df_members.empty:
        st.info("No members data available.")
        return

    # prepare safe points and basic table
    df = df_members.copy()
    df['Points_display'] = pd.to_numeric(df.get('Points', pd.Series(0)), errors='coerce').fillna(0).astype(int).clip(lower=0)

    # Build selection options; handle duplicate names by appending StudentID
    options = []
    id_map = {}
    for idx, row in df.iterrows():
        name = str(row.get('Name', '')).strip()
        sid = str(row.get('StudentID', ''))
        label = name
        # if duplicate name exists or StudentID present, show disambiguator
        if df['Name'].astype(str).tolist().count(name) > 1 or sid:
            label = f"{name} — {sid}"
        options.append(label)
        id_map[label] = sid

    selected_label = st.selectbox("Select member", options)
    selected_sid = id_map.get(selected_label)

    # locate member row
    member_row = df[df['StudentID'].astype(str) == str(selected_sid)]
    if member_row.empty:
        # fallback: try match by name only
        name_only = selected_label.split(' — ')[0]
        member_row = df[df['Name'].astype(str) == name_only]
        if member_row.empty:
            st.error("Selected member not found.")
            return

    member = member_row.iloc[0]
    name = str(member.get('Name', ''))
    student_id = str(member.get('StudentID', ''))
    points = int(member.get('Points_display', 0))

    # compute rank using existing leaderboard logic
    try:
        lb = compute_leaderboard(df_members, df_attendance)
        rank_row = lb[lb['StudentID'].astype(str) == str(student_id)]
        rank = int(rank_row.iloc[0]['Rank']) if not rank_row.empty else 'N/A'
    except Exception:
        rank = 'N/A'

    # compute events attended
    events = 0
    if df_attendance is not None and 'StudentID' in df_attendance.columns:
        try:
            att = df_attendance.copy()
            att['StudentID'] = att['StudentID'].astype(str)
            events = int((att['StudentID'] == str(student_id)).sum())
        except Exception:
            events = 0

    # Styling for profile card (cute, colorful)
    css = """
    <style>
    .mp-card { padding:20px; border-radius:14px; box-shadow:0 12px 30px rgba(10,20,40,0.06); color:#071133; }
    .mp-name { font-size:24px; font-weight:900; margin:0 }
    .mp-sub { color:#475569; margin-top:6px }
    .mp-stats { display:flex; gap:12px; margin-top:14px; flex-wrap:wrap }
    .mp-stat { padding:12px 14px; border-radius:10px; background:rgba(255,255,255,0.9); box-shadow:0 6px 18px rgba(10,20,40,0.03); min-width:120px }
    .mp-rank { font-size:18px; font-weight:800 }
    .mp-points { font-size:22px; font-weight:900 }
    .mp-emoji { font-size:34px; margin-right:12px }
    .mp-message { margin-top:12px; padding:10px 12px; border-radius:10px; background:#fff8f0 }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # Choose visual accent based on performance
    if isinstance(rank, int) and rank <= 3:
        accent_bg = 'linear-gradient(90deg,#FFF4B1,#FFECB3)'
        accent_emoji = '🏆'
    elif points < DANGER_THRESHOLD:
        accent_bg = 'linear-gradient(90deg,#FFEFEF,#FFDCDC)'
        accent_emoji = '⚠️'
    else:
        accent_bg = 'linear-gradient(90deg,#E6F7FF,#DFF6FF)'
        accent_emoji = '🙂'

    # Randomized messages
    low_msgs = [
        "Keep going — every point counts! 💪",
        "Small steps, big progress — you got this! ✨",
        "Consistency beats intensity — focus on today. 🌱",
    ]
    top_msgs = [
        "Amazing work — you're leading the pack! 🎉",
        "Top performer — keep shining! 🌟",
        "You're setting the standard — incredible! 🏆",
    ]
    neutral_msgs = [
        "Steady progress — keep it up! 💪",
        "You're making progress — stay consistent. 🚀",
        "Nice work — small wins add up! 🏅",
    ]

    if isinstance(rank, int) and rank <= 3:
        message = random.choice(top_msgs)
    elif points < DANGER_THRESHOLD:
        message = random.choice(low_msgs)
    else:
        message = random.choice(neutral_msgs)

    # Top profile card (single full-width cute card)
    html = (
        f"<div class='mp-card' style='background:{accent_bg}'>"
        f"<div style='display:flex;align-items:center;gap:14px'>"
        f"<div style='width:72px;height:72px;border-radius:50%;background:rgba(255,255,255,0.7);display:flex;align-items:center;justify-content:center;font-size:34px'>👤</div>"
        f"<div>"
        f"<div class='mp-name'>{accent_emoji} {name}</div>"
        f"<div class='mp-sub'>StudentID: {student_id}</div>"
        f"</div></div>"
        f"<div class='mp-stats'>"
        f"<div class='mp-stat'><div class='mp-points'>{points}</div><div>Points</div></div>"
        f"<div class='mp-stat'><div class='mp-rank'>{rank}</div><div>Rank</div></div>"
        f"<div class='mp-stat'><div class='mp-rank'>{events}</div><div>Events Attended</div></div>"
        f"</div>"
        f"<div class='mp-message'>{message}</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

    # Encouragement / notes
    if points < DANGER_THRESHOLD:
        st.info("Keep going — small consistent steps make a difference. Reach out for support if needed.")
    elif isinstance(rank, int) and rank <= 3:
        st.success("Top performer — great work! 🎉")
    else:
        st.write("Steady progress — keep pushing! 💪")

    st.markdown("---")
    st.text_area("Admin notes (UI-only)", value="", height=120)


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

    # Sidebar navigation: split functionality into pages to reduce crowding
    pages = [
        "Overview",
        "Leaderboard",
        "In Danger Members",
        "Quick Stats",
        "Member Profile",
        "Members",
        "Log Points",
        "Add Member",
        "Create Event",
    ]
    # show all navigation options in the sidebar as a list (radio) instead of a dropdown
    page = st.sidebar.radio("Navigate", pages)

    # Prepare members and attendance DataFrames
    df_members = data.get('members') if data is not None else None
    df_attendance = data.get('event_attendance') if data is not None else None

    # Render the selected page (full-width)
    if page == "Overview":
        st.header("Overview")
        if df_members is not None:
            show_top_members_chart(df_members)
        if "members" in sheets:
            st.subheader("Members (preview)")
            display_df = df_members.copy()
            if 'ID' in display_df.columns:
                display_df = display_df.drop(columns=['ID'])
            st.dataframe(display_df)

    elif page == "Leaderboard":
        show_leaderboard(df_members, df_attendance)

    elif page == "Quick Stats":
        df = df_members
        show_quick_stats(df)

    elif page == "Member Profile":
        df = df_members
        show_member_profile(df, df_attendance)

    elif page == "Members":
        default_index = sheets.index("members") if "members" in sheets else 0
        sheet = st.selectbox("Select sheet", sheets, index=default_index)
        df = get_sheet(data, sheet)
        display_df = df.copy()
        if sheet == "members" and 'ID' in display_df.columns:
            display_df = display_df.drop(columns=['ID'])
        st.dataframe(display_df)

    elif page == "Log Points":
        # operate on members sheet
        df = df_members
        df = add_points_form(df)

    elif page == "Add Member":
        df = df_members
        df = add_member(df)

    elif page == "In Danger Members":
        df = df_members
        show_in_danger_members(df)

    elif page == "Create Event":
        df = df_members
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



