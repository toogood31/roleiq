# Analytics Dashboard Access Guide

## Accessing the Analytics Dashboard

Once your Streamlit app is running, you'll see **two pages** in the sidebar:

1. **WorkAlign: AI Resume Matcher** (main page)
2. **Analytics** (admin-only page)

### To View Analytics:

1. Run your app: `streamlit run app.py`
2. Click on **"Analytics"** in the left sidebar
3. Enter the admin password when prompted
4. View your dashboard!

### Default Password

**Current password:** `workalign2024`

**IMPORTANT:** Change this before deploying to production!

### Changing the Admin Password

Open `pages/Analytics.py` and modify line 11:

```python
ADMIN_PASSWORD = "your_new_secure_password_here"
```

### What You'll See

The Analytics Dashboard shows:

- **Overview Metrics**
  - Total events logged
  - Number of analyses completed
  - PDF downloads
  - Average match score
  - Active days

- **Interactive Charts**
  - Match score distribution (histogram)
  - Daily activity (line chart)

- **Recent Events Table**
  - Last 20 events with timestamps and details

- **Error Analysis**
  - Error counts by type
  - Recent error messages

- **Key Insights**
  - PDF download rate
  - Error rate
  - Average analyses per day

### Filters

Use the sidebar dropdown to filter by time period:
- Last 7 days
- Last 14 days
- Last 30 days (default)
- Last 90 days
- Last 365 days

### Privacy

This analytics page is:
- ✅ Password-protected
- ✅ Hidden from regular users
- ✅ Only accessible to you (admin)
- ✅ Data stored locally (no external services unless you set up GA4)

### Troubleshooting

**"No analytics data yet"**
- This is normal if you haven't run any analyses yet
- The sample data in `logs/usage_analytics.jsonl` is for testing only
- Real data will be logged once users start analyzing resumes

**Forgot password?**
- Open `pages/Analytics.py`
- Check line 11 for the current password
- Or change it to a new one

## For Production Deployment

1. **Change the password** in `pages/Analytics.py`
2. **Optional:** Use environment variables for the password:
   ```python
   import os
   ADMIN_PASSWORD = os.getenv("ANALYTICS_PASSWORD", "default_password")
   ```
3. Then set the environment variable when running:
   ```bash
   ANALYTICS_PASSWORD=your_secure_password streamlit run app.py
   ```

## Next Steps

- Delete sample data: `rm logs/usage_analytics.jsonl`
- Start analyzing real resumes to collect data
- Check back daily/weekly to monitor usage

Questions? The analytics data is stored in `logs/usage_analytics.jsonl` in JSON Lines format - one event per line.
