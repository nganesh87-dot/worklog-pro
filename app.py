import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import uuid
import os
from io import BytesIO
from sqlalchemy import create_engine, text

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="WorkLog Pro",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================================================
# DATABASE CONFIG
# ==================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL is not configured. Please add it in Render environment variables.")
    st.stop()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# ==================================================
# DATABASE INIT
# ==================================================
def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS timelog (
                id TEXT PRIMARY KEY,
                entry_date DATE,
                start_time TEXT,
                end_time TEXT,
                hours NUMERIC,
                client TEXT,
                task TEXT,
                remarks TEXT,
                billable TEXT,
                created_at TIMESTAMP
            )
        """))

init_db()

# ==================================================
# HELPERS
# ==================================================
def calculate_hours(start_time, end_time):
    try:
        s = datetime.strptime(start_time, "%H:%M")
        e = datetime.strptime(end_time, "%H:%M")
        diff = (e - s).total_seconds() / 3600
        return round(diff, 2) if diff > 0 else 0
    except:
        return 0

def insert_entry(entry_date, start_time, end_time, hours, client, task, remarks, billable):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO timelog (
                id, entry_date, start_time, end_time, hours, client, task, remarks, billable, created_at
            ) VALUES (
                :id, :entry_date, :start_time, :end_time, :hours, :client, :task, :remarks, :billable, :created_at
            )
        """), {
            "id": str(uuid.uuid4()),
            "entry_date": str(entry_date),
            "start_time": start_time,
            "end_time": end_time,
            "hours": float(hours),
            "client": client,
            "task": task,
            "remarks": remarks,
            "billable": billable,
            "created_at": datetime.now()
        })

def delete_entry(row_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM timelog WHERE id = :id"), {"id": row_id})

def fetch_entries():
    return pd.read_sql("SELECT * FROM timelog ORDER BY entry_date DESC, start_time DESC", engine)

def format_hours(val):
    try:
        return f"{float(val):.2f}"
    except:
        return "0.00"

def safe_text(x):
    if pd.isna(x):
        return ""
    return str(x)

def to_datetime_safe(series):
    return pd.to_datetime(series, errors="coerce")

def dataframe_to_excel_bytes(df_export, sheet_name="WorkLog"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.getvalue()

# ==================================================
# SESSION STATE (APP STATE)
# ==================================================
defaults = {
    "session_running": False,
    "session_paused": False,
    "session_mode": "AUTO",
    "session_client": "",
    "session_task": "",
    "session_remarks": "",
    "session_billable": "Yes",
    "session_interval": 60,
    "session_start": None,
    "block_start": None,
    "last_logged": "—"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==================================================
# PREMIUM BLUE STYLING
# ==================================================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

html, body, [class*="css"] {
    font-family: Arial, Helvetica, sans-serif;
}

.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1500px;
}

.main {
    background:
        radial-gradient(circle at top left, rgba(191,219,254,0.85), transparent 25%),
        radial-gradient(circle at top right, rgba(147,197,253,0.60), transparent 22%),
        linear-gradient(180deg, #eaf3ff 0%, #f6fbff 100%);
}

.hero {
    background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(239,246,255,0.95));
    border: 1px solid rgba(96,165,250,0.16);
    border-radius: 28px;
    padding: 28px 30px 24px 30px;
    box-shadow: 0 22px 50px rgba(30,64,175,0.10);
    margin-bottom: 1.2rem;
}

.hero-title {
    font-size: 2.25rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.12;
    letter-spacing: -0.9px;
    margin-bottom: 0.4rem;
}

.hero-sub {
    color: #475569;
    font-size: 0.98rem;
    line-height: 1.75;
    max-width: 1050px;
}

.section-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(248,252,255,0.98));
    border: 1px solid rgba(96,165,250,0.14);
    border-radius: 24px;
    padding: 22px 22px 18px 22px;
    box-shadow: 0 14px 35px rgba(37,99,235,0.08);
    margin-bottom: 1rem;
}

.card-title {
    font-size: 1.18rem;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 0.35rem;
    letter-spacing: -0.3px;
}

.card-sub {
    color: #64748b;
    font-size: 0.92rem;
    margin-bottom: 1rem;
    line-height: 1.7;
}

