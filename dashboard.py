import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

# =========================
# LOAD GOOGLE SHEETS
# =========================
@st.cache_data
def load_data():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open("LCBTraining Data")
    worksheet = spreadsheet.worksheet("Data")
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    numeric_cols = ["Attempt_1","Attempt_2","Attempt_3","Last_Attempt","Average","Highest","Lowest"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    df["full_name"] = df["Player_name_first"].fillna("") + " " + df["Player_name_last"].fillna("")
    return df

df = load_data()

# =========================
# HELPER FUNCTIONS
# =========================
lower_is_better = {"10 yard sprint", "Pro Agility", "Home to 1B sprint"}

targets = {
    "8U": {"Bench":30,"Squat":50,"Pull Ups":2,"BES Tee":40,"BES Flip":35,"10 yard sprint":2.2,"Pro Agility":5.5,"Arm Speed Regular":35,"Arm Speed Pitch":30,"Home to 1B sprint":4.5},
    "10U":{"Bench":40,"Squat":70,"Pull Ups":4,"BES Tee":50,"BES Flip":45,"10 yard sprint":2.0,"Pro Agility":5.0,"Arm Speed Regular":45,"Arm Speed Pitch":40,"Home to 1B sprint":4.2},
    "12U":{"Bench":50,"Squat":90,"Pull Ups":6,"BES Tee":60,"BES Flip":55,"10 yard sprint":1.9,"Pro Agility":4.8,"Arm Speed Regular":55,"Arm Speed Pitch":50,"Home to 1B sprint":4.0},
    "14U":{"Bench":70,"Squat":110,"Pull Ups":8,"BES Tee":70,"BES Flip":65,"10 yard sprint":1.8,"Pro Agility":4.6,"Arm Speed Regular":65,"Arm Speed Pitch":60,"Home to 1B sprint":3.9},
    "16U":{"Bench":90,"Squat":140,"Pull Ups":10,"BES Tee":80,"BES Flip":75,"10 yard sprint":1.7,"Pro Agility":4.5,"Arm Speed Regular":75,"Arm Speed Pitch":70,"Home to 1B sprint":3.8}
}

def get_age_group(age):
    if age <= 8: return "8U"
    elif age <= 10: return "10U"
    elif age <= 12: return "12U"
    elif age <= 14: return "14U"
    return "16U"

# =========================
# GLOBAL PAGE STYLING
# =========================
st.markdown("""
<style>

/* HEADER WRAPPER */
.header-wrapper {
    background-color: #000000;
    padding: 18px;
    border-radius: 12px;
    margin-bottom: 25px;
    display: flex;
    align-items: center;
}

/* LOGO */
.header-logo {
    width: 80px;
    margin-right: 20px;
}

/* HEADER TEXT */
.header-text h1 {
    color: white;
    margin: 0;
    font-size: 34px;
    font-weight: 700;
}

.header-text p {
    color: #cccccc;
    margin: 0;
    font-size: 15px;
}

/* CARD */
.card {
    padding: 20px;
    background-color: #FFFFFF;
    border-radius: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.18);
    margin-bottom: 25px;
}

/* KPI TILE */
.kpi {
    padding: 14px;
    background-color: #F5F5F5;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 1px 5px rgba(0,0,0,0.12);
}

.kpi h4 {
    margin: 4px 0 6px 0;
    font-size: 14px;
    color: #444;
}

.kpi b {
    font-size: 18px;
    color: #000;
}

</style>
""", unsafe_allow_html=True)

# =========================
# HEADER WITH LOGO
# =========================
try:
    logo = Image.open("lcb training logo.png")
    st.markdown(
        f"""
        <div class="header-wrapper">
            <img src="data:image/png;base64,{st.image(logo, output_format='PNG').image_to_bytes().hex()}" 
            class="header-logo">
            <div class="header-text">
                <h1>LCB Training Performance Dashboard</h1>
                <p>Elite Player Development • Strength • Speed • Confidence</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
except:
    st.warning("Logo not found — make sure 'lcb training logo.png' is in the project folder.")

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["👤 Player", "👥 Team", "🏆 Leaderboard"])

# =============================================================
# --------------------- PLAYER TAB ----------------------------
# =============================================================
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Player Dashboard — Overview")

    players = sorted(df["full_name"].dropna().unique())
    selected_player = st.selectbox("Select Player", players)

    if selected_player:
        player_df = df[df["full_name"] == selected_player].copy()

        if player_df.empty:
            st.info("No records found for this player.")
        else:
            # Player info
            player_age = int(player_df["Age"].dropna().iloc[0]) if not player_df["Age"].dropna().empty else None
            age_group = get_age_group(player_age) if player_age else "N/A"
            player_team = player_df["Team"].dropna().iloc[0] if not player_df["Team"].dropna().empty else "N/A"

            # Summary Header
            st.markdown("<h3 style='margin-bottom:10px'>📊 Player Summary</h3>", unsafe_allow_html=True)

            # KPI Row
            colA, colB, colC = st.columns(3)
            colA.markdown(f"<div class='kpi'><h4>Player</h4><b>{selected_player}</b></div>", unsafe_allow_html=True)
            colB.markdown(f"<div class='kpi'><h4>Team</h4><b>{player_team}</b></div>", unsafe_allow_html=True)
            colC.markdown(f"<div class='kpi'><h4>Age Group</h4><b>{age_group}</b></div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ========= BEST SCORES TABLE =========
            st.markdown("### 🏅 Best Performance by Metric")
            summary_data = []
            for metric in player_df["Metric_Type"].unique():
                df_metric = player_df[player_df["Metric_Type"] == metric]
                best_score = df_metric["Average"].min() if metric in lower_is_better else df_metric["Average"].max()
                summary_data.append({"Metric": metric, "Best Score": best_score})

            best_df = pd.DataFrame(summary_data)
            st.dataframe(best_df.style.format({"Best Score": "{:.2f}"}), use_container_width=True)

            # ========= TREND CHARTS =========
            st.markdown("### 📈 Performance Trends")

            for metric in player_df["Metric_Type"].unique():
                df_m = player_df[player_df["Metric_Type"] == metric].sort_values("Date")
                fig = px.line(
                    df_m, x="Date", y="Average",
                    markers=True,
                    title=f"{metric} Progress Over Time"
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# =============================================================
# --------------------- TEAM TAB ------------------------------
# =============================================================
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Team Dashboard — Overview")

    teams = sorted(df["Team"].dropna().unique())
    selected_team = st.selectbox("Select Team", teams)

    if selected_team:
        team_df = df[df["Team"] == selected_team]

        if team_df.empty:
            st.warning("No team data found.")
        else:
            avg_age = round(team_df["Age"].mean(), 2)
            st.write(f"**Avg Age:** {avg_age}")

    st.markdown("</div>", unsafe_allow_html=True)

# =============================================================
# ------------------ LEADERBOARD TAB --------------------------
# =============================================================
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Leaderboard — Top Performers")

    metric_list = sorted(df["Metric_Type"].unique())
    selected_metric = st.selectbox("Select Metric", metric_list)

    df_metric = df[df["Metric_Type"] == selected_metric]
    df_metric = df_metric.groupby("full_name")["Average"].max().reset_index()

    if selected_metric in lower_is_better:
        df_metric = df_metric.sort_values("Average", ascending=True)
    else:
        df_metric = df_metric.sort_values("Average", ascending=False)

    st.dataframe(df_metric.head(15), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
