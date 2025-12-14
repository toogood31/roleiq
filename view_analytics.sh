#!/bin/bash
# WorkAlign Analytics Viewer
# Quick script to view your usage analytics

cd /Users/anthonygudzak/Desktop/workalign

echo "========================================"
echo "WorkAlign Analytics Dashboard"
echo "========================================"
echo ""

# Check if logs exist
if [ ! -f "logs/usage_analytics.jsonl" ]; then
    echo "❌ No analytics data yet!"
    echo ""
    echo "Run a few analyses in your app, then check back."
    echo "Logs will be created at: logs/usage_analytics.jsonl"
    exit 0
fi

# Show file size and line count
FILE_SIZE=$(du -h logs/usage_analytics.jsonl | cut -f1)
EVENT_COUNT=$(wc -l < logs/usage_analytics.jsonl)

echo "📊 Total Events Logged: $EVENT_COUNT"
echo "💾 Log File Size: $FILE_SIZE"
echo ""

# Count analyses
ANALYSIS_COUNT=$(grep -c '"event": "analysis_complete"' logs/usage_analytics.jsonl 2>/dev/null || echo "0")
echo "✅ Analyses Completed: $ANALYSIS_COUNT"

# Count PDF downloads
PDF_COUNT=$(grep -c '"event": "pdf_download"' logs/usage_analytics.jsonl 2>/dev/null || echo "0")
echo "📥 PDF Downloads: $PDF_COUNT"

# Count errors
ERROR_COUNT=$(grep -c '"event": "error_occurred"' logs/usage_analytics.jsonl 2>/dev/null || echo "0")
echo "⚠️  Errors: $ERROR_COUNT"

echo ""
echo "========================================"
echo "Recent Events (last 5):"
echo "========================================"
echo ""

# Show last 5 events (pretty printed if jq is available)
if command -v jq &> /dev/null; then
    tail -5 logs/usage_analytics.jsonl | jq -r '"[\(.timestamp | split("T")[0])] \(.event) - Score: \(.params.match_score // "N/A")"' 2>/dev/null || tail -5 logs/usage_analytics.jsonl
else
    tail -5 logs/usage_analytics.jsonl
    echo ""
    echo "💡 Tip: Install 'jq' for prettier output: brew install jq"
fi

echo ""
echo "========================================"
echo "Commands to explore further:"
echo "========================================"
echo ""
echo "View all events:"
echo "  cat logs/usage_analytics.jsonl"
echo ""
echo "View pretty-printed (if jq installed):"
echo "  cat logs/usage_analytics.jsonl | jq"
echo ""
echo "Filter by event type:"
echo "  grep 'analysis_complete' logs/usage_analytics.jsonl | jq"
echo ""
echo "Calculate average match score:"
echo "  grep 'match_score' logs/usage_analytics.jsonl | jq '.params.match_score' | awk '{sum+=\$1; count++} END {print sum/count}'"
echo ""
