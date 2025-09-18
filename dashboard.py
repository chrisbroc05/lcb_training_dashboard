import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ========================
# 1. Load Google Sheets Data
# ========================
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

    # Convert numeric and date columns
    numeric_cols = ["Attempt_1", "Attempt_2", "Attempt_3", "Last_Attempt", "Average", "Highest", "Lowest"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Full name column
    df["full_name"] = df["Player_name_first"].fillna('') + " " + df["Player_name_last"].fillna('')
    return df

df = load_data()

# ========================
# Helper Functions
# ========================
def get_age_group(age):
    if age <= 8: return "8U"
    elif age <= 10: return "10U"
    elif age <= 12: return "12U"
    elif age <= 14: return "14U"
    else: return "16U"

lower_is_better = {"10 yard sprint", "Pro Agility", "Home to 1B sprint"}
targets = {
    "8U": {"Bench":30,"Squat":50,"Pull Ups":2,"BES Tee":40,"BES Flip":35,"10 yard sprint":2.2,"Pro Agility":5.5,"Arm Speed Regular":35,"Arm Speed Pitch":30,"Home to 1B sprint":4.5},
    "10U":{"Bench":40,"Squat":70,"Pull Ups":4,"BES Tee":50,"BES Flip":45,"10 yard sprint":2.0,"Pro Agility":5.0,"Arm Speed Regular":45,"Arm Speed Pitch":40,"Home to 1B sprint":4.2},
    "12U":{"Bench":50,"Squat":90,"Pull Ups":6,"BES Tee":60,"BES Flip":55,"10 yard sprint":1.9,"Pro Agility":4.8,"Arm Speed Regular":55,"Arm Speed Pitch":50,"Home to 1B sprint":4.0},
    "14U":{"Bench":70,"Squat":110,"Pull Ups":8,"BES Tee":70,"BES Flip":65,"10 yard sprint":1.8,"Pro Agility":4.6,"Arm Speed Regular":65,"Arm Speed Pitch":60,"Home to 1B sprint":3.9},
    "16U":{"Bench":90,"Squat":140,"Pull Ups":10,"BES Tee":80,"BES Flip":75,"10 yard sprint":1.7,"Pro Agility":4.5,"Arm Speed Regular":75,"Arm Speed Pitch":70,"Home to 1B sprint":3.8}
}

# ========================
# Main Layout
# ========================
tab1, tab2, tab3 = st.tabs(["👤 Players", "👥 Teams", "🏆 Leaderboard"])

# ========================
# Players Tab
# ========================
with tab1:
    st.title("Player Insights")
    players = sorted(df["full_name"].dropna().unique())
    selected_player = st.selectbox("Select Player", players)

    if selected_player:
        player_df = df[df["full_name"] == selected_player]

        if not player_df.empty:
            # Profile Card (with black text)
            player_age = player_df["Age"].iloc[0]
            player_team = player_df["Team"].iloc[0]
            total_sessions = player_df["Date"].nunique()

            st.markdown(f"""
            <div style="background-color:#f0f2f6;padding:15px;border-radius:10px;margin-bottom:10px;color:black;">
                <h3 style="color:black;">{selected_player}</h3>
                <p><b>Team:</b> {player_team}</p>
                <p><b>Age:</b> {player_age} ({get_age_group(player_age)})</p>
                <p><b>Total Sessions:</b> {total_sessions}</p>
            </div>
            """, unsafe_allow_html=True)

            # ========================
            # Players Tab – Gauges per metric (with correct delta colors)
            # ========================
            st.subheader("Performance vs Targets")
            age_targets = targets.get(get_age_group(player_age), {})
            gauge_metrics = [m for m in player_df["Metric_Type"].unique() if m in age_targets]
            
            if gauge_metrics:
                for metric in gauge_metrics:
                    current_value = player_df[player_df["Metric_Type"] == metric]["Average"].iloc[-1]
                    target_value = age_targets[metric]
            
                    is_lower_better = metric in lower_is_better
                    axis_range = [0, target_value * 1.5]
            
                    # ✅ Fix: Adjust delta colors dynamically
                    delta_colors = (
                        {"increasing": {"color": "green"}, "decreasing": {"color": "red"}}
                        if not is_lower_better
                        else {"increasing": {"color": "red"}, "decreasing": {"color": "green"}}
                    )
            
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number+delta",
                        value=current_value,
                        delta={
                            "reference": target_value,
                            **delta_colors
                        },
                        title={"text": metric},
                        gauge={
                            "axis": {"range": axis_range},
                            "bar": {"color": "blue"},
                            "steps": [
                                {"range": [0, target_value], "color": "lightgreen" if not is_lower_better else "lightcoral"},
                                {"range": [target_value, axis_range[1]], "color": "lightcoral" if not is_lower_better else "lightgreen"},
                            ],
                            "threshold": {
                                "line": {"color": "black", "width": 4},
                                "thickness": 0.75,
                                "value": target_value
                            }
                        }
                    ))
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No targets available for this player.")
                
            # Trends
            st.subheader("Progress Over Time")
            for metric in player_df["Metric_Type"].unique():
                df_metric = player_df[player_df["Metric_Type"] == metric]
                if len(df_metric) > 1:
                    fig_line = px.line(df_metric, x="Date", y="Average", title=f"{metric} Progress", markers=True)
                    st.plotly_chart(fig_line, use_container_width=True)

            # Raw Data
            st.subheader("Raw Data")
            st.dataframe(player_df)

