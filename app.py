import streamlit as st
import pandas as pd
import plotly.express as px

# Set up clean responsive page configurations
st.set_page_config(page_title="Workforce Capacity & Utilization Tracker", layout="wide")
st.title("📊 Workforce Capacity & Utilization Analytics")
st.markdown("Operational metrics tracking resource allocations, bench status, and technical domain capabilities.")

# 1. Safely load your custom Google Sheet CSV export
@st.cache_data
def load_custom_data():
    df = pd.read_csv('workforce_data.csv')
    
    # Standardize string representations of percentages to floating values
    if df['Utilization'].dtype == 'object':
        df['Utilization_Rate'] = df['Utilization'].str.rstrip('%').astype('float')
    else:
        # FIXED: Changed the single-line ternary conditional to a clean, valid block
        if df['Utilization'].max() <= 1.0:
            df['Utilization_Rate'] = df['Utilization'] * 100
        else:
            df['Utilization_Rate'] = df['Utilization']
            
    return df

try:
    df = load_custom_data()

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Operational Controls")
    
    # Filter by physical resource locations
    location_options = df['Location'].dropna().unique()
    location_filter = st.sidebar.multiselect("Filter by Resource Location", options=location_options, default=location_options)
    
    # Filter by primary technical domain competency
    skill_options = df['Skill'].dropna().unique()
    skill_filter = st.sidebar.multiselect("Filter by Core Skill Matrix", options=skill_options, default=skill_options)
    
    # Filter by employee utilization operational categories
    status_options = df['Util Status'].dropna().unique()
    status_filter = st.sidebar.multiselect("Filter by Allocation Status", options=status_options, default=status_options)

    # Apply data isolation logic dynamically
    filtered_df = df[
        (df['Location'].isin(location_filter)) & 
        (df['Skill'].isin(skill_filter)) & 
        (df['Util Status'].isin(status_filter))
    ]

    # --- CORE KPI METRIC SCORECARDS ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Headcount Logged", f"{filtered_df.shape[0]} Employees")
    with col2:
        avg_util = filtered_df['Utilization_Rate'].mean()
        st.metric("Average Pool Utilization", f"{avg_util:.1f}%")
    with col3:
        total_billable = filtered_df['Billable Hours'].sum()
        st.metric("Total Active Billings", f"{total_billable:,} Hrs")
    with col4:
        bench_count = filtered_df[filtered_df['Bench'] > 0].shape[0]
        st.metric("Resources with Bench Exposure", f"{bench_count} Profiles")

    st.markdown("---")

    # --- GRAPHICAL DISTRIBUTION ROW 1 ---
    chart_row1_col1, chart_row1_col2 = st.columns(2)

    with chart_row1_col1:
        st.subheader("Competency Utilization Benchmarks")
        skill_util = filtered_df.groupby('Skill')['Utilization_Rate'].mean().reset_index()
        fig_bar = px.bar(
            skill_util, x='Skill', y='Utilization_Rate', 
            labels={'Utilization_Rate': 'Avg Utilization %', 'Skill': 'Technical Skill Set'},
            color='Skill', template='plotly_white', color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with chart_row1_col2:
        st.subheader("Resource Distribution by Location Hub")
        loc_dist = filtered_df.groupby('Location').size().reset_index(name='Headcount')
        fig_pie = px.pie(
            loc_dist, values='Headcount', names='Location', 
            hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # --- GRAPHICAL DISTRIBUTION ROW 2 (NEW GRADE ANALYSIS) ---
    chart_row2_col1, chart_row2_col2 = st.columns(2)

    with chart_row2_col1:
        st.subheader("Allocation Status Mix by Grade Level")
        # Group by Grade and Util Status to map organizational headcount distribution
        grade_status_mix = filtered_df.groupby(['Grade', 'Util Status']).size().reset_index(name='Count')
        fig_stacked = px.bar(
            grade_status_mix, x='Grade', y='Count', color='Util Status',
            labels={'Count': 'Employee Count', 'Util Status': 'Allocation Status'},
            template='plotly_white', barmode='stack',
            color_discrete_sequence=px.colors.qualitative.Vivid
        )
        st.plotly_chart(fig_stacked, use_container_width=True)

    with chart_row2_col2:
        st.subheader("Average Utilization Rate by Corporate Grade")
        # Calculate trailing mean benchmarks by corporate hierarchy tiers
        grade_util = filtered_df.groupby('Grade')['Utilization_Rate'].mean().reset_index()
        fig_grade_bar = px.bar(
            grade_util, y='Grade', x='Utilization_Rate', orientation='h',
            labels={'Utilization_Rate': 'Avg Utilization %'},
            color='Grade', template='plotly_white',
            color_discrete_sequence=px.colors.qualitative.Dark2
        )
        st.plotly_chart(fig_grade_bar, use_container_width=True)

    # --- DETAILED PERFORMANCE DATATABLE ---
    st.markdown("---")
    st.subheader("Granular Allocation Logs")
    st.dataframe(
        filtered_df[['Employee', 'Skill', 'Grade', 'Location', 'Project', 'Billable Hours', 'Utilization', 'Util Status']], 
        use_container_width=True
    )

except FileNotFoundError:
    st.error("⚠️ File 'workforce_data.csv' not found. Please export your Google Sheet data as a CSV and save it into your project folder.")
