import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

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
/* HEADER BAR */
.header {
    background-color: #111111;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 25px;
    color: white;
}

/* SUB-SECTION CARDS */
.card {
    padding: 18px;
    background-color: #FFFFFF;
    border-radius: 12px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    margin-bottom: 20px;
}

/* KPI TILE */
.kpi {
    padding: 15px;
    background-color: #f7f7f7;
    border-radius: 10px;
    text-align: center;
    margin: 5px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

</style>
""", unsafe_allow_html=True)

# =========================
# HEADER WITH LOGO
# =========================
st.markdown("""
<div class="header">
    <h1>LCB Training Performance Dashboard</h1>
    <p>Elite Player Development • Strength • Speed • Confidence</p>
</div>
""", unsafe_allow_html=True)

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["👤 Player", "👥 Team", "🏆 Leaderboard"])

# =========================
# PART 2 - Player / Team / Leaderboard UI + Charts (continued)
# Place this immediately after the header & tabs code from Part 1.
# =========================

# small helper: case-insensitive metric matching
def metric_in_list(metric, metric_list):
    return next((m for m in metric_list if m.lower() == metric.lower()), None)

# ---------- Player Tab ----------
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Player Dashboard — Overview")
    players = sorted(df["full_name"].dropna().unique())
    selected_player = st.selectbox("Select Player", players, index=0)

    if selected_player:
        player_df = df[df["full_name"] == selected_player].copy()
        if player_df.empty:
            st.info("No records for this player.")
        else:
            # basic player info
            player_age = int(player_df["Age"].dropna().iloc[0]) if not player_df["Age"].dropna().empty else None
            age_group = get_age_group(player_age) if player_age is not None else "N/A"
            player_team = player_df["Team"].dropna().iloc[0] if not player_df["Team"].dropna().empty else "N/A"
            total_sessions = player_df["Date"].nunique()

# ==========================
# Player Summary Card
# ==========================
st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown("""
<h3 style='margin-bottom:10px'>📊 Player Summary</h3>
""", unsafe_allow_html=True)

# --- FIRST ROW: Player Info ---
colA, colB, colC = st.columns([1,1,1])
colA.markdown(f"<div class='kpi'><h4>Player</h4><b>{selected_player}</b></div>", unsafe_allow_html=True)
colB.markdown(f"<div class='kpi'><h4>Team</h4><b>{player_team}</b></div>", unsafe_allow_html=True)
colC.markdown(f"<div class='kpi'><h4>Age Group</h4><b>{age_group}</b></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)

            # ==========================
            # Best Scores summary table
            # ==========================
            st.markdown("<h4 style='margin-top:0'>🏅 Best Performance by Metric</h4>", unsafe_allow_html=True)
            
            summary_data = []
            for metric in player_df["Metric_Type"].unique():
                df_metric = player_df[player_df["Metric_Type"] == metric]
            
                # Best result depends on whether low is better
                best_result = (
                    df_metric["Average"].min() if metric in lower_is_better
                    else df_metric["Average"].max()
                )
            
                summary_data.append({"Metric": metric, "Best Score": best_result})
            
            summary_df = pd.DataFrame(summary_data)
            
            # Render summary (clean table)
            st.dataframe(
                summary_df.style.format({"Best Score": "{:.2f}"})
                                 .set_properties(**{"text-align": "center"}),
                use_container_width=True
            )
            
            st.markdown("</div>", unsafe_allow_html=True)

            # Build summary table per metric: First, Last, Best, Growth (last - best), Goal
            metrics = player_df["Metric_Type"].dropna().unique().tolist()
            summary_rows = []
            for m in metrics:
                df_m = player_df[player_df["Metric_Type"].str.lower() == m.lower()].sort_values("Date")
                if df_m.empty:
                    continue
                first_result = df_m["Average"].iloc[0]
                last_result = df_m["Average"].iloc[-1]
                # best = max for higher-is-better, min for lower-is-better
                if m in lower_is_better:
                    best_result = df_m["Average"].min()
                else:
                    best_result = df_m["Average"].max()
                # Growth per your request = last_result - best_result
                growth = best_result - first_result
                # goal (target) from targets; use player's age_group
                goal = targets.get(age_group, {}).get(m) if age_group in targets else None
                summary_rows.append({
                    "Metric": m,
                    "First Result": round(first_result, 2) if pd.notna(first_result) else None,
                    "Last Result": round(last_result, 2) if pd.notna(last_result) else None,
                    "Best Result": round(best_result, 2) if pd.notna(best_result) else None,
                    "Growth (Last - Best)": round(growth, 2) if pd.notna(growth) else None,
                    "Goal": round(goal, 2) if goal is not None else None
                })

            df_summary = pd.DataFrame(summary_rows).sort_values("Metric")
            st.markdown("### Summary by Metric")
            st.dataframe(df_summary, use_container_width=True)

            # Best values chart (horizontal bar)
            if not df_summary.empty:
                df_best_plot = df_summary.sort_values("Best Result", ascending=False)
                fig_best = px.bar(df_best_plot, x="Best Result", y="Metric", orientation="h", text="Best Result",
                                  title=f"{selected_player} - Best Results (by Metric)")
                fig_best.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig_best.update_layout(margin=dict(l=120))
                st.plotly_chart(fig_best, use_container_width=True)

            # Separate endurance group (Push Ups / Wall Sit / Plank)
            endurance_names = ["push ups", "wall sit", "plank"]
            present_endurance = [m for m in metrics if m.lower() in endurance_names]
            if present_endurance:
                st.markdown("### Endurance (Push Ups • Wall Sit • Plank)")
                fig_end = go.Figure()
                for m in present_endurance:
                    df_e = player_df[player_df["Metric_Type"].str.lower() == m.lower()].sort_values("Date")
                    fig_end.add_trace(go.Scatter(x=df_e["Date"], y=df_e["Average"], mode="lines+markers+text", name=m,
                                                 text=df_e["Average"].round(2), textposition="top center"))
                fig_end.update_layout(height=350, legend_title="Metric")
                st.plotly_chart(fig_end, use_container_width=True)

            # Trend charts: strength (higher is better) and speed (lower is better)
            strength_metrics = [m for m in metrics if m.lower() not in [s.lower() for s in lower_is_better]]
            speed_metrics = [m for m in metrics if m.lower() in [s.lower() for s in lower_is_better]]

            if strength_metrics:
                st.markdown("### Strength Metrics (Higher is better)")
                fig_s = go.Figure()
                for m in strength_metrics:
                    df_m = player_df[player_df["Metric_Type"].str.lower() == m.lower()].sort_values("Date")
                    fig_s.add_trace(go.Scatter(x=df_m["Date"], y=df_m["Average"], mode="lines+markers+text", name=m,
                                               text=df_m["Average"].round(2), textposition="top center"))
                fig_s.update_layout(height=380)
                st.plotly_chart(fig_s, use_container_width=True)

            if speed_metrics:
                st.markdown("### Speed / Agility Metrics (Lower is better)")
                fig_sp = go.Figure()
                for m in speed_metrics:
                    df_m = player_df[player_df["Metric_Type"].str.lower() == m.lower()].sort_values("Date")
                    fig_sp.add_trace(go.Scatter(x=df_m["Date"], y=df_m["Average"], mode="lines+markers+text", name=m,
                                                text=df_m["Average"].round(2), textposition="top center"))
                fig_sp.update_layout(height=380)
                st.plotly_chart(fig_sp, use_container_width=True)

            # Raw data
            st.markdown("### Raw Data")
            st.dataframe(player_df.sort_values(["Metric_Type", "Date"], ascending=[True, False]), use_container_width=True)

# ---------- Team Tab ----------
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Team Dashboard — Overview")
    teams = sorted(df["Team"].dropna().unique())
    selected_team = st.selectbox("Select Team", teams, index=0)

    if selected_team:
        team_df = df[df["Team"] == selected_team].copy()
        if team_df.empty:
            st.info("No records for selected team.")
        else:
            avg_age = round(team_df["Age"].mean(), 1) if team_df["Age"].notna().any() else None
            agg_metrics = team_df["Metric_Type"].dropna().unique().tolist()

            # Team KPIs
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="kpi"><h4>Team</h4><b>{selected_team}</b></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="kpi"><h4>Players</h4><b>{team_df["full_name"].nunique()}</b></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="kpi"><h4>Avg Age</h4><b>{avg_age}</b></div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # Table per metric: team-first, team-last, team-best (averages of players' first/last/best), goal
            team_rows = []
            for m in agg_metrics:
                # for each player compute first/last/best, then average across players
                players_list = team_df["full_name"].unique()
                first_vals, last_vals, best_vals = [], [], []
                for p in players_list:
                    p_df = team_df[(team_df["full_name"] == p) & (team_df["Metric_Type"].str.lower() == m.lower())].sort_values("Date")
                    if p_df.empty:
                        continue
                    first_vals.append(p_df["Average"].iloc[0])
                    last_vals.append(p_df["Average"].iloc[-1])
                    if m in lower_is_better:
                        best_vals.append(p_df["Average"].min())
                    else:
                        best_vals.append(p_df["Average"].max())
                if not first_vals:
                    continue
                team_first = round(pd.Series(first_vals).mean(), 2)
                team_last = round(pd.Series(last_vals).mean(), 2)
                team_best = round(pd.Series(best_vals).mean(), 2)
                growth = round(team_last - team_best, 2)  # last - best per your request
                goal = targets.get(get_age_group(round(avg_age)) if avg_age else "16U", {}).get(m)
                team_rows.append({"Metric": m, "Team First (avg)": team_first, "Team Last (avg)": team_last,
                                  "Team Best (avg)": team_best, "Growth (Last - Best)": growth,
                                  "Goal": round(goal,2) if goal is not None else None})
            df_team_table = pd.DataFrame(team_rows)
            st.markdown("### Team Summary by Metric")
            st.dataframe(df_team_table, use_container_width=True)

            # Dropdown for a single metric comparison (Team average vs Target)
            st.markdown("### Team Average vs Target (pick metric)")
            metric_options = df_team_table["Metric"].tolist()
            sel_metric = st.selectbox("Metric to compare", metric_options)
            if sel_metric:
                row = df_team_table[df_team_table["Metric"].str.lower() == sel_metric.lower()].iloc[0]
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=["Team Average"], y=[row["Team Last (avg)"]], name="Team Avg", text=[row["Team Last (avg)"]], textposition="outside", marker_color="#1155CC"))
                if pd.notna(row["Goal"]):
                    fig_bar.add_trace(go.Bar(x=["Target"], y=[row["Goal"]], name="Target", text=[row["Goal"]], textposition="outside", marker_color="#6AA84F"))
                fig_bar.update_layout(title=f"{sel_metric} — Team Avg vs Target", yaxis_title="Value", barmode="group")
                st.plotly_chart(fig_bar, use_container_width=True)

            # Team Leaderboards: top players per metric
            st.markdown("### Team Leaderboards (per metric)")
            for m in agg_metrics:
                st.markdown(f"**{m}**")
                df_m = team_df[team_df["Metric_Type"].str.lower() == m.lower()]
                if df_m.empty:
                    st.write("No data")
                    continue
                if m in lower_is_better:
                    agg = df_m.groupby("full_name")["Average"].min().reset_index().sort_values("Average", ascending=True).rename(columns={"Average":"Best"})
                else:
                    agg = df_m.groupby("full_name")["Average"].max().reset_index().sort_values("Average", ascending=False).rename(columns={"Average":"Best"})
                agg.insert(0, "Rank", range(1, len(agg)+1))
                st.dataframe(agg.head(10), use_container_width=True)

            # Team raw data
            st.markdown("### Team Raw Data")
            st.dataframe(team_df.sort_values(["Metric_Type","Date"], ascending=[True, False]), use_container_width=True)

# ---------- Leaderboard Tab ----------
with tab3:
    st.subheader("🏆 Global Leaderboard")
    all_metrics = sorted(df["Metric_Type"].dropna().unique())
    leaderboard_metric = st.selectbox("Select Metric for Leaderboard", all_metrics, index=0)
    top_n = st.slider("Top N players", min_value=3, max_value=30, value=10)

    if leaderboard_metric:
        df_m = df[df["Metric_Type"].str.lower() == leaderboard_metric.lower()].copy()
        if df_m.empty:
            st.info("No data for selected metric.")
        else:
            if leaderboard_metric in lower_is_better:
                best_df = df_m.groupby(["full_name","Team","Age"])["Average"].min().reset_index().sort_values("Average", ascending=True)
            else:
                best_df = df_m.groupby(["full_name","Team","Age"])["Average"].max().reset_index().sort_values("Average", ascending=False)
            best_df = best_df.head(top_n).reset_index(drop=True)
            best_df.insert(0, "Rank", range(1, len(best_df)+1))
            # reorder for display
            best_df = best_df[["Rank","full_name","Team","Age","Average"]].rename(columns={"Average":"Best Score"})
            st.dataframe(best_df, use_container_width=True)

            # leaderboard bar chart
            fig_lb = px.bar(best_df, x="full_name", y="Best Score", color="Team", text="Best Score", title=f"Top {top_n} — {leaderboard_metric}")
            fig_lb.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_lb.update_layout(xaxis_title="", yaxis_title="Best Score", showlegend=True)
            st.plotly_chart(fig_lb, use_container_width=True)