# ========================
# Teams Tab
# ========================
with tab2:
    st.title("Team Insights")
    teams = sorted(df["Team"].dropna().unique())
    selected_team = st.selectbox("Select Team", teams)

    if selected_team:
        team_df = df[df["Team"] == selected_team]

        if not team_df.empty:
            avg_age = round(team_df["Age"].mean(), 1)
            total_sessions = team_df["Date"].nunique()
            total_players = team_df["full_name"].nunique()

            st.markdown(f"""
            <div style="background-color:#e8f4f8;padding:15px;border-radius:10px;margin-bottom:10px;color:black;">
                <h3 style="color:black;">{selected_team}</h3>
                <p><b>Players:</b> {total_players}</p>
                <p><b>Average Age:</b> {avg_age}</p>
                <p><b>Total Sessions:</b> {total_sessions}</p>
            </div>
            """, unsafe_allow_html=True)

            # ========================
            # Teams Tab – Team averages vs targets (with dropdown)
            # ========================
            st.subheader("Team Averages vs Targets")
            
            # Compute averages and attach targets
            avg_by_metric = team_df.groupby("Metric_Type")["Average"].mean().reset_index()
            avg_by_metric["Target"] = avg_by_metric["Metric_Type"].apply(
                lambda m: targets.get(get_age_group(avg_age), {}).get(m, None)
            )
            
            # Dropdown to choose metric
            metric_options = avg_by_metric["Metric_Type"].unique()
            selected_metric = st.selectbox("Select Metric", metric_options)
            
            # Filter to the selected metric
            metric_data = avg_by_metric[avg_by_metric["Metric_Type"] == selected_metric].iloc[0]
            
            # Build comparison bar chart
            fig_bar = go.Figure()
            
            # Add team average bar
            fig_bar.add_trace(go.Bar(
                x=["Team Average"],
                y=[metric_data["Average"]],
                name="Team Average",
                marker_color="blue"
            ))
            
            # Add target bar (only if exists)
            if pd.notna(metric_data["Target"]):
                fig_bar.add_trace(go.Bar(
                    x=["Target"],
                    y=[metric_data["Target"]],
                    name="Target",
                    marker_color="green"
                ))
            
            fig_bar.update_layout(
                title=f"{selected_metric}: Team Average vs Target",
                yaxis_title="Value",
                barmode="group"
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)



            # Team leaderboard (all metrics, not just those with targets)
            st.subheader("Team Leaderboard")
            for metric in team_df["Metric_Type"].unique():
                df_metric = team_df[team_df["Metric_Type"] == metric]
                is_lower_better = metric in lower_is_better
                if is_lower_better:
                    df_best = df_metric.groupby("full_name")["Average"].min().reset_index(name="best_score")
                    df_best = df_best.sort_values("best_score", ascending=True)
                else:
                    df_best = df_metric.groupby("full_name")["Average"].max().reset_index(name="best_score")
                    df_best = df_best.sort_values("best_score", ascending=False)
                df_best.insert(0, "Rank", range(1, len(df_best)+1))
                st.write(f"### {metric}")
                st.dataframe(df_best)

            # Raw Data
            st.subheader("Team Data")
            st.dataframe(team_df)
            
# ========================
# 3. Leaderboard Tab
# ========================
with tab3:
    st.subheader("🏆 Leaderboard")

    all_metrics = sorted(df["Metric_Type"].dropna().unique())
    leaderboard_metric = st.selectbox("Select Metric for Leaderboard", all_metrics)

    top_n = st.slider("Select number of top players to display", min_value=3, max_value=20, value=10, step=1)

    if leaderboard_metric:
        # Filter for selected metric
        df_leader = df[df["Metric_Type"] == leaderboard_metric].copy()

        # Lower is better for sprint/agility metrics
        lower_is_better_metrics = {"10 yard sprint", "Pro Agility", "Home to 1B sprint"}
        is_lower_better = leaderboard_metric in lower_is_better_metrics

        # Group by player and include Team + Age
        if is_lower_better:
            df_best = (
                df_leader.groupby(["full_name", "Team", "Age"])["Average"]
                .min()
                .reset_index(name="best_score")
                .sort_values("best_score", ascending=True)
                .head(top_n)
            )
        else:
            df_best = (
                df_leader.groupby(["full_name", "Team", "Age"])["Average"]
                .max()
                .reset_index(name="best_score")
                .sort_values("best_score", ascending=False)
                .head(top_n)
            )

        # Add ranking column
        df_best.insert(0, "Rank", range(1, len(df_best) + 1))

        # Reorder columns for a clean table display
        df_best = df_best[["Rank", "full_name", "Team", "Age", "best_score"]]

        st.write(f"### Top {len(df_best)} Players - {leaderboard_metric}")
        st.dataframe(df_best)

        fig_leader = px.bar(df_best, x="full_name", y="best_score", color="full_name", text="best_score", title=f"Leaderboard - {leaderboard_metric}")
        fig_leader.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        st.plotly_chart(fig_leader, use_container_width=True)