.kpi {
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(239,246,255,0.98) 100%);
    border: 1px solid rgba(96,165,250,0.16);
    border-radius: 22px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 12px 28px rgba(37,99,235,0.08);
    min-height: 128px;
}

.kpi-label {
    color: #1d4ed8;
    font-size: 0.80rem;
    text-transform: uppercase;
    letter-spacing: 0.55px;
    margin-bottom: 10px;
    font-weight: 800;
}

.kpi-value {
    font-size: 1.85rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.1;
    letter-spacing: -0.7px;
}

.kpi-note {
    color: #64748b;
    font-size: 0.8rem;
    margin-top: 10px;
}

.timer-box {
    background: linear-gradient(135deg, rgba(219,234,254,0.82) 0%, rgba(255,255,255,0.96) 100%);
    border: 1px solid rgba(59,130,246,0.20);
    border-radius: 24px;
    padding: 24px;
    min-height: 235px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}

.timer-big {
    font-size: 2.7rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -1px;
    margin-bottom: 0.3rem;
}

.status-pill {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(37,99,235,0.12);
    color: #1d4ed8;
    font-size: 0.8rem;
    font-weight: 800;
    margin-bottom: 0.9rem;
}

.small-muted {
    color: #475569;
    font-size: 0.9rem;
    line-height: 1.8;
}

.activity-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(239,246,255,0.96) 100%);
    border: 1px solid rgba(96,165,250,0.14);
    border-radius: 20px;
    padding: 16px 18px;
    box-shadow: 0 10px 24px rgba(37,99,235,0.06);
    margin-bottom: 0.8rem;
}

.activity-top {
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 0.25rem;
}

.activity-sub {
    color: #64748b;
    font-size: 0.88rem;
    line-height: 1.7;
}

.pill {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(37,99,235,0.12);
    color: #1d4ed8;
    font-size: 0.76rem;
    font-weight: 800;
    margin-top: 0.6rem;
}

.pill-no {
    background: rgba(245,158,11,0.14);
    color: #b45309;
}

div[data-testid="stDataFrame"] {
    border-radius: 18px !important;
    overflow: hidden !important;
}

.stButton > button {
    border-radius: 14px !important;
    font-weight: 800 !important;
    padding: 0.64rem 1rem !important;
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 8px 18px rgba(37,99,235,0.20) !important;
}

.stDownloadButton > button {
    border-radius: 14px !important;
    font-weight: 800 !important;
    padding: 0.64rem 1rem !important;
    background: linear-gradient(135deg, #0ea5e9, #2563eb) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 8px 18px rgba(14,165,233,0.18) !important;
}

.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stDateInput input {
    border-radius: 14px !important;
    border: 1px solid rgba(96,165,250,0.18) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    margin-bottom: 0.6rem;
    overflow-x: auto;
}

.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.86);
    border: 1px solid rgba(96,165,250,0.16);
    border-radius: 14px;
    padding: 10px 18px;
    font-weight: 800;
    color: #1e3a8a;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border-color: #2563eb !important;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# LOAD DATA
# ==================================================
df = fetch_entries()
if not df.empty:
    df["hours"] = pd.to_numeric(df["hours"], errors="coerce").fillna(0)
    df["entry_date"] = to_datetime_safe(df["entry_date"])
else:
    df = pd.DataFrame(columns=[
        "id", "entry_date", "start_time", "end_time", "hours",
        "client", "task", "remarks", "billable", "created_at"
    ])

today = pd.Timestamp(date.today())
this_month = today.strftime("%Y-%m")

today_df = df[df["entry_date"] == today] if not df.empty else pd.DataFrame()
week_df = df[df["entry_date"] >= (today - pd.Timedelta(days=6))] if not df.empty else pd.DataFrame()
month_df = df[df["entry_date"].dt.strftime("%Y-%m") == this_month] if not df.empty else pd.DataFrame()

total_hours = df["hours"].sum() if not df.empty else 0
billable_hours = df[df["billable"] == "Yes"]["hours"].sum() if not df.empty else 0
today_hours = today_df["hours"].sum() if not today_df.empty else 0
today_billable = today_df[today_df["billable"] == "Yes"]["hours"].sum() if not today_df.empty else 0
week_hours = week_df["hours"].sum() if not week_df.empty else 0
month_hours = month_df["hours"].sum() if not month_df.empty else 0
billable_pct = round((billable_hours / total_hours) * 100, 1) if total_hours > 0 else 0

