# WorkAlign Analytics Setup Guide

Your app now has **dual analytics tracking**:
1. **Google Analytics (GA4)** - Web-based dashboard
2. **Local Logging** - File-based tracking (no setup required)

---

## Option 1: Google Analytics (GA4) - Recommended for Production

### Step 1: Create GA4 Property

1. Go to [Google Analytics](https://analytics.google.com/)
2. Click **Admin** (gear icon, bottom left)
3. Click **Create Property**
4. Fill in:
   - Property name: "WorkAlign"
   - Reporting time zone: Your timezone
   - Currency: USD (or your currency)
5. Click **Next**
6. Business details: Select appropriate options
7. Click **Create**

### Step 2: Get Your Measurement ID

1. After creating property, go to **Admin** > **Data Streams**
2. Click **Add stream** > **Web**
3. Enter:
   - Website URL: `http://localhost:8501` (for testing)
   - Stream name: "WorkAlign Local" or your domain
4. Click **Create stream**
5. **Copy your Measurement ID** (format: `G-XXXXXXXXXX`)

### Step 3: Add Measurement ID to Your App

Open `/Users/anthonygudzak/Desktop/workalign/app.py` and replace:

```python
GA_MEASUREMENT_ID = "G-XXXXXXXXXX"  # TODO: Replace with your actual GA4 ID
```

With your actual ID:

```python
GA_MEASUREMENT_ID = "G-ABC1234567"  # Example
```

### Step 4: Access Your Analytics Dashboard

1. Go to [Google Analytics](https://analytics.google.com/)
2. Select your "WorkAlign" property
3. View real-time data: **Reports** > **Realtime**
4. View historical data: **Reports** > **Life cycle** > **Engagement**

### What GA4 Tracks:

- **Page views**: Every time someone loads your app
- **User sessions**: How long people use your app
- **Geography**: Where your users are located
- **Devices**: Desktop vs mobile, browsers, OS
- **User flow**: Navigation paths through your app
- **Custom events** (when we add them):
  - Analysis completed
  - PDF downloads
  - Error occurrences

### Viewing Key Metrics in GA4:

Navigate to these sections in GA4:

1. **Realtime** - See live users right now
2. **Reports > Engagement > Events** - See all tracked events
3. **Reports > User > Demographics** - See user locations
4. **Reports > User > Tech** - See devices, browsers
5. **Explore** (left sidebar) - Create custom reports

---

## Option 2: Local Analytics (No Setup Required)

Your app **automatically logs** all events to:
```
/Users/anthonygudzak/Desktop/workalign/logs/usage_analytics.jsonl
```

### View Local Analytics:

```bash
# See all events
cat logs/usage_analytics.jsonl | jq

# Count total analyses
grep '"event": "analysis_complete"' logs/usage_analytics.jsonl | wc -l

# Count PDF downloads
grep '"event": "pdf_download"' logs/usage_analytics.jsonl | wc -l

# See average match scores
grep "match_score" logs/usage_analytics.jsonl | jq '.params.match_score' | awk '{sum+=$1; count++} END {print sum/count}'
```

### What's Currently Tracked Locally:

- **analysis_complete** - When user finishes analysis
  - Params: `match_score`, `has_gaps`, `resume_file_type`
- **pdf_download** - When user downloads PDF report
  - Params: `match_score`
- **analyze_another_clicked** - When user clicks "Analyze Another"
- **error_occurred** - When parsing/analysis errors happen
  - Params: `error_type`, `error_message`

### Programmatic Access:

```python
from utils.analytics import get_usage_summary

# Get last 30 days of stats
stats = get_usage_summary(days=30)

print(f"Total analyses: {stats['total_analyses']}")
print(f"Total PDFs: {stats['total_pdfs_downloaded']}")
print(f"Avg match score: {stats['avg_match_score']:.1f}%")
print(f"Active days: {stats['unique_days']}")
```

---

## Recommended Setup for MVP

**For local testing:**
- Use local logging only (already working!)

**For production deployment:**
1. Set up GA4 (10 minutes)
2. Add your Measurement ID to `app.py`
3. Keep local logging as backup

---

## Privacy Considerations

### Google Analytics:
- Collects IP addresses (can be anonymized)
- Uses cookies for session tracking
- **Recommendation**: Add privacy policy if collecting user data

### Local Logging:
- No personal data collected
- Only anonymized usage metrics
- Stored locally on your server

---

## Adding Custom Events (Future)

To track additional events, use:

```python
from utils.analytics import track_event

# Track when user uploads a file
track_event('file_uploaded', {
    'file_type': 'pdf',
    'file_size_kb': 245
}, ga_measurement_id=GA_MEASUREMENT_ID)

# Track errors
track_event('error_occurred', {
    'error_type': 'PARSE_ERROR',
    'error_message': 'Failed to parse PDF'
}, ga_measurement_id=GA_MEASUREMENT_ID)
```

---

## Troubleshooting

### GA4 not showing data?
1. Check Measurement ID is correct in `app.py`
2. Wait 24-48 hours for data to appear in reports (Realtime shows immediately)
3. Test in an incognito window (ad blockers may block GA)
4. Check browser console for errors

### Local logs not created?
1. Check write permissions on `/Users/anthonygudzak/Desktop/workalign/logs/`
2. Run: `ls -la logs/usage_analytics.jsonl`

---

## Next Steps

1. **For now**: Your local logging is already working! Check `logs/usage_analytics.jsonl`
2. **Optional**: Set up GA4 for web dashboard (follow steps above)
3. **Later**: Add custom event tracking for specific user actions

Questions? Check [GA4 Documentation](https://support.google.com/analytics/answer/9304153)
