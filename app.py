
import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Workforce Capacity & Utilization Tracker",
    layout="wide"
)

st.title("📊 Workforce Capacity & Utilization Analytics")
st.markdown(
    "Operational analytics for workforce allocation, utilization, "
    "bench exposure, and technical capabilities."
)


# --------------------------------------------------
# 2. LOAD AND PREPARE DATA
# --------------------------------------------------
@st.cache_data(ttl=300)
def load_custom_data():
    # Google Sheets CSV export URL
    sheet_id = "1jGWp82ZtlcwNW4Sm9QVt-jg_yW-DyvJtYu3l44gdqP0"
    live_csv_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    )

    # Try the online data source first, then use the local CSV backup
    try:
        df = pd.read_csv(live_csv_url)
        data_source = "Google Sheets"
    except Exception:
        try:
            df = pd.read_csv("workforce_data.csv")
            data_source = "Local CSV backup"
        except Exception as local_error:
            raise RuntimeError(
                "Unable to load data from Google Sheets or the local CSV backup."
            ) from local_error

    # Check that the required columns exist
    required_columns = [
        "Employee",
        "Skill",
        "Grade",
        "Location",
        "Project",
        "Billable Hours",
        "Utilization",
        "Util Status",
        "Bench",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    # Convert utilization values into numeric percentages
    cleaned_util = (
        df["Utilization"]
        .astype(str)
        .str.rstrip("%")
        .str.strip()
    )

    df["Utilization_Rate"] = pd.to_numeric(
        cleaned_util,
        errors="coerce"
    )

    # Convert decimal values such as 0.85 into 85%
    valid_util = df["Utilization_Rate"].dropna()

    if not valid_util.empty and valid_util.max() <= 1.0:
        df["Utilization_Rate"] = df["Utilization_Rate"] * 100

    # Ensure numeric columns can be used in calculations
    df["Billable Hours"] = pd.to_numeric(
        df["Billable Hours"],
        errors="coerce"
    ).fillna(0)

    df["Bench"] = pd.to_numeric(
        df["Bench"],
        errors="coerce"
    ).fillna(0)

    return df, data_source


# --------------------------------------------------
# 3. LOAD DATA SAFELY
# --------------------------------------------------
try:
    df, data_source = load_custom_data()
    st.caption(f"Data source: {data_source}")

except Exception as error:
    st.error(
        "Unable to load the dashboard data. Check that your Google Sheet "
        "is accessible and that workforce_data.csv is available as a backup."
    )
    st.caption(f"Technical details: {error}")
    st.stop()


# --------------------------------------------------
# 4. SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("Operational Controls")

location_options = sorted(df["Location"].dropna().unique().tolist())
location_filter = st.sidebar.multiselect(
    "Filter by Resource Location",
    options=location_options,
    default=location_options
)

skill_options = sorted(df["Skill"].dropna().unique().tolist())
skill_filter = st.sidebar.multiselect(
    "Filter by Core Skill Matrix",
    options=skill_options,
    default=skill_options
)

status_options = sorted(df["Util Status"].dropna().unique().tolist())
status_filter = st.sidebar.multiselect(
    "Filter by Allocation Status",
    options=status_options,
    default=status_options
)


# --------------------------------------------------
# 5. FILTER THE DATA
# --------------------------------------------------
filtered_df = df[
    (df["Location"].isin(location_filter))
    & (df["Skill"].isin(skill_filter))
    & (df["Util Status"].isin(status_filter))
].copy()

if filtered_df.empty:
    st.warning(
        "No employees match the selected filters. "
        "Please select one or more options in the sidebar."
    )
    st.stop()


# --------------------------------------------------
# 6. KEY PERFORMANCE INDICATORS (KPIs)
# --------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Headcount Logged",
        f"{filtered_df.shape[0]:,} Employees"
    )

with col2:
    avg_util = filtered_df["Utilization_Rate"].mean()
    avg_util_display = (
        f"{avg_util:.1f}%" if pd.notna(avg_util) else "N/A"
    )
    st.metric("Average Pool Utilization", avg_util_display)

with col3:
    total_billable = filtered_df["Billable Hours"].sum()
    st.metric(
        "Total Billable Hours",
        f"{total_billable:,.1f} Hrs"
    )

with col4:
    bench_count = filtered_df[
        filtered_df["Bench"] > 0
    ].shape[0]
    st.metric(
        "Resources with Bench Exposure",
        f"{bench_count:,} Profiles"
    )


st.markdown("---")


# --------------------------------------------------
# 7. SKILL UTILIZATION AND LOCATION DISTRIBUTION
# --------------------------------------------------
chart_row1_col1, chart_row1_col2 = st.columns(2)

with chart_row1_col1:
    st.subheader("Competency Utilization Benchmarks")

    skill_util = (
        filtered_df.groupby("Skill")["Utilization_Rate"]
        .mean()
        .reset_index()
    )

    fig_bar = px.bar(
        skill_util,
        x="Skill",
        y="Utilization_Rate",
        labels={
            "Utilization_Rate": "Average Utilization (%)",
            "Skill": "Technical Skill Set",
        },
        color="Skill",
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Safe,
    )

    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)


with chart_row1_col2:
    st.subheader("Resource Distribution by Location Hub")

    loc_dist = (
        filtered_df.groupby("Location")
        .size()
        .reset_index(name="Headcount")
    )

    fig_pie = px.pie(
        loc_dist,
        values="Headcount",
        names="Location",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )

    st.plotly_chart(fig_pie, use_container_width=True)


st.markdown("---")


# --------------------------------------------------
# 8. ALLOCATION STATUS BY GRADE
# --------------------------------------------------
chart_row2_col1, chart_row2_col2 = st.columns(2)

with chart_row2_col1:
    st.subheader("Allocation Status Mix by Grade Level")

    grade_status_mix = (
        filtered_df.groupby(["Grade", "Util Status"])
        .size()
        .reset_index(name="Count")
    )

    fig_stacked = px.bar(
        grade_status_mix,
        x="Grade",
        y="Count",
        color="Util Status",
        labels={
            "Count": "Employee Count",
            "Util Status": "Allocation Status",
        },
        template="plotly_white",
        barmode="stack",
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )

    st.plotly_chart(fig_stacked, use_container_width=True)


with chart_row2_col2:
    st.subheader("Average Utilization by Corporate Grade")

    grade_util = (
        filtered_df.groupby("Grade")["Utilization_Rate"]
        .mean()
        .reset_index()
    )

    fig_grade_bar = px.bar(
        grade_util,
        y="Grade",
        x="Utilization_Rate",
        orientation="h",
        labels={
            "Utilization_Rate": "Average Utilization (%)",
            "Grade": "Corporate Grade",
        },
        color="Grade",
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Dark2,
    )

    fig_grade_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_grade_bar, use_container_width=True)


# --------------------------------------------------
# 9. DETAILED ALLOCATION TABLE
# --------------------------------------------------
st.markdown("---")
st.subheader("Granular Allocation Logs")

display_columns = [
    "Employee",
    "Skill",
    "Grade",
    "Location",
    "Project",
    "Billable Hours",
    "Utilization",
    "Util Status",
]

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
)
