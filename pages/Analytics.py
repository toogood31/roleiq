import streamlit as st
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

# Page config
st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")

# Admin password - TODO: Change this to your own secure password
ADMIN_PASSWORD = "workalign2024"

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Authentication
if not st.session_state.authenticated:
    st.title("Analytics Dashboard")
    st.write("This page is password-protected.")

    password = st.text_input("Enter admin password:", type="password", key="password_input")

    if st.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    st.stop()

# If authenticated, show analytics dashboard
st.title("RoleIQ Analytics Dashboard")

# Logout button in sidebar
with st.sidebar:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    st.write("**Filters**")
    days_filter = st.selectbox("Time Period", [7, 14, 30, 90, 365], index=2)

# Check if logs exist
log_file = "logs/usage_analytics.jsonl"
if not os.path.exists(log_file):
    st.warning("No analytics data yet. Logs will be created once users start analyzing resumes.")
    st.stop()

# Load and parse logs
events = []
try:
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
except Exception as e:
    st.error(f"Error loading analytics: {str(e)}")
    st.stop()

# Filter by date range
cutoff_date = datetime.utcnow() - timedelta(days=days_filter)
filtered_events = []
for event in events:
    event_date = datetime.fromisoformat(event['timestamp'])
    if event_date >= cutoff_date:
        filtered_events.append(event)

if not filtered_events:
    st.warning(f"No events in the last {days_filter} days.")
    st.stop()

# Calculate metrics
total_events = len(filtered_events)
analyses = [e for e in filtered_events if e['event'] == 'analysis_complete']
pdf_downloads = [e for e in filtered_events if e['event'] == 'pdf_download']
errors = [e for e in filtered_events if e['event'] == 'error_occurred']

total_analyses = len(analyses)
total_pdfs = len(pdf_downloads)
total_errors = len(errors)

# Calculate average match score
match_scores = [e['params']['match_score'] for e in analyses if 'match_score' in e['params']]
avg_score = sum(match_scores) / len(match_scores) if match_scores else 0

# Calculate unique days
unique_days = len(set([datetime.fromisoformat(e['timestamp']).date().isoformat() for e in filtered_events]))

# Display key metrics
st.subheader(f"Overview (Last {days_filter} Days)")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Events", total_events)

with col2:
    st.metric("Analyses", total_analyses)

with col3:
    st.metric("PDF Downloads", total_pdfs)

with col4:
    st.metric("Avg Match Score", f"{avg_score:.1f}%")

with col5:
    st.metric("Active Days", unique_days)

st.markdown("---")

# Charts section
col1, col2 = st.columns(2)

with col1:
    st.subheader("Match Score Distribution")
    if match_scores:
        # Create histogram
        score_ranges = {
            "0-20%": 0,
            "21-40%": 0,
            "41-60%": 0,
            "61-80%": 0,
            "81-100%": 0
        }

        for score in match_scores:
            if score <= 20:
                score_ranges["0-20%"] += 1
            elif score <= 40:
                score_ranges["21-40%"] += 1
            elif score <= 60:
                score_ranges["41-60%"] += 1
            elif score <= 80:
                score_ranges["61-80%"] += 1
            else:
                score_ranges["81-100%"] += 1

        chart_data = pd.DataFrame({
            "Range": list(score_ranges.keys()),
            "Count": list(score_ranges.values())
        })
        st.bar_chart(chart_data.set_index("Range"))
    else:
        st.info("No match score data available")

with col2:
    st.subheader("Daily Activity")
    # Group events by day
    daily_counts = defaultdict(int)
    for event in filtered_events:
        date = datetime.fromisoformat(event['timestamp']).date().isoformat()
        daily_counts[date] += 1

    if daily_counts:
        chart_data = pd.DataFrame({
            "Date": list(daily_counts.keys()),
            "Events": list(daily_counts.values())
        })
        chart_data = chart_data.sort_values("Date")
        st.line_chart(chart_data.set_index("Date"))
    else:
        st.info("No activity data available")

st.markdown("---")

# Recent events table
st.subheader("Recent Events")

# Create table data
table_data = []
for event in reversed(filtered_events[-20:]):  # Last 20 events
    timestamp = datetime.fromisoformat(event['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
    event_type = event['event']

    # Extract key params
    params_str = ""
    if 'match_score' in event.get('params', {}):
        params_str = f"Score: {event['params']['match_score']}%"
    if 'error_type' in event.get('params', {}):
        params_str = f"{event['params']['error_type']}: {event['params'].get('error_message', 'N/A')}"

    # Extract location
    location = event.get('location', {})
    location_str = f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"

    table_data.append({
        "Timestamp": timestamp,
        "Event": event_type,
        "Details": params_str,
        "Location": location_str
    })

if table_data:
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No recent events")

st.markdown("---")

# Geographic Distribution
st.subheader("Geographic Distribution")

# Count events by country
country_counts = defaultdict(int)
city_counts = defaultdict(int)

for event in filtered_events:
    location = event.get('location', {})
    country = location.get('country', 'Unknown')
    city = location.get('city', 'Unknown')

    country_counts[country] += 1
    city_counts[f"{city}, {country}"] += 1

col1, col2 = st.columns(2)

with col1:
    st.write("**Top Countries**")
    if country_counts:
        for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            st.write(f"- {country}: {count} events")
    else:
        st.info("No location data available")

with col2:
    st.write("**Top Cities**")
    if city_counts:
        for city, count in sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            st.write(f"- {city}: {count} events")
    else:
        st.info("No location data available")

st.markdown("---")

# Error analysis (if any errors)
if errors:
    st.subheader("Error Analysis")

    error_types = defaultdict(int)
    for error in errors:
        error_type = error['params'].get('error_type', 'Unknown')
        error_types[error_type] += 1

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Error Counts by Type**")
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {error_type}: {count}")

    with col2:
        st.write("**Recent Errors**")
        for error in errors[-5:]:
            timestamp = datetime.fromisoformat(error['timestamp']).strftime("%Y-%m-%d %H:%M")
            error_msg = error['params'].get('error_message', 'N/A')
            st.write(f"- [{timestamp}] {error_msg}")

# Additional insights
st.markdown("---")
st.subheader("Insights")

col1, col2, col3 = st.columns(3)

with col1:
    conversion_rate = (total_pdfs / total_analyses * 100) if total_analyses > 0 else 0
    st.metric("PDF Download Rate", f"{conversion_rate:.1f}%")
    st.caption("Percentage of analyses that resulted in PDF downloads")

with col2:
    error_rate = (total_errors / total_events * 100) if total_events > 0 else 0
    st.metric("Error Rate", f"{error_rate:.1f}%")
    st.caption("Percentage of events that were errors")

with col3:
    avg_daily = total_analyses / unique_days if unique_days > 0 else 0
    st.metric("Avg Analyses/Day", f"{avg_daily:.1f}")
    st.caption("Average number of analyses per active day")
