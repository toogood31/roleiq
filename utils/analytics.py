"""
Analytics utility for tracking usage metrics
Supports both Google Analytics and local logging
"""
import json
import os
from datetime import datetime
import streamlit.components.v1 as components
import requests


def get_user_location():
    """
    Get user's approximate location from IP address
    Returns dict with city, region, country
    """
    try:
        response = requests.get('https://ipapi.co/json/', timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city', 'Unknown'),
                'region': data.get('region', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
                'country_code': data.get('country_code', 'Unknown')
            }
    except Exception:
        pass

    return {
        'city': 'Unknown',
        'region': 'Unknown',
        'country': 'Unknown',
        'country_code': 'Unknown'
    }


def track_event(event_name, event_params=None, ga_measurement_id=None):
    """
    Track custom events in Google Analytics and local logs

    Args:
        event_name: Name of the event (e.g., 'analysis_complete', 'pdf_download')
        event_params: Dict of event parameters (e.g., {'match_score': 88})
        ga_measurement_id: GA4 Measurement ID (if None, only logs locally)
    """
    if event_params is None:
        event_params = {}

    # Local logging (always happens)
    _log_event_locally(event_name, event_params)

    # Google Analytics tracking (if configured)
    if ga_measurement_id and ga_measurement_id != "G-XXXXXXXXXX":
        _track_ga_event(event_name, event_params)


def _log_event_locally(event_name, event_params):
    """Log events to local JSON file for offline analytics"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "usage_analytics.jsonl")

    # Get user location
    location = get_user_location()

    event_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_name,
        "params": event_params,
        "location": location
    }

    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(event_data) + "\n")
    except Exception:
        pass  # Silently fail - analytics shouldn't break the app


def _track_ga_event(event_name, event_params):
    """Send custom event to Google Analytics"""
    # Convert params to GA-compatible format
    params_js = json.dumps(event_params)

    ga_event_script = f"""
    <script>
    if (typeof gtag !== 'undefined') {{
        gtag('event', '{event_name}', {params_js});
    }}
    </script>
    """

    try:
        components.html(ga_event_script, height=0)
    except Exception:
        pass  # Silently fail


def get_usage_summary(days=30):
    """
    Get usage summary from local logs

    Returns:
        Dict with usage statistics
    """
    log_file = "logs/usage_analytics.jsonl"

    if not os.path.exists(log_file):
        return {
            'total_analyses': 0,
            'total_pdfs_downloaded': 0,
            'avg_match_score': 0,
            'unique_days': 0
        }

    analyses = 0
    pdf_downloads = 0
    match_scores = []
    dates = set()

    try:
        with open(log_file, "r") as f:
            for line in f:
                event = json.loads(line.strip())

                # Filter by date range
                event_date = datetime.fromisoformat(event['timestamp'])
                days_ago = (datetime.utcnow() - event_date).days

                if days_ago <= days:
                    dates.add(event_date.date().isoformat())

                    if event['event'] == 'analysis_complete':
                        analyses += 1
                        if 'match_score' in event['params']:
                            match_scores.append(event['params']['match_score'])

                    elif event['event'] == 'pdf_download':
                        pdf_downloads += 1

        return {
            'total_analyses': analyses,
            'total_pdfs_downloaded': pdf_downloads,
            'avg_match_score': sum(match_scores) / len(match_scores) if match_scores else 0,
            'unique_days': len(dates)
        }

    except Exception:
        return {
            'total_analyses': 0,
            'total_pdfs_downloaded': 0,
            'avg_match_score': 0,
            'unique_days': 0
        }
