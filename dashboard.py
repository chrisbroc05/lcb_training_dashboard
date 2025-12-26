import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
import tempfile

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
    "8U": {
        "Bench": 45, "Squat": 70, "Pull Ups": 2, "Wall Sit": 30, "Plank": 30, "Push Ups": 5,
        "10 yard sprint": 2.8, "Pro Agility": 5.8, "Home to 1B sprint": 6.0,
        "Arm Speed Pitch": 30, "Arm Speed Reg": 35, "BES Flip": 45, "BES Tee": 40, "Broad Jump": 5
    },
    "10U": {
        "Bench": 65, "Squat": 90, "Pull Ups": 4, "Wall Sit": 60, "Plank": 45, "Push Ups": 10,
        "10 yard sprint": 2.3, "Pro Agility": 5.0, "Home to 1B sprint": 5.2,
        "Arm Speed Pitch": 40, "Arm Speed Reg": 45, "BES Flip": 60, "BES Tee": 50, "Broad Jump": 6
    },
    "12U": {
        "Bench": 90, "Squat": 120, "Pull Ups": 6, "Wall Sit": 90, "Plank": 60, "Push Ups": 15,
        "10 yard sprint": 2.0, "Pro Agility": 4.9, "Home to 1B sprint": 5.0,
        "Arm Speed Pitch": 50, "Arm Speed Reg": 55, "BES Flip": 65, "BES Tee": 60, "Broad Jump": 7
    },
    "14U": {
        "Bench": 120, "Squat": 135, "Pull Ups": 8, "Wall Sit": 120, "Plank": 90, "Push Ups": 20,
        "10 yard sprint": 1.9, "Pro Agility": 4.8, "Home to 1B sprint": 4.8,
        "Arm Speed Pitch": 60, "Arm Speed Reg": 65, "BES Flip": 75, "BES Tee": 70, "Broad Jump": 7.5
    },
    "16U": {
        "Bench": 135, "Squat": 180, "Pull Ups": 10, "Wall Sit": 180, "Plank": 120, "Push Ups": 25,
        "10 yard sprint": 1.7, "Pro Agility": 4.5, "Home to 1B sprint": 4.3,
        "Arm Speed Pitch": 70, "Arm Speed Reg": 75, "BES Flip": 90, "BES Tee": 80, "Broad Jump": 9
    }
}

def get_age_group(age):
    if age <= 8: return "8U"
    elif age <= 10: return "10U"
    elif age <= 12: return "12U"
    elif age <= 14: return "14U"
    return "16U"

# =========================
# PDF Summary
# =========================

CARD_METRICS = [
    "10 yard sprint",
    "Pro Agility",
    "BES Tee",
    "BES Flip",
    "Arm Speed Pitch",
    "Arm Speed Reg"
]


def draw_scorecard(c, x, y, w, h, metric, first, best, goal, status, trend_up):
    # Card background
    c.setFillColor(colors.whitesmoke)
    c.roundRect(x, y, w, h, 10, fill=1)

    # Border
    c.setStrokeColor(colors.grey)
    c.roundRect(x, y, w, h, 10, fill=0)

    # Metric title
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(x + 10, y + h - 20, metric)

    # First value
    c.setFont("Helvetica", 10)
    c.drawString(x + 10, y + h - 40, f"Best: {best:.2f}")

    # Best value
    c.setFont("Helvetica", 10)
    c.drawString(x + 10, y + h - 58, f"Best: {best:.2f}")

    # Goal
    goal_text = f"{goal:.2f}" if goal is not None else "—"
    c.drawString(x + 10, y + h - 76, f"Goal: {goal_text}")

    # Status
    status_color = colors.green if status == "Met" else colors.red
    c.setFillColor(status_color)
    c.drawString(x + 10, y + h - 94, f"Status: {status}")

    # Trend arrow
    arrow = "▲" if trend_up else "▼"
    arrow_color = colors.green if trend_up else colors.red
    c.setFillColor(arrow_color)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(x + w - 10, y + 15, arrow)