top_client = "—"
if not df.empty and not df.groupby("client")["hours"].sum().empty:
    top_client = df.groupby("client")["hours"].sum().sort_values(ascending=False).index[0]

# ==================================================
# HEADER
# ==================================================
st.markdown("""
<div class="hero">
    <div class="hero-title">WorkLog Pro</div>
    <div class="hero-sub">
        Permanent cloud-backed time tracking, quick manual logging, live session capture, dashboard analytics and mobile-ready access.
    </div>
</div>
""", unsafe_allow_html=True)

# ==================================================
# KPI ROW
# ==================================================
def kpi_card(col, label, value, note=""):
    with col:
        st.markdown(f"""
        <div class="kpi">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """, unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6 = st.columns(6)
kpi_card(k1, "Today's Hours", format_hours(today_hours), "Current day logged effort")
kpi_card(k2, "Today's Billable", format_hours(today_billable), "Billable execution volume")
kpi_card(k3, "This Week", format_hours(week_hours), "Rolling 7-day output")
kpi_card(k4, "This Month", format_hours(month_hours), "Current month work volume")
kpi_card(k5, "Billable %", f"{billable_pct}%", "Utilisation ratio")
kpi_card(k6, "Top Client", top_client if len(str(top_client)) < 16 else str(top_client)[:15] + "…", "Highest allocation")

st.write("")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dashboard",
    "Live Session",
    "Register",
    "Analytics",
    "Settings"
])

