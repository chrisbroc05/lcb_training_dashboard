import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ========================
# 1. Load Google Sheets data
# ========================
@st.cache_data
def load_data():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    # Load credentials from Streamlit Secrets
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)

    # Open spreadsheet and worksheet
    spreadsheet = client.open("LCBTraining Data")
    worksheet = spreadsheet.worksheet("Data")  # Replace with your sheet name
    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    # Convert numeric columns
    numeric_cols = ["attempt_1", "attempt_2", "attempt_3", "last_attempt", "average", "highest", "lowest"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert date column
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Create full name column
    df["full_name"] = df["first_name"].fillna('') + " " + df["last_name"].fillna('')

    return df

# Load the data
df = load_data()

# ========================
# Sidebar Filters (global)
# ========================
st.sidebar.header("Filter Data")

players = sorted(df["full_name"].dropna().unique())
selected_player = st.sidebar.selectbox("Select Player", ["All"] + players)

metric_types = sorted(df["metric_type"].dropna().unique())
selected_metric = st.sidebar.multiselect("Select Metric Type", ["All"] + metric_types)

teams = sorted(df["team"].dropna().unique())
selected_team = st.sidebar.selectbox("Select Team", ["All"] + teams)

# Apply filters
df_filtered = df.copy()
if selected_player != "All":
    df_filtered = df_filtered[df_filtered["full_name"] == selected_player]
if selected_metric and "All" not in selected_metric:
    df_filtered = df_filtered[df_filtered["metric_type"].isin(selected_metric)]
if selected_team != "All":
    df_filtered = df_filtered[df_filtered["team"] == selected_team]

# ========================
# Tabs
# ========================
tab1, tab2 = st.tabs(["📊 Dashboard", "🏆 Leaderboard"])

# ========================
# 2. Dashboard Tab
# ========================
with tab1:
    st.title("LCB Training Portal")
    st.write(f"### Team: {selected_team if selected_team != 'All' else 'All Teams'}")
    if selected_player != "All":
        st.write(f"### Player: {selected_player}")
    if selected_metric != "All":
        st.write(f"### Metric: {selected_metric}")

    # Summary Metrics Cards
    if not df_filtered.empty:
        total_sessions = df_filtered["date"].nunique()
        lower_is_better_metrics = ["10 yard sprint", "Pro Agility", "Home to 1B sprint"]

        if selected_metric == "All":
            metrics_to_use = df_filtered["metric_type"].unique().tolist()
        else:
            metrics_to_use = selected_metric if isinstance(selected_metric, list) else [selected_metric]

        for metric in metrics_to_use:
            df_metric = df_filtered[df_filtered["metric_type"] == metric]

            if not df_metric.empty:
                st.markdown(f"### 📌 {metric}")

                if "target" not in df_metric.columns:
                    df_metric["target"] = df_metric["average"].mean()

                is_lower_better = metric in lower_is_better_metrics

                best_score = df_metric["lowest"].min() if is_lower_better else df_metric["highest"].max()
                latest_date = df_metric["date"].max()
                latest_avg = df_metric[df_metric["date"] == latest_date]["average"].mean()
                overall_avg = df_metric["average"].mean()
                avg_delta = overall_avg - latest_avg if is_lower_better else latest_avg - overall_avg

                first_avg = df_metric.sort_values("date")["average"].iloc[0]
                improvement_pct = ((first_avg - latest_avg) / first_avg * 100) if is_lower_better else ((latest_avg - first_avg) / first_avg * 100) if first_avg != 0 else 0

                targets_met_pct = (df_metric["average"] <= df_metric["target"]).mean() * 100 if is_lower_better else (df_metric["average"] >= df_metric["target"]).mean() * 100
                consistency_score = df_metric["average"].std()

                col1, col2, col3 = st.columns(3)
                col4, col5, col6 = st.columns(3)

                col1.metric(label="🏆 Best Score", value=f"{best_score:.2f}")
                col2.metric(label="📊 Latest Avg vs Overall", value=f"{latest_avg:.2f}", delta=f"{avg_delta:+.2f}")
                col3.metric(label="📈 Improvement %", value=f"{improvement_pct:+.1f}%")
                col4.metric(label="🎯 % Targets Met", value=f"{targets_met_pct:.1f}%")
                col5.metric(label="📉 Consistency (Std Dev)", value=f"{consistency_score:.2f}")
                col6.metric(label="🗓️ Number of Sessions", value=total_sessions)

                st.markdown("---")
            else:
                st.info(f"No data available for metric: {metric}")
    else:
        st.info("No data available for the current selection.")

    # -----------------
    # Multi-Gauge Charts (Performance vs Targets)
    # -----------------
    def get_age_group(age):
        if age <= 8: return "8U"
        elif age <= 10: return "10U"
        elif age <= 12: return "12U"
        elif age <= 14: return "14U"
        else: return "16U"

    lower_is_better = {"10 yard sprint", "Pro Agility", "Home to 1B sprint"}
    targets = {
        "8U": {"Bench":30, "Squat":50, "Pull Ups":2,"BES - Tee":40,"BES - Flip":35,"10 yard sprint":2.2,"Pro Agility":5.5,"Arm Speed - Regular":35,"Arm Speed - Pitch":30,"Home to 1B sprint":4.5},
        "10U":{"Bench":40,"Squat":70,"Pull Ups":4,"BES - Tee":50,"BES - Flip":45,"10 yard sprint":2.0,"Pro Agility":5.0,"Arm Speed - Regular":45,"Arm Speed - Pitch":40,"Home to 1B sprint":4.2},
        "12U":{"Bench":50,"Squat":90,"Pull Ups":6,"BES - Tee":60,"BES - Flip":55,"10 yard sprint":1.9,"Pro Agility":4.8,"Arm Speed - Regular":55,"Arm Speed - Pitch":50,"Home to 1B sprint":4.0},
        "14U":{"Bench":70,"Squat":110,"Pull Ups":8,"BES - Tee":70,"BES - Flip":65,"10 yard sprint":1.8,"Pro Agility":4.6,"Arm Speed - Regular":65,"Arm Speed - Pitch":60,"Home to 1B sprint":3.9},
        "16U":{"Bench":90,"Squat":140,"Pull Ups":10,"BES - Tee":80,"BES - Flip":75,"10 yard sprint":1.7,"Pro Agility":4.5,"Arm Speed - Regular":75,"Arm Speed - Pitch":70,"Home to 1B sprint":3.8}
    }

    st.subheader("🎯 Performance vs Targets")
    if not df_filtered.empty:
        player_age = df_filtered["age"].iloc[0] if selected_player != "All" else df_filtered["age"].mean()
        age_group = get_age_group(player_age)
        age_targets = targets.get(age_group, {})
        metric_types_in_data = df_filtered["metric_type"].unique()
        gauge_metrics = [m for m in metric_types_in_data if m in age_targets]

        if gauge_metrics:
            num_metrics = len(gauge_metrics)
            rows = (num_metrics // 2) + (num_metrics % 2)
            fig = go.Figure()
            row_idx, col_idx = 0, 0

            for metric in gauge_metrics:
                current_value = df_filtered[df_filtered["metric_type"]==metric]["average"].iloc[-1] if selected_player!="All" else df_filtered[df_filtered["metric_type"]==metric]["average"].mean()
                target_value = age_targets[metric]
                if metric in lower_is_better:
                    delta_reference = target_value
                    delta_increasing_color="red"
                    delta_decreasing_color="green"
                else:
                    delta_reference=target_value
                    delta_increasing_color="green"
                    delta_decreasing_color="red"

                fig.add_trace(go.Indicator(
                    mode="gauge+number+delta",
                    value=current_value,
                    delta={"reference":delta_reference,"increasing":{"color":delta_increasing_color},"decreasing":{"color":delta_decreasing_color}},
                    title={"text":metric},
                    gauge={
                        "axis":{"range":[0,target_value*1.5]},
                        "bar":{"color":"blue"},
                        "steps":[{"range":[0,target_value*0.7],"color":"red"},
                                 {"range":[target_value*0.7,target_value*0.9],"color":"yellow"},
                                 {"range":[target_value*0.9,target_value*1.1],"color":"green"}],
                        "threshold":{"line":{"color":"black","width":4},"thickness":0.75,"value":target_value}
                    },
                    domain={'row':row_idx,'column':col_idx}
                ))
                col_idx +=1
                if col_idx>1:
                    col_idx=0
                    row_idx+=1

            fig.update_layout(grid={'rows':rows,'columns':2,'pattern':"independent"},height=rows*300)
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.warning("No metrics available for target comparison.")

    # -----------------
    # Raw Data Table
    # -----------------
    st.subheader("Raw Data")
    st.dataframe(df_filtered)

# ========================
# 3. Leaderboard Tab
# ========================
with tab2:
    st.subheader("🏆 Leaderboard")

    all_metrics = sorted(df["metric_type"].dropna().unique())
    leaderboard_metric = st.selectbox("Select Metric for Leaderboard", all_metrics)

    top_n = st.slider("Select number of top players to display", min_value=3, max_value=20, value=10, step=1)

    if leaderboard_metric:
        df_leader = df[df["metric_type"]==leaderboard_metric].copy()
        lower_is_better_metrics = {"10 yard sprint", "Pro Agility", "Home to 1B sprint"}
        is_lower_better = leaderboard_metric in lower_is_better_metrics

        if is_lower_better:
            df_best = df_leader.groupby("full_name")["average"].min().reset_index(name="best_score")
            df_best = df_best.sort_values("best_score", ascending=True).head(top_n)
        else:
            df_best = df_leader.groupby("full_name")["average"].max().reset_index(name="best_score")
            df_best = df_best.sort_values("best_score", ascending=False).head(top_n)

        df_best.insert(0,"Rank",range(1,len(df_best)+1))
        st.write(f"### Top {len(df_best)} Players - {leaderboard_metric}")
        st.dataframe(df_best)

        fig_leader = px.bar(df_best,x="full_name",y="best_score",color="full_name",text="best_score",title=f"Leaderboard - {leaderboard_metric}")
        fig_leader.update_traces(texttemplate='%{text:.2f}',textposition='outside')
        st.plotly_chart(fig_leader,use_container_width=True)