def create_player_summary_pdf(player_name, player_df, age_group, team):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp_file.name, pagesize=LETTER)
    width, height = LETTER

    # ---- LOGO ----
    logo_path = "lcb training logo.png"
    c.drawImage(logo_path, 40, height - 90, width=70, height=70, mask="auto")

    # ---- TITLE ----
    c.setFont("Helvetica-Bold", 20)
    c.drawString(130, height - 55, "LCB Training Performance Summary")

    # ---- PLAYER INFO ----
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawString(40, height - 120, f"Player: {player_name}")
    c.drawString(40, height - 140, f"Team: {team}")
    c.drawString(40, height - 160, f"Age Group: {age_group}")

    # ---- SCORECARDS ----
    card_width = 250
    card_height = 95
    start_x = 40
    start_y = height - 240
    gap_x = 20
    gap_y = 20

    col = 0
    row = 0

    for metric in CARD_METRICS:
        mdf = player_df[player_df["Metric_Type"] == metric]
        if mdf.empty:
            continue

        # First & Best values
        if metric in lower_is_better:
            best = mdf["Lowest"].min()
            first = mdf.sort_values("Date")["Lowest"].iloc[0]
            trend_up = best < first
            status = "Met" if targets.get(age_group, {}).get(metric) and best <= targets[age_group][metric] else "Needs Work"
        else:
            best = mdf["Highest"].max()
            first = mdf.sort_values("Date")["Highest"].iloc[0]
            trend_up = best > first
            status = "Met" if targets.get(age_group, {}).get(metric) and best >= targets[age_group][metric] else "Needs Work"

        goal = targets.get(age_group, {}).get(metric)

        x = start_x + col * (card_width + gap_x)
        y = start_y - row * (card_height + gap_y)

        draw_scorecard(
            c,
            x=x,
            y=y,
            w=card_width,
            h=card_height,
            metric=metric,
            first=first,
            best=best,
            goal=goal,
            status=status,
            trend_up=trend_up
        )

        col += 1
        if col > 1:
            col = 0
            row += 1

    # ---- FOOTER ----
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawCentredString(
        width / 2,
        30,
        "Generated by LCB Training Performance Portal • Work Hard. Be Memorable."
    )

    c.showPage()
    c.save()

    return temp_file.name


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
tab1, tab2, tab3 = st.tabs(["👤 Player", "👥 Team", "🏆 LCB Training Leaderboard"])

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
            # PDF GENERATION
            # ---------------------------
            if st.button("📄 Create Summary Report"):
                pdf_path = create_player_summary_pdf(
                    selected_player,
                    player_df,
                    age_group,
                    player_team
                )

                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Player Report (PDF)",
                        f,
                        file_name=f"{selected_player.replace(' ', '_')}_LCB_Report.pdf",
                        mime="application/pdf"
                    )

            # ---------------------------
            # PLAYER SUMMARY
            # ---------------------------
            st.markdown("<h3 style='margin-bottom:10px'>📊 Player Summary</h3>", unsafe_allow_html=True)

            colA, colB, colC = st.columns(3)
            colA.markdown(f"<div class='kpi'><h4>Player</h4><b>{selected_player}</b></div>", unsafe_allow_html=True)
            colB.markdown(f"<div class='kpi'><h4>Team</h4><b>{player_team}</b></div>", unsafe_allow_html=True)
            colC.markdown(f"<div class='kpi'><h4>Age Group</h4><b>{age_group}</b></div>", unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

        # ===========================
        # RESULTS SUMMARY TABLE (FIRST, LATEST, BEST, GROWTH)
        # ===========================
        st.markdown("### 📘 Results Summary")
        
        rows = []
        for metric in player_df["Metric_Type"].unique():
            mdf = player_df[player_df["Metric_Type"] == metric].sort_values("Date")
        
            # ----- NEW LOGIC FOR FIRST & LATEST -----
            if metric in lower_is_better:
                first = mdf["Lowest"].iloc[0] if "Lowest" in mdf else mdf["Average"].iloc[0]
                latest = mdf["Lowest"].iloc[-1] if "Lowest" in mdf else mdf["Average"].iloc[-1]
            else:
                first = mdf["Highest"].iloc[0] if "Highest" in mdf else mdf["Average"].iloc[0]
                latest = mdf["Highest"].iloc[-1] if "Highest" in mdf else mdf["Average"].iloc[-1]

            # Best logic stays the same
            if metric in lower_is_better:
                best = mdf["Lowest"].min()
                growth = first - best  
            else:
                best = mdf["Highest"].max()
                growth = best - first

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
        
        # ---- FORMAT NUMERIC COLUMNS ----
        numeric_cols = ["First", "Latest", "Best", "Growth", "Goal"]
        format_dict = {col: "{:.2f}" for col in numeric_cols if col in summary_df.columns}
        
        # ---- CONDITIONAL FORMATTING FOR 'Best' ----
        def color_best_row(row):
            metric = row["Metric"]
            val = row["Best"]
            goal_val = targets.get(age_group, {}).get(metric, None)
            if goal_val is None:
                return [""] * len(row)  # no formatting
            if metric in lower_is_better:
                color = "color: green" if val <= goal_val else "color: red"
            else:
                color = "color: green" if val >= goal_val else "color: red"
            # Apply color only to 'Best', empty string for other columns
            return [""]*row.index.get_loc("Best") + [color] + [""]*(len(row)-row.index.get_loc("Best")-1)
        
        summary_df_styled = summary_df.style.format(format_dict)\
            .apply(color_best_row, axis=1)
        
        st.dataframe(summary_df_styled, width="stretch")
        
        # =========================
        # BEST PERFORMANCES TABLE
        # =========================
        st.markdown("### 🏅 Best Performance by Metric")
        
        summary_data = []
        for metric in player_df["Metric_Type"].unique():
            df_metric = player_df[player_df["Metric_Type"] == metric]
            best_score = df_metric["Lowest"].min() if metric in lower_is_better else df_metric["Highest"].max()
            summary_data.append({"Metric": metric, "Best Score": best_score})
        
        best_df = pd.DataFrame(summary_data)
        best_df["Best Score"] = pd.to_numeric(best_df["Best Score"], errors="coerce")
        
        st.dataframe(
            best_df.style.format({"Best Score": "{:.2f}"}),
            width="stretch"
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
        
            # --- NEW LOGIC FOR FIRST & LATEST ---
            if metric in lower_is_better:
                first = mdf["Lowest"].iloc[0] if "Lowest" in mdf.columns else mdf["Average"].iloc[0]
                latest = mdf["Lowest"].iloc[-1] if "Lowest" in mdf.columns else mdf["Average"].iloc[-1]
            else:
                first = mdf["Highest"].iloc[0] if "Highest" in mdf.columns else mdf["Average"].iloc[0]
                latest = mdf["Highest"].iloc[-1] if "Highest" in mdf.columns else mdf["Average"].iloc[-1]

            if metric in lower_is_better:
                best = mdf["Lowest"].min()
                growth = first - best   # lower = better
            else:
                best = mdf["Highest"].max()
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
                    x="Date", y="Highest", color="Metric_Type",
                    markers=True,
                    title="Strength Performance (Jan - Jun)"
                )
                fig_h1.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h1, width="stretch")
        
            # Second half of year
            df_h2 = df_baseball[df_baseball["Month"] > 6]
            if not df_h2.empty:
                fig_h2 = px.line(
                    df_h2.sort_values("Date"),
                    x="Date", y="Highest", color="Metric_Type",
                    markers=True,
                    title="Strength Performance (Jul - Dec)"
                )
                fig_h2.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h2, width="stretch")

        
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
                    x="Date", y="Lowest", color="Metric_Type",
                    markers=True,
                    title="Speed & Agility Performance (Jan - Jun)"
                )
                fig_h1.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h1, width="stretch")
        
            # Second half of year (Jul - Dec)
            df_h2 = df_baseball[df_baseball["Month"] > 6]
            if not df_h2.empty:
                fig_h2 = px.line(
                    df_h2.sort_values("Date"),
                    x="Date", y="Lowest", color="Metric_Type",
                    markers=True,
                    title="Speed & Agility Performance (Jul - Dec)"
                )
                fig_h2.update_layout(height=350, legend_title_text="Metric")
                st.plotly_chart(fig_h2, width="stretch")

        
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
                        <h3 style="margin:0 0 10px 0; font-size:18px; color:blue;">{metric}</h3>
                        <p style="margin:4px 0; font-size:18px; color:blue;"><b>First:</b> {first:.2f}</p>
                        <p style="margin:4px 0; font-size:18px; color:blue;"><b>Best:</b> {best:.2f}</p>
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
                st.plotly_chart(fig_strength, width="stretch")
            
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
                st.plotly_chart(fig_speed, width="stretch")
            
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
                        width="stretch"
                    )