# ==================================================
# DASHBOARD
# ==================================================
with tab1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Quick Time Entry</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-sub">Fast manual logging for completed work blocks and ad hoc entries.</div>', unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        quick_date = st.date_input("Date", value=date.today(), key="quick_date")
    with q2:
        quick_start = st.text_input("Start Time (HH:MM)", value="09:00", key="quick_start")
    with q3:
        quick_end = st.text_input("End Time (HH:MM)", value="10:00", key="quick_end")
    with q4:
        quick_billable = st.selectbox("Billable", ["Yes", "No"], key="quick_billable")

    q5, q6 = st.columns(2)
    with q5:
        quick_client = st.text_input("Client / Entity", key="quick_client")
    with q6:
        quick_task = st.text_input("Task / Work Item", key="quick_task")

    quick_remarks = st.text_area("Remarks", height=90, key="quick_remarks")
    quick_hours = calculate_hours(quick_start, quick_end)
    st.info(f"Calculated Hours: {quick_hours:.2f}")

    if st.button("Save Quick Entry", use_container_width=True, key="save_quick"):
        if not quick_client.strip() or not quick_task.strip():
            st.error("Please enter Client and Task.")
        elif quick_hours <= 0:
            st.error("Please enter valid Start Time and End Time.")
        else:
            insert_entry(
                entry_date=quick_date,
                start_time=quick_start,
                end_time=quick_end,
                hours=quick_hours,
                client=quick_client,
                task=quick_task,
                remarks=quick_remarks,
                billable=quick_billable
            )
            st.success("Entry saved successfully.")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Today’s Work Sheet</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-sub">Visible operating sheet for the current day.</div>', unsafe_allow_html=True)

        if not today_df.empty:
            show_today = today_df.copy()
            show_today["entry_date"] = show_today["entry_date"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                show_today[["entry_date", "start_time", "end_time", "hours", "client", "task", "billable", "remarks"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No work blocks logged today.")

        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Recent Activity</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-sub">Most recent work blocks captured in the system.</div>', unsafe_allow_html=True)

        if not df.empty:
            recent = df.head(6).copy()
            recent["entry_date_display"] = recent["entry_date"].dt.strftime("%Y-%m-%d")
            for _, r in recent.iterrows():
                billable_class = "pill" if safe_text(r["billable"]) == "Yes" else "pill pill-no"
                st.markdown(f"""
                <div class="activity-card">
                    <div class="activity-top">{safe_text(r["client"]) or "—"} • {safe_text(r["task"]) or "—"}</div>
                    <div class="activity-sub">
                        {safe_text(r["entry_date_display"])} | {safe_text(r["start_time"])}–{safe_text(r["end_time"])} | {format_hours(r["hours"])} hrs
                        <br>{safe_text(r["remarks"])}
                    </div>
                    <div class="{billable_class}">{safe_text(r["billable"]) or "Yes"}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Recent activity will appear after entries are logged.")

        st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# LIVE SESSION
# ==================================================
with tab2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Live Session Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-sub">Use Auto Mode for structured interval capture and Manual Mode for discretionary logging.</div>', unsafe_allow_html=True)

    left, right = st.columns([1.15, 1])

    with left:
        status = "Idle"
        if st.session_state.session_running:
            status = f"Running • {st.session_state.session_mode}"
        elif st.session_state.session_paused:
            status = "Paused"

        if st.session_state.session_start:
            elapsed = datetime.now() - st.session_state.session_start
            total_seconds = int(elapsed.total_seconds())
            hh = total_seconds // 3600
            mm = (total_seconds % 3600) // 60
            ss = total_seconds % 60
            timer_text = f"{hh:02d}:{mm:02d}:{ss:02d}"
        else:
            timer_text = "00:00:00"

        st.markdown(f"""
        <div class="timer-box">
            <div class="status-pill">{status}</div>
            <div class="timer-big">{timer_text}</div>
            <div class="small-muted">
                Last Logged Block: <strong>{st.session_state.last_logged}</strong><br>
                Current Client: <strong>{st.session_state.session_client or "—"}</strong><br>
                Current Task: <strong>{st.session_state.session_task or "—"}</strong><br>
                Billable: <strong>{st.session_state.session_billable or "Yes"}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        ui_mode = st.selectbox(
            "Session Mode",
            ["AUTO", "MANUAL"],
            index=0 if st.session_state.session_mode == "AUTO" else 1,
            key="ui_session_mode"
        )

        ui_interval = st.selectbox(
            "Auto Log Interval (minutes)",
            [15, 30, 45, 60],
            index=[15, 30, 45, 60].index(st.session_state.session_interval) if st.session_state.session_interval in [15, 30, 45, 60] else 3,
            key="ui_session_interval"
        )

        ui_billable = st.selectbox(
            "Billable",
            ["Yes", "No"],
            index=0 if st.session_state.session_billable == "Yes" else 1,
            key="ui_live_session_billable"
        )

        ui_client = st.text_input(
            "Client / Entity",
            value=st.session_state.session_client,
            key="ui_live_client"
        )

        ui_task = st.text_input(
            "Task / Work Item",
            value=st.session_state.session_task,
            key="ui_live_task"
        )

        ui_remarks = st.text_area(
            "Remarks",
            value=st.session_state.session_remarks,
            height=90,
            key="ui_live_remarks"
        )

    b1, b2, b3, b4, b5 = st.columns(5)

    with b1:
        if st.button("Start Session", use_container_width=True, key="start_session"):
            if not ui_client.strip() or not ui_task.strip():
                st.error("Please enter Client and Task before starting a session.")
            else:
                st.session_state.session_mode = ui_mode
                st.session_state.session_interval = ui_interval
                st.session_state.session_billable = ui_billable
                st.session_state.session_client = ui_client
                st.session_state.session_task = ui_task
                st.session_state.session_remarks = ui_remarks

                st.session_state.session_running = True
                st.session_state.session_paused = False
                st.session_state.session_start = datetime.now()
                st.session_state.block_start = datetime.now()
                st.success("Session started successfully.")
                st.rerun()

    with b2:
        if st.button("Pause", use_container_width=True, key="pause_session"):
            if st.session_state.session_running:
                st.session_state.session_running = False
                st.session_state.session_paused = True
                st.warning("Session paused.")
                st.rerun()

    with b3:
        if st.button("Resume", use_container_width=True, key="resume_session"):
            if st.session_state.session_paused:
                st.session_state.session_running = True
                st.session_state.session_paused = False
                st.success("Session resumed.")
                st.rerun()

    with b4:
        if st.button("Log Current Block", use_container_width=True, key="log_current_block"):
            if st.session_state.block_start:
                now = datetime.now()
                start_dt = st.session_state.block_start
                end_dt = now
                hrs = round((end_dt - start_dt).total_seconds() / 3600, 2)

                if hrs > 0:
                    insert_entry(
                        entry_date=start_dt.date(),
                        start_time=start_dt.strftime("%H:%M"),
                        end_time=end_dt.strftime("%H:%M"),
                        hours=hrs,
                        client=st.session_state.session_client,
                        task=st.session_state.session_task,
                        remarks=st.session_state.session_remarks,
                        billable=st.session_state.session_billable
                    )
                    st.session_state.last_logged = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')} ({hrs:.2f}h)"
                    st.session_state.block_start = datetime.now()
                    st.success("Current block logged successfully.")
                    st.rerun()
                else:
                    st.error("Block duration is too short.")

    with b5:
        if st.button("Stop Session", use_container_width=True, key="stop_session"):
            if st.session_state.block_start:
                now = datetime.now()
                start_dt = st.session_state.block_start
                end_dt = now
                hrs = round((end_dt - start_dt).total_seconds() / 3600, 2)

                if hrs > 0:
                    insert_entry(
                        entry_date=start_dt.date(),
                        start_time=start_dt.strftime("%H:%M"),
                        end_time=end_dt.strftime("%H:%M"),
                        hours=hrs,
                        client=st.session_state.session_client,
                        task=st.session_state.session_task,
                        remarks=st.session_state.session_remarks,
                        billable=st.session_state.session_billable
                    )
                    st.session_state.last_logged = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')} ({hrs:.2f}h)"

            st.session_state.session_running = False
            st.session_state.session_paused = False
            st.session_state.session_start = None
            st.session_state.block_start = None
            st.success("Session stopped.")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# AUTO MODE CHECK
if st.session_state.session_running and st.session_state.session_mode == "AUTO" and st.session_state.block_start:
    now = datetime.now()
    mins = (now - st.session_state.block_start).total_seconds() / 60

    if mins >= st.session_state.session_interval:
        start_dt = st.session_state.block_start
        end_dt = start_dt + timedelta(minutes=st.session_state.session_interval)
        hrs = round((end_dt - start_dt).total_seconds() / 3600, 2)

        insert_entry(
            entry_date=start_dt.date(),
            start_time=start_dt.strftime("%H:%M"),
            end_time=end_dt.strftime("%H:%M"),
            hours=hrs,
            client=st.session_state.session_client,
            task=st.session_state.session_task,
            remarks=st.session_state.session_remarks,
            billable=st.session_state.session_billable
        )

        st.session_state.last_logged = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')} ({hrs:.2f}h)"
        st.session_state.block_start = end_dt
        st.rerun()

# ==================================================
# REGISTER
# ==================================================
with tab3:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Execution Register</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-sub">Complete searchable record of all work logs.</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1:
        search_text = st.text_input("Search", value="", key="register_search")
    with f2:
        filter_billable = st.selectbox("Billable Filter", ["All", "Yes", "No"], key="register_billable_filter")
    with f3:
        filter_month = st.text_input("Month Filter (YYYY-MM)", value="", key="register_month_filter")

    filtered_df = df.copy()

    if not filtered_df.empty:
        if search_text.strip():
            q = search_text.lower().strip()
            filtered_df = filtered_df[
                filtered_df["client"].fillna("").str.lower().str.contains(q) |
                filtered_df["task"].fillna("").str.lower().str.contains(q) |
                filtered_df["remarks"].fillna("").str.lower().str.contains(q)
            ]

        if filter_billable != "All":
            filtered_df = filtered_df[filtered_df["billable"] == filter_billable]

        if filter_month.strip():
            filtered_df = filtered_df[filtered_df["entry_date"].dt.strftime("%Y-%m") == filter_month.strip()]

    if not filtered_df.empty:
        display_df = filtered_df.copy()
        display_df["entry_date"] = display_df["entry_date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display_df[["entry_date", "start_time", "end_time", "hours", "client", "task", "billable", "remarks"]],
            use_container_width=True,
            hide_index=True
        )

        csv_bytes = display_df.to_csv(index=False).encode("utf-8")
        excel_bytes = dataframe_to_excel_bytes(display_df, sheet_name="Filtered Register")

        d1, d2 = st.columns(2)
        with d1:
            st.download_button("Export Filtered CSV", data=csv_bytes, file_name=f"time_log_{date.today()}.csv", mime="text/csv", key="download_filtered_csv")
        with d2:
            st.download_button("Export Filtered Excel", data=excel_bytes, file_name=f"time_log_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_filtered_excel")
    else:
        st.info("No entries found for current filters.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Delete Specific Entry</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-sub">Use this only when you need to remove an incorrect log.</div>', unsafe_allow_html=True)

    if not df.empty:
        selector_df = df.copy()
        selector_df["entry_date_display"] = selector_df["entry_date"].dt.strftime("%Y-%m-%d")
        selector_df["label"] = (
            selector_df["entry_date_display"] + " | " +
            selector_df["start_time"].fillna("") + "-" +
            selector_df["end_time"].fillna("") + " | " +
            selector_df["client"].fillna("") + " | " +
            selector_df["task"].fillna("")
        )

        selected_label = st.selectbox("Select Entry", selector_df["label"].tolist(), key="delete_selector")
        selected_row = selector_df[selector_df["label"] == selected_label].iloc[0]

        if st.button("Delete Selected Entry", use_container_width=True, key="delete_selected_entry"):
            delete_entry(selected_row["id"])
            st.success("Entry deleted successfully.")
            st.rerun()
    else:
        st.info("No entries available yet.")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# ANALYTICS
# ==================================================
with tab4:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-sub">Operational visibility across clients, tasks and daily work output.</div>', unsafe_allow_html=True)

    if not df.empty:
        a1, a2 = st.columns(2)

        with a1:
            client_chart = df.groupby("client", dropna=False)["hours"].sum().reset_index().sort_values("hours", ascending=False).head(10)
            client_chart["client"] = client_chart["client"].replace("", "—").fillna("—")
            fig1 = px.bar(client_chart, x="client", y="hours", title="Hours by Client")
            st.plotly_chart(fig1, use_container_width=True)

        with a2:
            day_chart = df.groupby(df["entry_date"].dt.strftime("%Y-%m-%d"))["hours"].sum().reset_index()
            day_chart.columns = ["date", "hours"]
            fig2 = px.line(day_chart, x="date", y="hours", title="Hours by Day", markers=True)
            st.plotly_chart(fig2, use_container_width=True)

        b1, b2 = st.columns(2)

        with b1:
            task_chart = df.groupby("task", dropna=False)["hours"].sum().reset_index().sort_values("hours", ascending=False).head(10)
            task_chart["task"] = task_chart["task"].replace("", "—").fillna("—")
            fig3 = px.bar(task_chart, x="task", y="hours", title="Hours by Task")
            st.plotly_chart(fig3, use_container_width=True)

        with b2:
            billable_chart = df.groupby("billable", dropna=False)["hours"].sum().reset_index()
            billable_chart["billable"] = billable_chart["billable"].replace("", "—").fillna("—")
            fig4 = px.pie(billable_chart, names="billable", values="hours", title="Billable vs Non-Billable")
            st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Analytics will appear once entries are available.")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# SETTINGS
# ==================================================
with tab5:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">System & Backup</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-sub">Use this section for backup and environment visibility.</div>', unsafe_allow_html=True)

    s1, s2 = st.columns(2)
    s1.metric("Database", "Cloud PostgreSQL")
    s2.metric("Total Entries", int(len(df)))

    if not df.empty:
        csv_data = df.copy()
        if "entry_date" in csv_data.columns:
            csv_data["entry_date"] = csv_data["entry_date"].dt.strftime("%Y-%m-%d")

        full_csv = csv_data.to_csv(index=False).encode("utf-8")
        full_excel = dataframe_to_excel_bytes(csv_data, sheet_name="Full Backup")

        b1, b2 = st.columns(2)
        with b1:
            st.download_button("Download Full CSV Backup", data=full_csv, file_name=f"worklog_full_backup_{date.today()}.csv", mime="text/csv", key="download_full_csv")
        with b2:
            st.download_button("Download Full Excel Backup", data=full_excel, file_name=f"worklog_full_backup_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_full_excel")

    st.info("Your data is now designed to persist independently of app restarts and redeployments.")

    st.markdown('</div>', unsafe_allow_html=True)
