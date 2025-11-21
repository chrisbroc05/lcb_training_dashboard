import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO

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
# CONFIG
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
# GLOBAL STYLE
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
    width: 55px;  /* Smaller logo */
    margin-right: 20px;
}

/* HEADER TEXT */
.header-text h1 {
    color: white;
    margin: 0;
    font-size: 32px;
    font-weight: 700;
}

.header-text p {
    color: #cccccc;
    margin: 0;
    font-size: 14px;
}

/* SLOGAN */
.header-text .slogan {
    color: #bbbbbb;
    margin-top: 6px;
    font-size: 13px;
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
# HEADER WITH LOGO + SLOGAN
# =========================
def image_to_base64(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

try:
    logo = Image.open("lcb training logo.png")
    logo_b64 = image_to_base64(logo)

    st.markdown(
    f"""
    <style>
        .header-wrapper {{
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .header-logo {{
            width: 120px;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .header-text h1 {{
            margin: 0;
            font-size: 36px;
            color: #FFFFFF;
        }}
        .header-text p {{
            margin: 2px 0;
            font-size: 16px;
            color: #FFFFFF;
        }}
        .header-text .slogan {{
            font-size: 14px;
            font-style: italic;
            color: #FFFFFF;
            margin-top: 5px;
            max-width: 600px;
        }}
    </style>

    <div class="header-wrapper">
        <img src="data:image/png;base64,{logo_b64}" class="header-logo">
        <div class="header-text">
            <h1>LCB Training Performance Dashboard</h1>
            <p>Player Development • Strength • Speed • Confidence</p>
            <p class="slogan">Elite Player Development Training for Teams and Players — <b>Helping Athletes Build Strength, Skill, and Confidence On and Off the Field</b></p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
except:
    st.warning("Logo not found — make sure 'lcb training logo.png' is present.")

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
            # ---------------------------
            # GET MOST RECENT PLAYER INFO
            # ---------------------------
            most_recent = player_df.sort_values("Date").iloc[-1]
            player_age = int(most_recent["Age"]) if not pd.isna(most_recent["Age"]) else None
            player_team = most_recent["Team"] if str(most_recent["Team"]) != "nan" else "N/A"
            age_group = get_age_group(player_age) if player_age else "N/A"

            # ---------------------------
            # PLAYER SUMMARY
            # ---------------------------
            st.markdown("<h3 style='margin-bottom:10px'>📊 Player Summary</h3>", unsafe_allow_html=True)

            colA, colB, colC = st.columns(3)
            colA.markdown(f"<div class='kpi'><h4>Player</h4><b>{selected_player}</b></div>", unsafe_allow_html=True)
            colB.markdown(f"<div class='kpi'><h4>Team</h4><b>{player_team}</b></div>", unsafe_allow_html=True)
            colC.markdown(f"<div class='kpi'><h4>Age Group</h4><b>{age_group}</b></div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

        # =====================================================
        # RESULTS SUMMARY TABLE (FIRST, LATEST, BEST, GROWTH)
        # =====================================================
        st.markdown("### 📘 Results Summary")
        
        rows = []
        for metric in player_df["Metric_Type"].unique():
            mdf = player_df[player_df["Metric_Type"] == metric].sort_values("Date")
        
            first = mdf["Average"].iloc[0]
            latest = mdf["Average"].iloc[-1]
        
            if metric in lower_is_better:
                best = mdf["Average"].min()
                growth = first - best  # improvement = decrease
            else:
                best = mdf["Average"].max()
                growth = best - first  # improvement = increase
        
            goal = targets.get(age_group, {}).get(metric, None)
        
            rows.append({
                "Metric": metric,
                "First": first,
                "Latest": latest,
                "Best": best,
                "Growth": growth,
                "Goal": goal
            })
        
        summary_df = pd.DataFrame(rows)
        
        # ---- FIXED: Format only the numeric columns ----
        numeric_cols = ["First", "Latest", "Best", "Growth", "Goal"]
        format_dict = {col: "{:.2f}" for col in numeric_cols if col in summary_df.columns}
        
        st.dataframe(summary_df.style.format(format_dict), use_container_width=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # =========================
        # BEST PERFORMANCES TABLE
        # =========================
        st.markdown("### 🏅 Best Performance by Metric")
        
        summary_data = []
        for metric in player_df["Metric_Type"].unique():
            df_metric = player_df[player_df["Metric_Type"] == metric]
            best_score = df_metric["Average"].min() if metric in lower_is_better else df_metric["Average"].max()
            summary_data.append({"Metric": metric, "Best Score": best_score})
        
        best_df = pd.DataFrame(summary_data)
        best_df["Best Score"] = pd.to_numeric(best_df["Best Score"], errors="coerce")
        
        st.dataframe(
            best_df.style.format({"Best Score": "{:.2f}"}),
            use_container_width=True
        )
        
        # =========================
        # PERFORMANCE TRENDS
        # =========================
        st.markdown("### 📈 Performance Trends")
        
        # --- Metric Groups ---
        baseball_metrics = [
            "Arm Speed Pitch", "Arm Speed Reg",
            "BES Flip", "BES Tee"
        ]
        
        speed_metrics = [
            "10 yard sprint", "Pro Agility"
        ]
        
        # Helper function to compute summary for cards
        def get_metric_summary(df, metric):
            mdf = df[df["Metric_Type"] == metric].sort_values("Date")
            if mdf.empty:
                return None, None, None
        
            first = mdf["Average"].iloc[0]
            latest = mdf["Average"].iloc[-1]
        
            if metric in lower_is_better:
                best = mdf["Average"].min()
                growth = first - best   # lower = better
            else:
                best = mdf["Average"].max()
                growth = best - first   # higher = better
        
            return first, best, growth
        
        
        # -----------------------------
        # KPI Cards for Baseball Metrics
        # -----------------------------
        st.markdown("#### Strength Performance Metrics")
        
        df_baseball = player_df[player_df["Metric_Type"].isin(baseball_metrics)]
        
        if not df_baseball.empty:
            df_baseball["Month"] = df_baseball["Date"].dt.month
        
            # First half of year
            df_h1 = df_baseball[df_baseball["Month"] <= 6]
            if not df_h1.empty:
                fig_h1 = px.line(
                    df_h1.sort_values("Date"),
                    x="Date", y="Average", color="Metric_Type",
                    markers=True,
                    title="Strength Performance (Jan - Jun)"
                )
                fig_h1.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h1, use_container_width=True)
        
            # Second half of year
            df_h2 = df_baseball[df_baseball["Month"] > 6]
            if not df_h2.empty:
                fig_h2 = px.line(
                    df_h2.sort_values("Date"),
                    x="Date", y="Average", color="Metric_Type",
                    markers=True,
                    title="Strength Performance (Jul - Dec)"
                )
                fig_h2.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h2, use_container_width=True)

        
            card_cols = st.columns(4)
            for i, metric in enumerate(baseball_metrics):
                first, best, growth = get_metric_summary(player_df, metric)
                if first is None:
                    continue
        
                # Determine arrow and color
                if growth > 0:
                    growth_color = "#00B050"  # vivid green
                    arrow = "▲"
                elif growth < 0:
                    growth_color = "#FF0000"  # bright red
                    arrow = "▼"
                else:
                    growth_color = "#000000"  # black if no change
                    arrow = ""
        
                with card_cols[i % 4]:
                    st.markdown(f"""
                    <div class='kpi' style="text-align:center; padding:20px;">
                        <h3 style="margin:0 0 10px 0; font-size:20px; color:blue;">{metric}</h3>
                        <p style="margin:4px 0; font-size:18px; color:blue;"><b>First:</b> {first:.2f}</p>
                        <p style="margin:4px 0; font-size:18px; color:blue;"><b>Best:</b> {best:.2f}</p>
                        <p style="margin:8px 0 0 0; font-size:20px; font-weight:700; color:{growth_color};">
                            {arrow} {growth:.2f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

        
        # Add vertical space
        st.markdown("<br><br>", unsafe_allow_html=True)  # <-- extra space between sections
        
        # -----------------------------
        # KPI Cards for Speed & Agility Metrics
        # -----------------------------
        st.markdown("#### Speed & Agility Performance Metrics")
        
        df_baseball = player_df[player_df["Metric_Type"].isin(speed_metrics)]
        
        if not df_baseball.empty:
            df_baseball["Month"] = df_baseball["Date"].dt.month
        
            # First half of year (Jan - Jun)
            df_h1 = df_baseball[df_baseball["Month"] <= 6]
            if not df_h1.empty:
                fig_h1 = px.line(
                    df_h1.sort_values("Date"),
                    x="Date", y="Average", color="Metric_Type",
                    markers=True,
                    title="Speed & Agility Performance (Jan - Jun)"
                )
                fig_h1.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h1, use_container_width=True)
        
            # Second half of year (Jul - Dec)
            df_h2 = df_baseball[df_baseball["Month"] > 6]
            if not df_h2.empty:
                fig_h2 = px.line(
                    df_h2.sort_values("Date"),
                    x="Date", y="Average", color="Metric_Type",
                    markers=True,
                    title="Speed & Agility Performance (Jul - Dec)"
                )
                fig_h2.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h2, use_container_width=True)

        
            card_cols = st.columns(2)
            for i, metric in enumerate(speed_metrics):
                first, best, growth = get_metric_summary(player_df, metric)
                if first is None:
                    continue
        
                # Determine arrow and color
                if growth > 0:
                    growth_color = "#00B050"  # vivid green
                    arrow = "▲"
                elif growth < 0:
                    growth_color = "#FF0000"  # bright red
                    arrow = "▼"
                else:
                    growth_color = "#000000"  # black if no change
                    arrow = ""
        
                with card_cols[i % 2]:
                    st.markdown(f"""
                    <div class='kpi' style="text-align:center; padding:20px;">
                        <h3 style="margin:0 0 10px 0; font-size:20px;">{metric}</h3>
                        <p style="margin:4px 0; font-size:18px;"><b>First:</b> {first:.2f}</p>
                        <p style="margin:4px 0; font-size:18px;"><b>Best:</b> {best:.2f}</p>
                        <p style="margin:8px 0 0 0; font-size:20px; font-weight:700; color:{growth_color};">
                            {arrow} {growth:.2f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)


# =============================================================
# --------------------- TEAM TAB ------------------------------
# =============================================================
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Team Dashboard — Overview")

    # ---------------------------
    # Team Selection
    # ---------------------------
    teams = sorted(df["Team"].dropna().unique())
    selected_team = st.selectbox("Select Team", teams)

    if selected_team:
        team_df = df[df["Team"] == selected_team].copy()

        if team_df.empty:
            st.warning("No data found for this team.")
        else:
            # ---------------------------
            # Team Summary KPIs
            # ---------------------------
            st.markdown("<h3>📊 Team Summary</h3>", unsafe_allow_html=True)

            # Calculate averages for the team
            avg_age = round(team_df["Age"].mean(), 1)
            avg_bes_tee = round(team_df[team_df["Metric_Type"].isin(["BES Tee"])]["Average"].mean(), 1)
            avg_sprint = round(team_df[team_df["Metric_Type"].isin(["10 yard sprint"])]["Average"].mean(), 1)
            avg_speed = round(team_df[team_df["Metric_Type"].isin(["Pro Agility"])]["Average"].mean(), 1)

            kpi_cols = st.columns(4)
            kpi_cols[0].markdown(f"<div class='kpi'><h4>Avg Age</h4><b>{avg_age}</b></div>", unsafe_allow_html=True)
            kpi_cols[1].markdown(f"<div class='kpi'><h4>Avg BES Tee</h4><b>{avg_bes_tee}</b></div>", unsafe_allow_html=True)
            kpi_cols[2].markdown(f"<div class='kpi'><h4>Avg 10 Yard Sprint</h4><b>{avg_sprint}</b></div>", unsafe_allow_html=True)
            kpi_cols[3].markdown(f"<div class='kpi'><h4>Avg Pro Agility</h4><b>{avg_speed}</b></div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ---------------------------
            # Team Performance Trends - Strength
            # ---------------------------
            st.markdown("### Team Strength Metrics")
            
            # Filter strength metrics for the team
            team_strength = team_df[team_df["Metric_Type"].isin(baseball_metrics)]
            if not team_strength.empty:
                strength_metrics = team_strength.groupby(["Date", "Metric_Type"])["Average"].mean().reset_index()
                fig_strength = px.line(
                    strength_metrics.sort_values("Date"),
                    x="Date", y="Average", color="Metric_Type",
                    markers=True,
                    title=f"{selected_team} Strength Performance Over Time"
                )
                fig_strength.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_strength, use_container_width=True)
            
            # ---------------------------
            # Team Performance Trends - Speed & Agility
            # ---------------------------
            st.markdown("### Team Speed & Agility Metrics")
            
            # Filter speed metrics for the team
            team_speed = team_df[team_df["Metric_Type"].isin(speed_metrics)]
            if not team_speed.empty:
                speed_metrics = team_speed.groupby(["Date", "Metric_Type"])["Average"].mean().reset_index()
                fig_speed = px.line(
                    speed_metrics.sort_values("Date"),
                    x="Date", y="Average", color="Metric_Type",
                    markers=True,
                    title=f"{selected_team} Speed & Agility Performance Over Time"
                )
                fig_speed.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_speed, use_container_width=True)
            
            st.markdown("<hr>", unsafe_allow_html=True)


            # ---------------------------
            # Top Performers Table with Metric Filter
            # ---------------------------
            st.markdown("### Top Performers by Metric")
            
            # Metric selection for filtering
            metrics_for_filter = sorted(team_df["Metric_Type"].unique())
            selected_metric = st.selectbox("Select Metric to View Top Performers", metrics_for_filter)
            
            if selected_metric:
                metric_df = team_df[team_df["Metric_Type"] == selected_metric].copy()
            
                if metric_df.empty:
                    st.warning("No data found for this metric.")
                else:
                    # Determine whether to use max or min based on metric type
                    if selected_metric in lower_is_better:
                        top_players_metric = metric_df.groupby("player_id").agg({
                            "Player_name_first": "first",
                            "Player_name_last": "first",
                            "Average": "min"  # lower is better
                        }).reset_index()
                    else:
                        top_players_metric = metric_df.groupby("player_id").agg({
                            "Player_name_first": "first",
                            "Player_name_last": "first",
                            "Average": "max"  # higher is better
                        }).reset_index()
            
                    top_players_metric["Full Name"] = top_players_metric["Player_name_first"] + " " + top_players_metric["Player_name_last"]
                    top_players_metric = top_players_metric.sort_values("Average", ascending=(selected_metric in lower_is_better))
            
                    st.dataframe(
                        top_players_metric[["Full Name", "Average"]].head(10).style.format({"Average": "{:.2f}"}),
                        use_container_width=True
                    )


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