# =============================================================
# ------------------ LEADERBOARD TAB --------------------------
# =============================================================
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("LCB Training Leaderboard — Top Performers")

    # ---- Metric Filter ----
    metric_list = sorted(df["Metric_Type"].unique())
    selected_metric = st.selectbox("Select Metric", metric_list)

    # ---- Age Filter ----
    age_options = ["All Ages"] + sorted(df["Age"].unique())
    selected_age = st.selectbox("Filter by Age", age_options)

    # Apply age filter
    if selected_age != "All Ages":
        df_filtered = df[df["Age"] <= int(selected_age)]
    else:
        df_filtered = df.copy()

    # ---- Filter data for selected metric ----
    df_metric = df_filtered[df_filtered["Metric_Type"] == selected_metric]

    # ---- Build leaderboard rows ----
    rows = []
    for player, pdf in df_metric.groupby("full_name"):
        pdf = pdf.sort_values("Date")

        if selected_metric in lower_is_better:
            value = pdf["Average"].min()  # lowest is better
            rows.append({"full_name": player, "Age": pdf["Age"].iloc[-1], "Lowest": value})
        else:
            value = pdf["Average"].max()  # highest is better
            rows.append({"full_name": player, "Age": pdf["Age"].iloc[-1], "Highest": value})

    leaderboard = pd.DataFrame(rows)

    # ---- Sorting ----
    if selected_metric in lower_is_better:
        leaderboard = leaderboard.sort_values("Lowest", ascending=True)
    else:
        leaderboard = leaderboard.sort_values("Highest", ascending=False)

    # ---- Display top performers ----
    st.dataframe(leaderboard.head(15), width="stretch")

    st.markdown("</div>", unsafe_allow_html=True)

